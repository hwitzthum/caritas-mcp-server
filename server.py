"""
Caritas MCP Server with OpenAI ChatGPT Integration
This server provides secure access to OpenAI's chat models for your team
"""

import os
import logging
from typing import Optional, List, Dict
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from auth import require_auth  # Note: auth module handles loading .env internally

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate required environment variables
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Create MCP server
mcp = FastMCP("Caritas API Server")

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Configuration
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', 4000))

# Security configuration
ALLOWED_MODELS = {
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-3.5-turbo'
}
MAX_INPUT_LENGTH = 50000  # Maximum characters for user input
MAX_DOCUMENT_LENGTH = 100000  # Maximum characters for document analysis


# Validation Functions
def validate_input(text: str, field_name: str = "Input", max_length: int = MAX_INPUT_LENGTH) -> None:
    """Validate user input for security and length constraints"""
    if not text:
        raise ValueError(f"{field_name} cannot be empty")

    if not text.strip():
        raise ValueError(f"{field_name} cannot be only whitespace")

    if len(text) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length} characters (got {len(text)})")


def validate_temperature(temperature: float) -> None:
    """Validate temperature parameter"""
    if not isinstance(temperature, (int, float)):
        raise ValueError("Temperature must be a number")

    if not 0 <= temperature <= 1:
        raise ValueError(f"Temperature must be between 0 and 1 (got {temperature})")


def validate_model(model: str) -> None:
    """Validate model is in allowlist"""
    if model not in ALLOWED_MODELS:
        raise ValueError(
            f"Model '{model}' not allowed. Allowed models: {', '.join(sorted(ALLOWED_MODELS))}"
        )


def validate_messages(messages: List[Dict[str, str]]) -> None:
    """Validate message format for multi-turn conversations"""
    if not messages:
        raise ValueError("Messages list cannot be empty")

    if not isinstance(messages, list):
        raise ValueError("Messages must be a list")

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise ValueError(f"Message at index {i} must be a dictionary")

        if 'role' not in msg:
            raise ValueError(f"Message at index {i} missing 'role' field")

        if 'content' not in msg:
            raise ValueError(f"Message at index {i} missing 'content' field")

        if msg['role'] not in ['user', 'assistant', 'system']:
            raise ValueError(f"Message at index {i} has invalid role: {msg['role']}")


def sanitize_error(error: Exception) -> dict:
    """Sanitize error messages to avoid leaking sensitive information"""
    error_type = type(error).__name__

    # Map specific error types to user-friendly messages
    error_messages = {
        'AuthenticationError': 'Authentication failed with OpenAI API',
        'RateLimitError': 'Rate limit exceeded. Please try again later',
        'APIConnectionError': 'Failed to connect to OpenAI API',
        'Timeout': 'Request timed out. Please try again',
        'ValueError': str(error),  # Our validation errors are safe to show
    }

    return {
        "success": False,
        "error": error_messages.get(error_type, "An error occurred processing your request"),
        "error_code": error_type
    }


def get_user_id(user_info: Optional[dict]) -> str:
    """Safely extract user ID from user_info"""
    if not user_info:
        return "unknown"
    return user_info.get("sub", "unknown")


@mcp.tool()
@require_auth
def chat_with_gpt(
        user_message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        auth_token: str = "",
        user_info: dict = None
) -> dict:
    """
    Send a message to ChatGPT and get a response

    This is your main tool for chatting with OpenAI's models.
    Only authenticated Caritas team members can use this.

    Args:
        user_message: The message/question you want to ask ChatGPT
        system_prompt: Optional instructions for how ChatGPT should behave
                      (e.g., "You are a helpful assistant for social workers")
        model: Which model to use (default: gpt-4o)
              Options: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
        temperature: Creativity level (0.0 = focused, 2.0 = creative)
        max_tokens: Maximum length of response
        auth_token: Auth0 token (passed automatically by client)
        user_info: User information from Auth0 (passed automatically)

    Returns:
        dict: ChatGPT's response with metadata

    Example:
        chat_with_gpt(
            user_message="What are best practices for client intake?",
            system_prompt="You are an expert social worker at Caritas Schweiz"
        )
    """
    try:
        # Validate inputs
        validate_input(user_message, "User message")
        if system_prompt:
            validate_input(system_prompt, "System prompt")

        # Log who's making the request
        user_id = get_user_id(user_info)
        logger.info(f"User {user_id} sending message to ChatGPT")

        # Use defaults if not specified
        model = model or DEFAULT_MODEL
        max_tokens = max_tokens or MAX_TOKENS

        # Validate parameters
        validate_model(model)
        validate_temperature(temperature)

        # Build the messages array for OpenAI
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
            max_tokens=max_tokens,
        )

        # Extract the response
        assistant_message = response.choices[0].message.content

        logger.info(f"User {user_id} received response ({response.usage.total_tokens} tokens)")

        return {
            "success": True,
            "response": assistant_message,
            "model_used": model,
            "tokens_used": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }
        }
    except ValueError as e:
        logger.warning(f"Validation error for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in chat_with_gpt for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)


@mcp.tool()
@require_auth
def multi_turn_conversation(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        auth_token: str = "",
        user_info: dict = None
) -> dict:
    """
    Have a multi-turn conversation with ChatGPT

    Use this when you need to maintain context across multiple messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
                 Example: [
                     {"role": "user", "content": "Hello"},
                     {"role": "assistant", "content": "Hi! How can I help?"},
                     {"role": "user", "content": "Tell me about Caritas"}
                 ]
        system_prompt: Optional instructions for ChatGPT's behavior
        model: Which model to use (default: gpt-4o)
        temperature: Creativity level (0.0 = focused, 2.0 = creative)
        auth_token: Auth0 token (passed automatically)
        user_info: User information from Auth0 (passed automatically)

    Returns:
        dict: ChatGPT's response with metadata

    Example:
        multi_turn_conversation(
            messages=[
                {"role": "user", "content": "What is Caritas?"},
                {"role": "assistant", "content": "Caritas is..."},
                {"role": "user", "content": "Tell me more about its history"}
            ],
            system_prompt="You are a Caritas expert"
        )
    """
    try:
        # Validate inputs
        validate_messages(messages)
        if system_prompt:
            validate_input(system_prompt, "System prompt")

        # Log who's making the request
        user_id = get_user_id(user_info)
        logger.info(f"User {user_id} starting multi-turn conversation with ChatGPT")

        # Use defaults
        model = model or DEFAULT_MODEL

        # Validate parameters
        validate_model(model)
        validate_temperature(temperature)

        # Build conversation history
        conversation = []

        # Add system prompt if provided
        if system_prompt:
            conversation.append({
                "role": "system",
                "content": system_prompt
            })

        # Add message history
        conversation.extend(messages)

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model=model,
            messages=conversation,
            temperature=temperature,
            max_tokens=MAX_TOKENS
        )

        # Extract response
        assistant_message = response.choices[0].message.content

        logger.info(f"User {user_id} completed multi-turn conversation ({response.usage.total_tokens} tokens)")

        return {
            "success": True,
            "response": assistant_message,
            "model_used": model,
            "conversation_length": len(conversation),
            "tokens_used": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }

    except ValueError as e:
        logger.warning(f"Validation error for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in multi_turn_conversation for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)


@mcp.tool()
@require_auth
def analyze_document_with_gpt(
        document_text: str,
        analysis_request: str,
        model: Optional[str] = None,
        auth_token: str = "",
        user_info: dict = None
) -> dict:
    """
    Analyze a document using ChatGPT

    Perfect for summarizing reports, extracting key information,
    or analyzing case files.

    Args:
        document_text: The full text of the document to analyze
        analysis_request: What you want to know about the document
                         (e.g., "Summarize this", "Extract action items",
                          "What are the key risks?")
        model: Which model to use (default: gpt-4o - recommended for long docs)
        auth_token: Auth0 token (passed automatically)
        user_info: User information from Auth0 (passed automatically)

    Returns:
        dict: ChatGPT's analysis

    Example:
        analyze_document_with_gpt(
            document_text="[Long case report...]",
            analysis_request="Summarize the key issues and recommended actions"
        )
    """
    try:
        # Validate inputs
        validate_input(document_text, "Document text", MAX_DOCUMENT_LENGTH)
        validate_input(analysis_request, "Analysis request")

        # Log who's making the request
        user_id = get_user_id(user_info)
        doc_length = len(document_text)
        logger.info(f"User {user_id} analyzing document ({doc_length} chars)")

        # Use default model
        model = model or DEFAULT_MODEL
        validate_model(model)

        # Create a specialized system prompt for document analysis
        system_prompt = """You are a document analysis assistant for Caritas Schweiz.
    Provide clear, concise, and actionable analysis.
    Focus on what's most important and relevant."""

        # Build the analysis prompt
        user_prompt = f"""
    Please analyze the following document:

    ---
    {document_text}
    ---

    Analysis request: {analysis_request}

    Please provide a thorough but concise analysis."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,  # Lower temperature for more focused analysis
            max_tokens=MAX_TOKENS
        )

        # Extract response
        analysis = response.choices[0].message.content

        logger.info(f"User {user_id} completed document analysis ({response.usage.total_tokens} tokens)")

        return {
            "success": True,
            "analysis": analysis,
            "document_length": doc_length,
            "model_used": model,
            "tokens_used": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }

    except ValueError as e:
        logger.warning(f"Validation error for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in analyze_document_with_gpt for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)


@mcp.tool()
@require_auth
def translate_text(
        text: str,
        target_language: str,
        source_language: str = "auto",
        auth_token: str = "",
        user_info: dict = None
) -> dict:
    """
    Translate text using ChatGPT

    Useful for translating between Swiss languages (German, French, Italian)
    and other languages your clients might speak.

    Args:
        text: The text to translate
        target_language: Language to translate to
                        (e.g., "German", "French", "Italian", "English")
        source_language: Source language (default: "auto" for auto-detect)
        auth_token: Auth0 token (passed automatically)
        user_info: User information from Auth0 (passed automatically)

    Returns:
        dict: Translated text

    Example:
        translate_text(
            text="Hello, how can I help you today?",
            target_language="German"
        )
    """
    try:
        # Validate inputs
        validate_input(text, "Text to translate", 10000)  # Reasonable limit for translation
        validate_input(target_language, "Target language", 100)

        # Log who's making the request
        user_id = get_user_id(user_info)
        logger.info(f"User {user_id} translating text to {target_language}")

        # Build translation prompt
        if source_language == "auto":
            prompt = f"Translate the following text to {target_language}:\n\n{text}"
        else:
            prompt = f"Translate the following text from {source_language} to {target_language}:\n\n{text}"

        messages = [
            {
                "role": "system",
                "content": "You are a professional translator. Provide accurate, natural-sounding translations. Only output the translation, no explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # GPT-4 is better at translation
            messages=messages,
            temperature=0.3,  # Lower temperature for consistent translation
            max_tokens=2000
        )

        # Extract translation
        translation = response.choices[0].message.content

        logger.info(f"User {user_id} completed translation ({response.usage.total_tokens} tokens)")

        return {
            "success": True,
            "original_text": text,
            "translated_text": translation,
            "target_language": target_language,
            "source_language": source_language,
            "tokens_used": response.usage.total_tokens
        }

    except ValueError as e:
        logger.warning(f"Validation error for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in translate_text for user {get_user_id(user_info)}: {e}")
        return sanitize_error(e)


@mcp.tool()
@require_auth
def get_user_info(auth_token: str = "", user_info: dict = None) -> dict:
    """
    Get information about the authenticated user

    This is useful for debugging and seeing who's logged in

    Args:
        auth_token: Auth0 token (passed automatically)
        user_info: User information from Auth0 (passed automatically)

    Returns:
        dict: User information from Auth0 token
    """
    if not user_info:
        return {
            "error": "User information not available"
        }

    return {
        "user_id": user_info.get('sub'),
        "permissions": user_info.get('permissions', []),
        "issued_at": user_info.get('iat'),
        "expires_at": user_info.get('exp')
    }


@mcp.tool()
def health_check() -> dict:
    """
    Check if the server is running (no authentication required)

    Returns:
        dict: Server health status
    """
    # Test OpenAI connection
    try:
        openai_client.models.list()
        openai_status = "connected"
    except Exception as e:
        openai_status = f"error: {type(e).__name__}"
        logger.warning(f"OpenAI connection test failed: {e}")

    # Test Auth0 configuration (don't make actual request, just check config)
    try:
        from auth import auth_validator
        auth_config_status = "configured" if auth_validator.domain and auth_validator.api_identifier else "missing"
    except Exception as e:
        auth_config_status = f"error: {type(e).__name__}"
        logger.warning(f"Auth0 configuration check failed: {e}")

    return {
        "status": "healthy",
        "message": "Caritas MCP Server is running!",
        "auth_enabled": True,
        "auth_config_status": auth_config_status,
        "openai_status": openai_status,
        "default_model": DEFAULT_MODEL,
        "allowed_models": list(ALLOWED_MODELS)
    }


if __name__ == "__main__":
    # For remote hosting (Render, etc.), use HTTP transport
    # For local stdio development, you can use: mcp.run()
    import uvicorn

    # Get port from environment (Render sets this automatically)
    port = int(os.getenv('PORT', 8000))

    logger.info(f"Starting MCP HTTP server on port {port}")

    # Get the FastMCP HTTP app
    app = mcp.streamable_http_app()

    # Run as HTTP server for remote access
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces (required for Render)
        port=port,
        log_level="info"
    )

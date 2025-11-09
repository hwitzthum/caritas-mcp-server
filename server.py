"""
Caritas MCP Server with OpenAI ChatGPT Integration
Simplified production-ready server with FastMCP built-in Auth0 JWT verification
"""

import os
import logging
from typing import Optional, List, Dict
from fastmcp import FastMCP
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate required environment variables
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Create MCP server with authentication configured via environment variables
# Authentication is automatically configured from FASTMCP_SERVER_AUTH_* env vars
mcp = FastMCP("Caritas API Server")

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Configuration
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '4000'))

# Security configuration
ALLOWED_MODELS = {
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-3.5-turbo'
}
MAX_INPUT_LENGTH = 50000
MAX_DOCUMENT_LENGTH = 100000


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


def sanitize_error(error: Exception) -> dict:
    """Sanitize error messages to avoid leaking sensitive information"""
    error_type = type(error).__name__
    error_messages = {
        'AuthenticationError': 'Authentication failed with OpenAI API',
        'RateLimitError': 'Rate limit exceeded. Please try again later',
        'APIConnectionError': 'Failed to connect to OpenAI API',
        'Timeout': 'Request timed out. Please try again',
        'ValueError': str(error),
    }
    return {
        "success": False,
        "error": error_messages.get(error_type, "An error occurred processing your request"),
        "error_code": error_type
    }


# MCP Tools - Authentication is handled automatically by FastMCP
@mcp.tool()
def chat_with_gpt(
        user_message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
) -> dict:
    """
    Send a message to ChatGPT and get a response

    Args:
        user_message: The message/question you want to ask ChatGPT
        system_prompt: Optional instructions for how ChatGPT should behave
        model: Which model to use (default: gpt-4o)
        temperature: Creativity level (0.0 = focused, 1.0 = creative)
        max_tokens: Maximum length of response

    Returns:
        dict: ChatGPT's response with metadata
    """
    try:
        validate_input(user_message, "User message")
        if system_prompt:
            validate_input(system_prompt, "System prompt")

        logger.info("Sending message to ChatGPT")

        model = model or DEFAULT_MODEL
        max_tokens = max_tokens or MAX_TOKENS

        validate_model(model)
        validate_temperature(temperature)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = openai_client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
            max_tokens=max_tokens,
        )

        assistant_message = response.choices[0].message.content

        logger.info(f"Received response ({response.usage.total_tokens} tokens)")

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
        logger.warning(f"Validation error: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in chat_with_gpt: {e}")
        return sanitize_error(e)


@mcp.tool()
def multi_turn_conversation(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
) -> dict:
    """
    Have a multi-turn conversation with ChatGPT

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        system_prompt: Optional instructions for ChatGPT's behavior
        model: Which model to use (default: gpt-4o)
        temperature: Creativity level (0.0 = focused, 1.0 = creative)

    Returns:
        dict: ChatGPT's response with metadata
    """
    try:
        if not messages or not isinstance(messages, list):
            raise ValueError("Messages must be a non-empty list")

        if system_prompt:
            validate_input(system_prompt, "System prompt")

        logger.info("Starting multi-turn conversation with ChatGPT")

        model = model or DEFAULT_MODEL
        validate_model(model)
        validate_temperature(temperature)

        conversation = []
        if system_prompt:
            conversation.append({"role": "system", "content": system_prompt})
        conversation.extend(messages)

        response = openai_client.chat.completions.create(
            model=model,
            messages=conversation,
            temperature=temperature,
            max_tokens=MAX_TOKENS
        )

        assistant_message = response.choices[0].message.content

        logger.info(f"Completed multi-turn conversation ({response.usage.total_tokens} tokens)")

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
        logger.warning(f"Validation error: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in multi_turn_conversation: {e}")
        return sanitize_error(e)


@mcp.tool()
def analyze_document_with_gpt(
        document_text: str,
        analysis_request: str,
        model: Optional[str] = None
) -> dict:
    """
    Analyze a document using ChatGPT

    Args:
        document_text: The full text of the document to analyze
        analysis_request: What you want to know about the document
        model: Which model to use (default: gpt-4o)

    Returns:
        dict: ChatGPT's analysis
    """
    try:
        validate_input(document_text, "Document text", MAX_DOCUMENT_LENGTH)
        validate_input(analysis_request, "Analysis request")

        doc_length = len(document_text)
        logger.info(f"Analyzing document ({doc_length} chars)")

        model = model or DEFAULT_MODEL
        validate_model(model)

        system_prompt = """You are a document analysis assistant for Caritas Schweiz.
Provide clear, concise, and actionable analysis.
Focus on what's most important and relevant."""

        user_prompt = f"""Please analyze the following document:

---
{document_text}
---

Analysis request: {analysis_request}

Please provide a thorough but concise analysis."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=MAX_TOKENS
        )

        analysis = response.choices[0].message.content

        logger.info(f"Completed document analysis ({response.usage.total_tokens} tokens)")

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
        logger.warning(f"Validation error: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in analyze_document_with_gpt: {e}")
        return sanitize_error(e)


@mcp.tool()
def translate_text(
        text: str,
        target_language: str,
        source_language: str = "auto"
) -> dict:
    """
    Translate text using ChatGPT

    Args:
        text: The text to translate
        target_language: Language to translate to
        source_language: Source language (default: "auto" for auto-detect)

    Returns:
        dict: Translated text
    """
    try:
        validate_input(text, "Text to translate", 10000)
        validate_input(target_language, "Target language", 100)

        logger.info(f"Translating text to {target_language}")

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

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=2000
        )

        translation = response.choices[0].message.content

        logger.info(f"Completed translation ({response.usage.total_tokens} tokens)")

        return {
            "success": True,
            "original_text": text,
            "translated_text": translation,
            "target_language": target_language,
            "source_language": source_language,
            "tokens_used": response.usage.total_tokens
        }
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return sanitize_error(e)
    except Exception as e:
        logger.error(f"Error in translate_text: {e}")
        return sanitize_error(e)


@mcp.tool()
def health_check() -> dict:
    """
    Check if the server is running

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

    return {
        "status": "healthy",
        "message": "Caritas MCP Server is running!",
        "auth_enabled": True,
        "openai_status": openai_status,
        "default_model": DEFAULT_MODEL,
        "allowed_models": list(ALLOWED_MODELS)
    }


if __name__ == "__main__":
    # For Render.com deployment - use SSE transport for Claude Desktop compatibility
    # Note: SSE is needed because mcp-remote (used by Claude Desktop) doesn't support Streamable HTTP yet
    port = int(os.getenv('PORT', '8000'))

    logger.info(f"Starting Caritas MCP Server on 0.0.0.0:{port}")
    logger.info(f"Authentication: FastMCP JWT Verification (Auth0)")
    logger.info(f"Transport: SSE (for Claude Desktop compatibility)")

    # Run with SSE transport - compatible with mcp-remote
    # Authentication is automatically configured via FASTMCP_SERVER_AUTH_* environment variables
    import uvicorn

    # Create the ASGI app with SSE transport at /sse endpoint
    app = mcp.http_app(transport="sse", path="/sse")

    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
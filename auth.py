"""
Auth0 Authentication Middleware for MCP Server
This checks if the incoming request has a valid Auth0 token
"""

import os
import logging
import requests
from jose import jwt, jwk
from jose.exceptions import JWTError, JWKError
from functools import wraps
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file (for local dev only)
# On Render, env vars are set in the dashboard, so this is a no-op
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Auth0Validator:
    """
    Simple class to validate Auth0 tokens
    Think of this as your bouncer checking IDs
    """

    def __init__(self):
        # Get Auth0 configuration from environment
        self.domain = os.getenv('AUTH0_DOMAIN')
        self.api_identifier = os.getenv('AUTH0_API_IDENTIFIER')
        self.algorithms = os.getenv('AUTH0_ALGORITHMS', 'RS256').split(',')

        # Validate required configuration
        if not self.domain:
            raise ValueError("AUTH0_DOMAIN environment variable is required")
        if not self.api_identifier:
            raise ValueError("AUTH0_API_IDENTIFIER environment variable is required")

        # Get Auth0's public keys (used to verify tokens)
        self.jwks_url = f'https://{self.domain}/.well-known/jwks.json'
        self.jwks_cache = None
        self.jwks_cache_time = None
        self.jwks_cache_ttl = timedelta(hours=24)  # Cache for 24 hours

    def get_jwks(self) -> dict:
        """
        Get JWKS from Auth0, with caching
        """
        # Check if cache is valid
        if (self.jwks_cache and self.jwks_cache_time and
            datetime.now() - self.jwks_cache_time < self.jwks_cache_ttl):
            return self.jwks_cache

        # Fetch fresh JWKS
        try:
            logger.info(f"Fetching JWKS from {self.jwks_url}")
            response = requests.get(self.jwks_url, timeout=10)
            response.raise_for_status()
            jwks = response.json()

            # Update cache
            self.jwks_cache = jwks
            self.jwks_cache_time = datetime.now()
            logger.info("JWKS cache updated successfully")

            return jwks

        except requests.exceptions.Timeout:
            logger.error("Timeout fetching JWKS from Auth0")
            if self.jwks_cache:
                logger.warning("Using stale JWKS cache due to timeout")
                return self.jwks_cache
            raise Exception("Unable to fetch JWKS and no cache available")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching JWKS: {e}")
            if self.jwks_cache:
                logger.warning("Using stale JWKS cache due to error")
                return self.jwks_cache
            raise Exception(f"Unable to fetch JWKS: {e}")

    def get_signing_key(self, token: str):
        """
        Get the public key to verify the token
        This is like checking if an ID was issued by the real DMV
        """
        try:
            # Get JWKS (cached)
            jwks = self.get_jwks()

            # Decode token header to find which key was used
            unverified_header = jwt.get_unverified_header(token)

            # Find the matching key
            for key in jwks.get('keys', []):
                if key.get('kid') == unverified_header.get('kid'):
                    # Convert JWK to PEM format for verification
                    return jwk.construct(key).to_pem()

            raise Exception('Unable to find appropriate signing key')

        except JWKError as e:
            logger.error(f"JWK error: {e}")
            raise Exception(f"Invalid signing key: {e}")

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify if a token is valid
        Returns the token payload if valid, None if invalid
        """
        if not token:
            logger.warning("Empty token provided")
            return None

        try:
            # Get the signing key (in PEM format)
            signing_key = self.get_signing_key(token)

            # Verify and decode the token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=self.algorithms,
                audience=self.api_identifier,
                issuer=f'https://{self.domain}/'
            )

            logger.info(f"Token validated successfully for user: {payload.get('sub', 'unknown')}")
            return payload

        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            return None


# Create a global validator instance
auth_validator = Auth0Validator()

def require_auth(func):
    """
    Decorator to require authentication for MCP tools
    Use this on any tool that needs authentication

    Usage:
        @require_auth
        def my_secure_tool():
            ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # In a real implementation, you'd extract the token from the request
        # For MCP, this will be passed via headers or context
        # This is a simplified version for demonstration

        token = kwargs.get('auth_token')
        if not token:
            raise ValueError("Authentication token required")

        # Remove the 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Verify the token
        payload = auth_validator.verify_token(token)
        if not payload:
            raise ValueError("Invalid or expired authentication token")

        # Add user info to kwargs for the tool to use
        kwargs['user_info'] = payload

        # Call the original function
        return func(*args, **kwargs)

    return wrapper

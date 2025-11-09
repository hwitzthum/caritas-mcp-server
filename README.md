# Caritas MCP Server

**Production-ready FastMCP server with Auth0 JWT authentication and OpenAI integration**

Simplified and secure MCP (Model Context Protocol) server providing authenticated access to OpenAI ChatGPT, deployed on Render.com.

## Features

- 🔐 **Auth0 JWT Authentication**: Built-in FastMCP JWT verification (no custom middleware!)
- 🤖 **OpenAI Integration**: Access to GPT-4o, GPT-4o-mini, GPT-4-turbo, and GPT-3.5
- 🌍 **Translation**: Multi-language support for Swiss organizations
- 📄 **Document Analysis**: Analyze and summarize documents up to 100k characters
- 💬 **Chat & Conversations**: Single and multi-turn conversations
- 🛡️ **Security**: Input validation, model allowlist, error sanitization
- 🚀 **Streamable HTTP**: Production-ready transport with FastMCP

## Architecture

### Simplified Authentication Flow

```
┌─────────────┐                ┌─────────────────┐
│   Client    │───── JWT ─────▶│  FastMCP Server │
│             │                 │ (Render.com)    │
└─────────────┘                 └─────────────────┘
       │                               │
       │                               │ Auto-verify JWT
       │                               ▼
       │                        ┌──────────────┐
       │                        │  Auth0 JWKS  │
       └───── Get Token ───────▶│  Endpoint    │
                                 └──────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │   OpenAI     │
                                 │     API      │
                                 └──────────────┘
```

**Key Simplifications:**
- FastMCP handles JWT verification automatically
- No custom middleware needed
- No manual token parsing
- Configuration via environment variables

## Quick Start (Local Development)

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy and edit the environment file:

```bash
cp .env .env
```

Update `.env` with your credentials:

```bash
# FastMCP Authentication Provider
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.jwt.JWTVerifier

# Auth0 Configuration (from https://manage.auth0.com/)
AUTH0_DOMAIN=your-tenant.auth0.com
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=https://caritas-mcp-server.onrender.com
FASTMCP_SERVER_AUTH_JWT_ISSUER=https://your-tenant.auth0.com/
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=https://your-tenant.auth0.com/.well-known/jwks.json
FASTMCP_SERVER_AUTH_JWT_ALGORITHM=RS256

# OpenAI Configuration (from https://platform.openai.com/)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000
```

### 3. Run the Server

```bash
python server.py
```

Server will start on `http://localhost:8000/mcp`

### 4. Test Health Check

```bash
curl http://localhost:8000/mcp
```

## Deploying to Render.com

### Prerequisites

1. **Auth0 Account**: Create an API in Auth0
   - Go to [Auth0 Dashboard](https://manage.auth0.com/)
   - Create an API with identifier: `https://caritas-mcp-server.onrender.com`
   - Note your domain (e.g., `your-tenant.auth0.com`)

2. **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)

3. **GitHub Repository**: Your code must be in a Git repository

### Deployment Steps

#### 1. Prepare Your Repository

Ensure your code is committed:

```bash
git init
git add .
git commit -m "Initial FastMCP server deployment"
```

**IMPORTANT**: Never commit `.env` file (it's already in `.gitignore`)

#### 2. Deploy to Render

**Option A: Using render.yaml (Recommended)**

1. Push to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click **New +** → **Blueprint**
4. Connect your repository
5. Render will automatically detect `render.yaml`

**Option B: Manual Setup**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `caritas-mcp-server`
   - **Region**: `Frankfurt` (closest to Switzerland)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Plan**: `Starter` ($7/month recommended)

#### 3. Set Environment Variables

In Render Dashboard → Your Service → **Environment**, add these variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `FASTMCP_SERVER_AUTH` | `fastmcp.server.auth.providers.jwt.JWTVerifier` | Required |
| `FASTMCP_SERVER_AUTH_JWT_AUDIENCE` | `https://caritas-mcp-server.onrender.com` | Your Auth0 API identifier |
| `FASTMCP_SERVER_AUTH_JWT_ISSUER` | `https://your-tenant.auth0.com/` | Include trailing slash |
| `FASTMCP_SERVER_AUTH_JWT_JWKS_URI` | `https://your-tenant.auth0.com/.well-known/jwks.json` | Auth0 JWKS endpoint |
| `FASTMCP_SERVER_AUTH_JWT_ALGORITHM` | `RS256` | Standard Auth0 algorithm |
| `OPENAI_API_KEY` | `sk-...` | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default model |
| `OPENAI_MAX_TOKENS` | `4000` | Max tokens per response |

#### 4. Deploy and Verify

1. Click **Save Changes** - Render will deploy automatically
2. Wait for build to complete (check logs)
3. Your service will be available at: `https://caritas-mcp-server.onrender.com`

**Test the deployment:**

```bash
# Health check (no auth required)
curl https://caritas-mcp-server.onrender.com/mcp

# With authentication (requires Auth0 token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://caritas-mcp-server.onrender.com/mcp
```

### Getting an Auth0 Token (for testing)

Use Auth0's API to get a token:

```bash
curl --request POST \
  --url https://YOUR_TENANT.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://caritas-mcp-server.onrender.com",
    "grant_type": "client_credentials"
  }'
```

## Available MCP Tools

All tools require Auth0 JWT authentication (except `health_check`):

### 1. `chat_with_gpt`
Send a message to ChatGPT

**Parameters:**
- `user_message` (str, required): Your question
- `system_prompt` (str, optional): Instructions for ChatGPT's behavior
- `model` (str, optional): Model to use (default: gpt-4o)
- `temperature` (float, optional): 0.0-1.0 (default: 0.7)
- `max_tokens` (int, optional): Max response length

### 2. `multi_turn_conversation`
Multi-turn conversation with context

**Parameters:**
- `messages` (list, required): List of `{"role": "user/assistant", "content": "..."}`
- `system_prompt` (str, optional): System instructions
- `model` (str, optional): Model to use
- `temperature` (float, optional): Creativity level

### 3. `analyze_document_with_gpt`
Analyze documents up to 100k characters

**Parameters:**
- `document_text` (str, required): Full document text
- `analysis_request` (str, required): What to analyze
- `model` (str, optional): Model to use

### 4. `translate_text`
Translate text between languages

**Parameters:**
- `text` (str, required): Text to translate (max 10k chars)
- `target_language` (str, required): Target language
- `source_language` (str, optional): Source language (default: "auto")

### 5. `health_check`
Check server status (no auth required)

**Returns:** Server health, OpenAI status, available models

## What Changed (Simplification)

### Before (Over-Complicated)
- ❌ Custom `auth.py` with manual JWT validation
- ❌ Custom `auth_middleware.py` with Starlette middleware
- ❌ Manual JWKS fetching and caching
- ❌ Dependencies: `python-jose`, `requests`
- ❌ 180+ lines of authentication code
- ❌ Type errors in OpenAI API calls

### After (Best Practice)
- ✅ FastMCP built-in JWT verification
- ✅ Configuration via environment variables
- ✅ No custom authentication code needed
- ✅ Minimal dependencies: `fastmcp`, `openai`, `uvicorn`
- ✅ ~400 lines total (vs 600+)
- ✅ No type errors

## Security Best Practices

✅ **DO:**
- Use FastMCP's built-in JWT verification
- Set environment variables in Render Dashboard (never commit)
- Use different Auth0 credentials for dev/production
- Rotate API keys regularly
- Monitor OpenAI usage and costs
- Keep dependencies updated

❌ **DON'T:**
- Commit `.env` to git
- Share API keys
- Hardcode credentials
- Use production credentials locally
- Skip input validation

## Troubleshooting

### Local Development

**Error: Missing FASTMCP_SERVER_AUTH**
- Ensure `.env` file exists
- Check `FASTMCP_SERVER_AUTH` is set to `fastmcp.server.auth.providers.jwt.JWTVerifier`

**Error: OPENAI_API_KEY required**
- Verify `.env` has `OPENAI_API_KEY`
- Key must start with `sk-`

**Error: Module not found**
- Run: `pip install -r requirements.txt`

### Render Deployment

**Build Fails**
- Check logs in Render dashboard
- Verify `requirements.txt` is correct
- Ensure Python 3.11+ compatibility

**Authentication Fails**
- Verify all `FASTMCP_SERVER_AUTH_JWT_*` variables are set
- Check Auth0 API identifier matches `FASTMCP_SERVER_AUTH_JWT_AUDIENCE`
- Ensure JWKS URI is correct (include `.well-known/jwks.json`)
- Verify issuer URL has trailing slash

**Server Crashes**
- Check Render logs for specific error
- Test OpenAI API key is valid
- Verify all required env vars are set

**Connection Refused**
- Wait for deployment to complete
- Check service status in Render dashboard
- Verify health check endpoint: `/mcp`

## Files Structure

```
1-Project/
├── server.py              # Main FastMCP server (simplified!)
├── requirements.txt       # Minimal dependencies
├── .env.example          # Environment variable template
├── render.yaml           # Render deployment config
├── README.md             # This file
└── .gitignore           # Excludes .env
```

## Cost Estimates

**Render.com:**
- Starter Plan: $7/month
- Includes: 512 MB RAM, auto-scaling, HTTPS, custom domain

**OpenAI:**
- GPT-4o-mini: ~$0.15 per 1M tokens (input) / $0.60 per 1M tokens (output)
- GPT-4o: ~$2.50 per 1M tokens (input) / $10.00 per 1M tokens (output)

**Auth0:**
- Free tier: Up to 7,500 active users
- Perfect for internal tools

## Support & Resources

- **FastMCP Docs**: https://gofastmcp.com/
- **Auth0 Docs**: https://auth0.com/docs
- **Render Docs**: https://render.com/docs
- **OpenAI API**: https://platform.openai.com/docs

## License

MIT License - see LICENSE file for details

---

**Built with ❤️ using FastMCP, Auth0, and OpenAI**
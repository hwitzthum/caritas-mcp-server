# Caritas MCP Server

Secure MCP (Model Context Protocol) server providing authenticated access to OpenAI ChatGPT for your team, with Auth0 authentication.

## Features

- 🔐 **Auth0 Authentication**: Secure token-based authentication
- 🤖 **OpenAI Integration**: Access to GPT-4 and GPT-3.5 models
- 🌍 **Translation**: Multi-language support for Swiss organizations
- 📄 **Document Analysis**: Analyze and summarize documents
- 💬 **Chat & Conversations**: Single and multi-turn conversations
- 🛡️ **Security**: Input validation, rate limiting, and error sanitization

## Quick Start (Local Development)

### 1. Clone and Install

```bash
git clone <your-repo>
cd 1-Project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```bash
# Auth0 Configuration (get from https://manage.auth0.com/)
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_API_IDENTIFIER=https://your-api-identifier
AUTH0_ALGORITHMS=RS256

# OpenAI Configuration (get from https://platform.openai.com/)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000
```

### 3. Run the Server

```bash
python server.py
```

## Deploying to Render

### Prerequisites

- A [Render](https://render.com/) account
- Your code in a GitHub repository
- Auth0 application set up
- OpenAI API key

### Deployment Steps

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo>
   git push -u origin main
   ```

   **Important**: Make sure `.env` is in `.gitignore` (it already is!)

2. **Create a New Web Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **New +** → **Web Service**
   - Connect your GitHub repository
   - Configure:
     - **Name**: `caritas-mcp-server` (or your choice)
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python server.py`
     - **Region**: Choose closest to your users

3. **Set Environment Variables in Render**

   In your Render service settings → **Environment** tab, add:

   | Key | Value |
   |-----|-------|
   | `AUTH0_DOMAIN` | `your-tenant.auth0.com` |
   | `AUTH0_API_IDENTIFIER` | `https://your-api-identifier` |
   | `AUTH0_ALGORITHMS` | `RS256` |
   | `OPENAI_API_KEY` | `sk-your-openai-key` |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
   | `OPENAI_MAX_TOKENS` | `4000` |

4. **Update Auth0 Configuration**

   In your Auth0 dashboard, update the API identifier to match your Render URL:
   - If using custom domain: `https://your-domain.com`
   - Default Render URL: `https://caritas-mcp-server.onrender.com`

5. **Deploy**

   Render will automatically deploy your service. Monitor the logs for any errors.

### Verify Deployment

Test your deployed service:

```bash
curl https://your-service.onrender.com/health
```

## Architecture

### How It Works

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  MCP Server  │─────▶│   OpenAI    │
│ (with Auth0)│      │ (Render/Local)│      │     API     │
└─────────────┘      └──────────────┘      └─────────────┘
       │                     │
       │                     ▼
       │              ┌──────────────┐
       └─────────────▶│    Auth0     │
                      │ (Validation) │
                      └──────────────┘
```

### Environment Variable Loading

- **Local Development**: `.env` file (via `python-dotenv`)
- **Render Deployment**: Environment variables set in Render dashboard
- The `auth.py` module handles loading `.env` automatically
- On Render, `load_dotenv()` is a no-op (env vars already available)

## Security Best Practices

✅ **DO:**
- Set environment variables in Render dashboard
- Use different Auth0 credentials for dev/production
- Rotate your OpenAI API key regularly
- Monitor usage and costs in OpenAI dashboard
- Keep dependencies updated

❌ **DON'T:**
- Commit `.env` file to git (already in `.gitignore`)
- Share your API keys in chat/email
- Use production credentials for local testing
- Expose your Auth0 domain publicly

## API Tools

### Available MCP Tools

1. **`chat_with_gpt`** - Send a message to ChatGPT
2. **`multi_turn_conversation`** - Multi-turn conversation with context
3. **`analyze_document_with_gpt`** - Analyze and summarize documents
4. **`translate_text`** - Translate between languages
5. **`get_user_info`** - Get authenticated user information
6. **`health_check`** - Check server health (no auth required)

### Example Usage

```python
# Using the MCP client
result = client.call_tool(
    "chat_with_gpt",
    {
        "user_message": "What are best practices for social work?",
        "system_prompt": "You are an expert social worker",
        "auth_token": "Bearer YOUR_AUTH0_TOKEN"
    }
)
```

## Troubleshooting

### Local Development

**Error: `AUTH0_DOMAIN environment variable is required`**
- Make sure `.env` file exists and has correct values
- Verify `.env` is in the same directory as `server.py`

**Error: `OPENAI_API_KEY environment variable is required`**
- Check your `.env` file has `OPENAI_API_KEY` set
- Make sure the key starts with `sk-`

### Render Deployment

**Build Fails**
- Check your `requirements.txt` is complete
- Verify Python version compatibility

**Server Crashes on Startup**
- Check Render logs for specific error
- Verify all environment variables are set in Render dashboard
- Ensure Auth0 credentials are correct

**Auth0 Token Validation Fails**
- Update `AUTH0_API_IDENTIFIER` in `.env` to match your Render URL
- Check Auth0 dashboard API settings

## Support

For issues or questions:
1. Check the logs (locally: terminal, Render: dashboard logs)
2. Verify environment variables are set correctly
3. Test with `health_check` tool to verify connectivity

## License

MIT License - see LICENSE file for details
# Claude Desktop Configuration for Caritas MCP Server

## Step 1: Get Your Auth0 Access Token

First, you need to obtain an Auth0 access token. Run this command (replace with your Auth0 credentials):

```bash
curl --request POST \
  --url https://dev-tkf0h1lojy0to3kz.eu.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://caritas-mcp-server.onrender.com",
    "grant_type": "client_credentials"
  }'
```

You'll get a response like:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

Copy the `access_token` value.

---

## Step 2: Configure Claude Desktop

### Find Your Configuration File

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

---

## Step 3: Add MCP Server Configuration

Open the `claude_desktop_config.json` file and add your server configuration:

### Option A: With Token in Config (Simple but less secure)

```json
{
  "mcpServers": {
    "caritas-api": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://caritas-mcp-server.onrender.com/sse",
        "--header",
        "Authorization:Bearer YOUR_AUTH0_TOKEN_HERE"
      ]
    }
  }
}
```

**Note:** Replace `YOUR_AUTH0_TOKEN_HERE` with the actual token from Step 1. The `/sse` endpoint is required for Claude Desktop. Due to a bug in some platforms, avoid spaces around the colon (use `Authorization:Bearer` not `Authorization: Bearer`).

### Option B: With Token in Environment Variable (More secure - Recommended)

```json
{
  "mcpServers": {
    "caritas-api": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://caritas-mcp-server.onrender.com/sse",
        "--header",
        "Authorization:${AUTH_TOKEN}"
      ],
      "env": {
        "AUTH_TOKEN": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

**Replace `YOUR_TOKEN_HERE`** with the actual token from Step 1 (the "Bearer " prefix is already included in the env variable).

**Note:** The `/sse` endpoint is required for Claude Desktop compatibility via `mcp-remote`.

---

## Step 4: Restart Claude Desktop

After saving the configuration file, completely quit and restart Claude Desktop for the changes to take effect.

---

## Step 5: Test the Connection

In Claude Desktop, you should now be able to use the MCP tools. Try asking:

> "Use the health_check tool to verify the Caritas server is running"

Or:

> "Use chat_with_gpt to ask: What is the meaning of life?"

---

## Available MCP Tools

Once connected, you'll have access to these tools:

1. **chat_with_gpt** - Send messages to ChatGPT
2. **multi_turn_conversation** - Have conversations with context
3. **analyze_document_with_gpt** - Analyze documents up to 100k characters
4. **translate_text** - Translate text between languages
5. **health_check** - Check server status (no auth required)

---

## Troubleshooting

### "Connection refused" or "Server not responding"

1. Verify the server URL is correct: `https://caritas-mcp-server.onrender.com/mcp`
2. Check if the server is running in Render dashboard
3. Test with curl:
   ```bash
   curl https://caritas-mcp-server.onrender.com/mcp
   ```

### "Authentication failed" or "401 Unauthorized"

1. Your token may have expired (tokens typically last 24 hours)
2. Get a fresh token using the command in Step 1
3. Update the token in `claude_desktop_config.json`
4. Restart Claude Desktop

### "MCP server not found"

1. Make sure the configuration file is in the correct location
2. Check for JSON syntax errors (use a JSON validator)
3. Ensure Claude Desktop was fully restarted
4. Check Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`

---

## Token Refresh Script (Optional)

To avoid manually refreshing tokens, create a script:

**`refresh_token.sh`** (macOS/Linux):
```bash
#!/bin/bash

# Get new token from Auth0
TOKEN=$(curl -s --request POST \
  --url https://dev-tkf0h1lojy0to3kz.eu.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://caritas-mcp-server.onrender.com",
    "grant_type": "client_credentials"
  }' | jq -r '.access_token')

# Update Claude config
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
jq --arg token "$TOKEN" '.mcpServers."caritas-api".headers.Authorization = "Bearer \($token)"' "$CONFIG_FILE" > tmp.json && mv tmp.json "$CONFIG_FILE"

echo "Token refreshed successfully!"
```

Make it executable:
```bash
chmod +x refresh_token.sh
```

Run it whenever your token expires:
```bash
./refresh_token.sh
```

---

## Security Notes

⚠️ **Important:**
- The Auth0 token in your config file is like a password
- Keep your `claude_desktop_config.json` file secure
- Don't share your configuration file with others
- Tokens expire after 24 hours (configurable in Auth0)
- Consider using a dedicated Auth0 application for Claude Desktop

---

## Support

If you encounter issues:
1. Check the Render logs at: https://dashboard.render.com/
2. Verify environment variables are set in Render dashboard
3. Test the server directly with curl (see Troubleshooting section)
4. Check Claude Desktop logs for detailed error messages
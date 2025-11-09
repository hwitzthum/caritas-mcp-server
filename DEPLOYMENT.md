# Render Deployment Checklist

## Fixed Issues

✅ **Server now runs as HTTP server** (was stdio-only)
✅ **Added uvicorn** for production ASGI serving
✅ **Proper port binding** using `0.0.0.0` and `$PORT` env var
✅ **Environment variables loaded correctly** for both local and Render

## What Changed

### server.py
```python
# OLD (doesn't work on Render)
if __name__ == "__main__":
    mcp.run()  # stdio only

# NEW (works on Render)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    app = mcp.streamable_http_app()  # HTTP server
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### requirements.txt
Added:
- `uvicorn` - ASGI server for production

## Render Configuration

### Service Settings

| Setting | Value |
|---------|-------|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python server.py` |
| **Python Version** | 3.12 (or latest) |

### Environment Variables

**Required:**
- `AUTH0_DOMAIN` = `dev-tkf0h1lojy0to3kz.eu.auth0.com`
- `AUTH0_API_IDENTIFIER` = `https://caritas-mcp-server.onrender.com`
- `AUTH0_ALGORITHMS` = `RS256`
- `OPENAI_API_KEY` = `sk-your-key-here`
- `OPENAI_MODEL` = `gpt-4o-mini`
- `OPENAI_MAX_TOKENS` = `4000`

**Auto-set by Render:**
- `PORT` = (automatically assigned)

## Deploy Steps

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Fix Render deployment with HTTP server"
   git push
   ```

2. **Trigger Redeploy on Render:**
   - Go to your service dashboard
   - Click **Manual Deploy** → **Deploy latest commit**
   - Or push will auto-deploy if enabled

3. **Monitor Logs:**
   Watch for:
   ```
   INFO:     Starting MCP HTTP server on port 10000
   INFO:     Uvicorn running on http://0.0.0.0:10000
   INFO:     Application startup complete
   ```

4. **Test Deployment:**
   ```bash
   curl https://caritas-mcp-server.onrender.com/
   ```

## Expected Log Output (Success)

```
2025-01-09 10:00:00 - Starting MCP HTTP server on port 10000
2025-01-09 10:00:00 - INFO:     Started server process [1]
2025-01-09 10:00:00 - INFO:     Waiting for application startup.
2025-01-09 10:00:00 - INFO:     Application startup complete.
2025-01-09 10:00:00 - INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
```

## Troubleshooting

### If deployment still fails:

**Check Environment Variables:**
```bash
# In Render logs, verify env vars are loaded
echo $AUTH0_DOMAIN
echo $OPENAI_API_KEY
```

**Verify Build Success:**
- Build should show: `Build successful 🎉`
- All requirements should install without errors

**Check Start Command:**
- Must be exactly: `python server.py`
- Not just: `python` (this was the previous issue!)

## Testing After Deployment

1. **Health Check:**
   ```bash
   curl https://your-service.onrender.com/
   ```

2. **With Auth0 Token:**
   ```bash
   curl -X POST https://your-service.onrender.com/tools/health_check \
     -H "Content-Type: application/json"
   ```

## Need Help?

- **Render Logs:** Dashboard → Your Service → Logs
- **Build Logs:** Dashboard → Your Service → Events → Build
- **Runtime Logs:** Dashboard → Your Service → Logs (live)
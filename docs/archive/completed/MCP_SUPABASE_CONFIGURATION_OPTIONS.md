# MCP Supabase Configuration - All Options Tried

## Current Status: Still Not Working

We've tried multiple configuration methods, but the MCP server is still returning "Unauthorized".

## Configuration Methods Attempted

### 1. ✅ Environment File (`~/.config/supabase-mcp/.env`)
```bash
SUPABASE_ACCESS_TOKEN=sbp_960690c75b6fe22ccb7d671f19eb482af12703a0
```
**Status**: Created, but MCP server not reading it

### 2. ✅ Cursor Settings (`settings.json`)
```json
"claudeCode.environmentVariables": [
    {
        "key": "SUPABASE_ACCESS_TOKEN",
        "value": "sbp_960690c75b6fe22ccb7d671f19eb482af12703a0"
    }
]
```
**Status**: Added, but MCP server processes don't have it in their environment

### 3. ✅ Project Root `mcp.json`
```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase",
        "--access-token",
        "sbp_960690c75b6fe22ccb7d671f19eb482af12703a0"
      ]
    }
  }
}
```
**Status**: Created, but Cursor might not be reading it (uses built-in MCP server)

## The Problem

Cursor appears to be using a **built-in Supabase MCP server** that it manages automatically. The logs show:
```
Starting new stdio process with command: npx -y @supabase/mcp-server-supabase
```

It's not passing the `--access-token` argument, and it's not reading from environment variables.

## Possible Solutions

### Option 1: Configure Through Cursor UI
1. Open Cursor Settings (Cmd+,)
2. Search for "MCP" or "Model Context Protocol"
3. Find Supabase MCP server configuration
4. Add the access token there

### Option 2: Update Workspace Storage Config
Cursor stores MCP configurations in workspace storage. We might need to:
1. Find the workspace storage directory for this project
2. Update the `mcp-servers.json` file there
3. Add the Supabase server with the access token

### Option 3: Use Environment Variable in Shell
Set it as a system-wide environment variable that Cursor inherits:
```bash
# Add to ~/.zshrc or ~/.bash_profile
export SUPABASE_ACCESS_TOKEN=sbp_960690c75b6fe22ccb7d671f19eb482af12703a0
```

### Option 4: Check if Token is Valid
The token might be invalid or expired. Verify:
1. Go to: https://supabase.com/dashboard/account/tokens
2. Check if the token is still active
3. Generate a new token if needed

## Next Steps

1. **Check Cursor's MCP Settings UI** - Look for a way to configure MCP servers through the UI
2. **Verify Token** - Make sure the token is still valid
3. **Try System Environment Variable** - Set it in your shell profile
4. **Contact Cursor Support** - If none of the above work, this might be a Cursor-specific issue

---

**Last Updated**: 2025-11-22  
**Status**: Configuration complete, but MCP server still not authenticating






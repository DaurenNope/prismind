# MCP Supabase Troubleshooting - Current Status

## Configuration Attempts

### ✅ Completed
1. **Token saved to `~/.config/supabase-mcp/.env`**
   - File exists and has correct token
   - Permissions set to 600 (secure)

2. **Token added to Cursor settings.json**
   - Location: `~/Library/Application Support/Cursor/User/settings.json`
   - Added to `claudeCode.environmentVariables` array
   - Format: `{"key": "SUPABASE_ACCESS_TOKEN", "value": "sbp_..."}`

### ⚠️ Still Getting "Unauthorized"

The MCP server is still not picking up the token. Possible reasons:

1. **MCP Server needs reload**: Cursor's MCP server process may need to be restarted/reloaded
2. **Different configuration location**: Cursor might use a different config file for MCP servers
3. **Token format issue**: The token might need to be configured differently

## Next Steps to Try

### Option 1: Reload Cursor Window
1. In Cursor: `Cmd+Shift+P` → "Reload Window"
2. Test connection again

### Option 2: Check MCP Server Logs
```bash
cat ~/.local/share/supabase-mcp/mcp_server.log
```

### Option 3: Verify Token is Valid
1. Go to: https://supabase.com/dashboard/account/tokens
2. Check if token is still active
3. Verify token hasn't expired

### Option 4: Check Cursor's MCP Configuration
Cursor might have a separate MCP configuration file. Check:
- `~/Library/Application Support/Cursor/User/globalStorage/*/mcp_settings.json`
- Any workspace-specific MCP config files

### Option 5: Manual MCP Server Configuration
If Cursor uses a specific MCP config format, we might need to:
1. Find Cursor's MCP server configuration location
2. Add the token in the correct format for that config

## Current Configuration Locations

1. **Environment file**: `~/.config/supabase-mcp/.env`
   ```bash
   SUPABASE_ACCESS_TOKEN=sbp_960690c75b6fe22ccb7d671f19eb482af12703a0
   ```

2. **Cursor settings**: `~/Library/Application Support/Cursor/User/settings.json`
   ```json
   "claudeCode.environmentVariables": [
       {
           "key": "SUPABASE_ACCESS_TOKEN",
           "value": "sbp_960690c75b6fe22ccb7d671f19eb482af12703a0"
       }
   ]
   ```

## Token Information

- **Token**: `sbp_960690c75b6fe22ccb7d671f19eb482af12703a0`
- **Type**: Personal Access Token (PAT)
- **Source**: https://supabase.com/dashboard/account/tokens

---

**Last Updated**: 2025-11-22  
**Status**: Configuration complete, but MCP server not picking up token yet







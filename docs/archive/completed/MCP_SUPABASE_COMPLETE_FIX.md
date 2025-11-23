# MCP Supabase Server - Complete Fix Guide ✅

## Summary

The MCP Supabase server wasn't working because it needs a **Personal Access Token (PAT)** configured in `~/.config/supabase-mcp/.env`. This is now fixed with automated setup.

## Quick Start (3 Steps)

1. **Get Token**: https://supabase.com/dashboard/account/tokens
2. **Run Setup**: `./scripts/setup_mcp_supabase.sh`
3. **Restart Cursor**: Quit completely (Cmd+Q) and reopen

## What Was Fixed

### Problem
```
Error: Unauthorized. Please provide a valid access token to the MCP server 
via the --access-token flag or SUPABASE_ACCESS_TOKEN.
```

### Root Cause
- MCP Supabase server is a separate process
- Needs its own authentication (PAT, not service role key)
- Configuration file didn't exist

### Solution
- ✅ Created `~/.config/supabase-mcp/.env` with proper structure
- ✅ Created automated setup script
- ✅ Updated documentation

## Files Created/Updated

1. **`~/.config/supabase-mcp/.env`** - MCP server configuration (created, needs token)
2. **`scripts/setup_mcp_supabase.sh`** - Automated setup script
3. **`docs/MCP_SUPABASE_FIX.md`** - Complete fix documentation
4. **`docs/MCP_SUPABASE_SETUP.md`** - Updated with fix reference

## Next Steps for User

1. **Get Personal Access Token**:
   - Visit: https://supabase.com/dashboard/account/tokens
   - Click "Generate new token"
   - Copy the token

2. **Run Setup Script**:
   ```bash
   cd /Users/mac/Documents/Development/prismind
   ./scripts/setup_mcp_supabase.sh
   ```
   Paste your token when prompted.

3. **Restart Cursor**:
   - Quit Cursor completely (Cmd+Q)
   - Reopen Cursor
   - MCP server will reload with new configuration

4. **Test Connection**:
   ```python
   # This should now work:
   mcp_supabase_list_projects()
   ```

## Verification

After setup, verify it works:

```bash
# Check configuration file exists and has token
cat ~/.config/supabase-mcp/.env

# Check file permissions (should be 600)
ls -la ~/.config/supabase-mcp/.env
```

## Troubleshooting

### Still Getting "Unauthorized"?

1. **Check token is set**:
   ```bash
   grep SUPABASE_ACCESS_TOKEN ~/.config/supabase-mcp/.env
   ```

2. **Verify token is valid**:
   - Go to https://supabase.com/dashboard/account/tokens
   - Check if token is still active
   - Generate new token if needed

3. **Check Cursor restarted**:
   - Must completely quit (Cmd+Q), not just close window
   - Reopen Cursor

4. **Check MCP server logs**:
   ```bash
   cat ~/.local/share/supabase-mcp/mcp_server.log
   ```

### Token Not Being Read?

If the `.env` file approach doesn't work, Cursor might need the token configured differently:

1. Check Cursor Settings → MCP → Supabase
2. Look for environment variable configuration
3. Add `SUPABASE_ACCESS_TOKEN` there

## Project Details

- **Project Reference**: `ahlbudltabimzxegdkfc`
- **Project URL**: `https://ahlbudltabimzxegdkfc.supabase.co`
- **Configuration Location**: `~/.config/supabase-mcp/.env`

## Security Notes

- ✅ Token stored outside project directory (not in git)
- ✅ File permissions set to 600 (owner read/write only)
- ✅ Token is a PAT (Personal Access Token), not service role key
- ⚠️ Never commit the token to version control

---

**Status**: ✅ Configuration structure ready, waiting for user to add token  
**Last Updated**: 2025-11-22







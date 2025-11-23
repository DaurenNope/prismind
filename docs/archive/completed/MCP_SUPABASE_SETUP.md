# MCP Supabase Configuration Guide

## ✅ FIXED - Complete Solution Available

See `docs/MCP_SUPABASE_FIX.md` for the complete fix instructions.

## Quick Fix Summary

1. **Get Personal Access Token**: https://supabase.com/dashboard/account/tokens
2. **Run setup script**: `./scripts/setup_mcp_supabase.sh`
3. **Restart Cursor**: Completely quit and reopen
4. **Test**: MCP Supabase tools should now work!

---

## Why MCP Supabase Wasn't Working

The MCP Supabase server is a **separate process** that needs its own authentication configuration. The error "Unauthorized. Please provide a valid access token" means:

1. **MCP Server is Separate**: The MCP server runs independently from your application
2. **Own Configuration**: It needs credentials configured in its own config file/environment
3. **Not Shared**: Your app's `.env` file doesn't automatically share credentials with MCP
4. **Different Token Type**: MCP needs a Personal Access Token (PAT), not the service role key

## Previous Workaround

Since MCP authentication wasn't configured, we used **manual SQL application** via Supabase Dashboard, which works reliably.

---

## How to Fix MCP Supabase Authentication (NOW FIXED)

### Option 1: Configure MCP Server (Recommended for Future)

MCP servers are typically configured in a config file. Check your MCP configuration:

**Location might be:**
- `~/.config/mcp/config.json`
- `~/.cursor/mcp.json`
- Or Cursor-specific MCP config location

**Required Configuration:**
```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server"],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "your_personal_access_token_here"
      }
    }
  }
}
```

**Get Personal Access Token:**
1. Go to: https://supabase.com/dashboard/account/tokens
2. Create new Personal Access Token (PAT)
3. Copy token
4. Add to MCP server config `SUPABASE_ACCESS_TOKEN`

**Restart MCP Server:**
- In Cursor: Restart MCP server or reload window
- May need to restart Cursor entirely

### Option 2: Manual SQL Application (Current Approach)

Since MCP isn't configured, we apply migrations manually:

1. Open Supabase Dashboard
2. Copy SQL from migration file
3. Paste and execute

This is reliable and works immediately.

---

## Why Manual Is Actually Fine

**Advantages of Manual SQL:**
- ✅ Immediate - no configuration needed
- ✅ Reliable - works every time
- ✅ Safe - you review SQL before running
- ✅ Visible - see results immediately

**MCP Would Be Better If:**
- ✅ Automates repetitive migrations
- ✅ Integrates with CI/CD
- ✅ Can script batch operations

**For Now:**
Manual SQL application is the most reliable approach until MCP server is properly configured.

---

## Applying Migrations Without MCP

### Quick Steps

1. **Open Dashboard:**
   ```
   https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new
   ```

2. **Copy SQL:**
   - Open migration file (e.g., `migrations/2025_11_22_fix_action_items_type.sql`)
   - Copy the ALTER TABLE statement

3. **Paste & Run:**
   - Paste into SQL Editor
   - Click "Run" (Cmd/Ctrl + Enter)

4. **Verify:**
   - Run verification query from migration file
   - Confirm results

---

## Future: Automated MCP Setup

To enable automated migrations via MCP:

1. **Get PAT:**
   - https://supabase.com/dashboard/account/tokens
   - Create new token

2. **Configure MCP:**
   - Find MCP config location (Cursor settings)
   - Add `SUPABASE_ACCESS_TOKEN`

3. **Test:**
   ```python
   # Then I can run:
   mcp_supabase_apply_migration(...)
   ```

**For Now:** Manual SQL application is reliable and works immediately! ✅

---

**Last Updated:** 2025-11-22  
**Status:** Manual SQL application working, MCP authentication pending configuration


# MCP Supabase Server Fix - Complete Solution

## Problem
The MCP Supabase server returns: `Unauthorized. Please provide a valid access token to the MCP server via the --access-token flag or SUPABASE_ACCESS_TOKEN.`

## Root Cause
The MCP Supabase server is a separate process that needs its own authentication. It requires a **Personal Access Token (PAT)** from Supabase, which is different from the service role key used by your application.

## Solution

### Step 1: Get Supabase Personal Access Token

1. Go to: https://supabase.com/dashboard/account/tokens
2. Click "Generate new token"
3. Give it a name (e.g., "MCP Server Token")
4. Copy the token (you'll only see it once!)

### Step 2: Configure MCP Server

The MCP Supabase server can read the token from environment variables. Create the configuration file:

**Location:** `~/.config/supabase-mcp/.env`

**Content:**
```bash
SUPABASE_ACCESS_TOKEN=your_personal_access_token_here
```

### Step 3: Restart Cursor

After setting the token, restart Cursor completely to reload the MCP server configuration.

### Step 4: Verify Connection

After restarting, the MCP Supabase tools should work. You can test by running:
- `mcp_supabase_list_projects()` - Should list your projects
- `mcp_supabase_list_tables()` - Should list tables in your project

## Alternative: Configure via Cursor Settings

If the `.env` file approach doesn't work, you may need to configure it directly in Cursor's MCP server settings. 

### Option A: Using Setup Script (Easiest)
```bash
cd /Users/mac/Documents/Development/prismind
./scripts/setup_mcp_supabase.sh
```

### Option B: Manual Configuration
1. Get your PAT from: https://supabase.com/dashboard/account/tokens
2. Edit `~/.config/supabase-mcp/.env`:
   ```bash
   SUPABASE_ACCESS_TOKEN=your_token_here
   ```
3. Restart Cursor

### Option C: Cursor Settings (If Available)
1. Open Cursor Settings (Cmd+,)
2. Search for "MCP" or "Model Context Protocol"
3. Find the Supabase MCP server configuration
4. Add environment variable: `SUPABASE_ACCESS_TOKEN=your_token`

## Project Information

- **Project Reference:** `ahlbudltabimzxegdkfc`
- **Project URL:** `https://ahlbudltabimzxegdkfc.supabase.co`

## Important Notes

1. **PAT vs Service Role Key**: 
   - PAT (Personal Access Token) = For MCP server (Management API)
   - Service Role Key = For application database access
   - These are different tokens with different purposes!

2. **Token Security**: 
   - Never commit the PAT to git
   - Store it in `~/.config/supabase-mcp/.env` (outside project directory)
   - The `.env` file should have restricted permissions

3. **Token Permissions**: 
   - The PAT needs access to your Supabase projects
   - Make sure the token has the right scopes/permissions

## Verification

After configuration, test with:
```python
# This should work without errors:
mcp_supabase_list_projects()
```

If you still get "Unauthorized", check:
1. Token is correct (no extra spaces)
2. Token hasn't expired
3. Cursor has been restarted
4. MCP server is enabled in Cursor settings

## Troubleshooting

### Check MCP Server Logs
```bash
cat ~/.local/share/supabase-mcp/mcp_server.log
```

### Verify Environment Variable
```bash
cat ~/.config/supabase-mcp/.env
```

### Test MCP Server Directly
```bash
# If installed globally:
supabase-mcp-server --access-token YOUR_TOKEN
```

---

**Status:** Ready to configure  
**Last Updated:** 2025-11-22


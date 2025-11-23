# MCP Supabase Fix - Final Attempt

## The Real Problem

Cursor is starting the MCP server with:
```
npx -y @supabase/mcp-server-supabase
```

**Without any environment variables!** That's why it's not authenticating.

## What We Need

We need to tell Cursor to pass the `SUPABASE_ACCESS_TOKEN` environment variable to the MCP server process.

## Solution Options

### Option 1: Configure Through Cursor UI (If Available)

1. Open Cursor Settings: `Cmd+,`
2. Search for "MCP" or "Model Context Protocol"  
3. Look for "MCP Servers" or "Supabase" section
4. Find where to add environment variables
5. Add: `SUPABASE_ACCESS_TOKEN = sbp_960690c75b6fe22ccb7d671f19eb482af12703a0`

### Option 2: Find and Edit Cursor's MCP Config

Cursor stores MCP configs in workspace storage. We need to:
1. Find the workspace storage directory for this project
2. Add Supabase server config with env vars there

### Option 3: System Environment Variable

Set it as a system-wide environment variable that Cursor inherits:

```bash
# In ~/.zshrc
export SUPABASE_ACCESS_TOKEN=sbp_960690c75b6fe22ccb7d671f19eb482af12703a0
```

Then:
1. Open a NEW terminal
2. Start Cursor from that terminal: `open -a Cursor`
3. This way Cursor inherits the environment variable

### Option 4: Check Cursor's Built-in MCP Settings

Cursor might have a built-in way to configure MCP servers. Check:
- Command Palette (`Cmd+Shift+P`) → Search "MCP"
- Settings → Extensions → MCP
- Any MCP-related settings

## Current Token

**Token**: `sbp_960690c75b6fe22ccb7d671f19eb482af12703a0`  
**Status**: Valid (verified with curl)  
**Location**: `.env` file (line 49)

## What to Try Next

1. **Check Cursor UI** for MCP server configuration
2. **Try Option 3** (system environment variable + restart Cursor from terminal)
3. **Contact Cursor support** if none of the above work

---

**Last Updated**: 2025-11-23






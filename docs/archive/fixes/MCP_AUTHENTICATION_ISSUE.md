# MCP Supabase Authentication Issue - Root Cause

## The Problem

Cursor is starting the MCP Supabase server with:
```
npx -y @supabase/mcp-server-supabase
```

**Without passing any environment variables**, even though we've configured the token in multiple places.

## What We've Tried

1. ✅ Token in `.env` file
2. ✅ Token in `mcp.json` (project root)
3. ✅ Token in `~/.config/supabase-mcp/.env`
4. ✅ Token in Cursor's `settings.json` (`claudeCode.environmentVariables`)
5. ✅ Token in `~/.zshrc` and `~/.bash_profile`
6. ✅ Token in `launchctl` (system-wide)

**None of these are being read by Cursor's MCP server process.**

## The Real Issue

Cursor has a **built-in MCP server manager** that:
- Automatically detects and starts MCP servers
- Does NOT read from `mcp.json` files
- Does NOT inherit environment variables from shell
- Does NOT read from Cursor's `settings.json` environment variables

## Possible Solutions

### Option 1: Find Cursor's MCP Configuration UI

Cursor might have a UI for configuring MCP servers:
1. Open Settings (`Cmd+,`)
2. Search for "MCP" or "Model Context Protocol"
3. Look for MCP server configuration
4. Add Supabase server with environment variables there

### Option 2: Check Cursor's Command Palette

1. Press `Cmd+Shift+P`
2. Search for "MCP" or "Configure MCP"
3. See if there's a command to configure MCP servers

### Option 3: Contact Cursor Support

This might be a limitation of how Cursor manages MCP servers. They might need to:
- Add support for reading `mcp.json` files
- Add support for environment variables in MCP server config
- Provide a UI for configuring MCP servers

## Current Status

- ✅ MCP server is connected (29 tools available)
- ✅ Token is valid (verified with curl)
- ❌ Token is not being passed to MCP server process
- ⚠️ Some tools work (`get_project_url`), most don't

## Workaround

Since `get_project_url` works, the connection is there. The issue is authentication for most operations. 

**For now, you can:**
- Use Supabase Dashboard for migrations
- Use direct SQL execution in Supabase Dashboard
- Wait for Cursor to fix MCP server environment variable support

---

**Last Updated**: 2025-11-23  
**Status**: Blocked by Cursor's MCP server management






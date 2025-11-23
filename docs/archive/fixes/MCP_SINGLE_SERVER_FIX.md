# MCP Supabase - Single Server Configuration

## Issue

Cursor only shows **one Supabase server** in the dashboard, and it's using `@supabase/mcp-server-supabase` which isn't picking up the authentication token.

## Solution

Since Cursor only recognizes one Supabase server, I've replaced it with `mcp-supabase-db` which:
- Has better database-focused features
- May handle authentication differently
- Passes credentials as command-line arguments (more reliable)

## New Configuration

**File**: `/Users/mac/Documents/Development/prismind/mcp.json`

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-supabase-db",
        "--supabase-url",
        "https://ahlbudltabimzxegdkfc.supabase.co",
        "--access-token",
        "sbp_960690c75b6fe22ccb7d671f19eb482af12703a0"
      ]
    }
  }
}
```

**Key Changes**:
- Using `mcp-supabase-db` instead of `@supabase/mcp-server-supabase`
- Passing credentials as **command-line arguments** (more reliable than env vars)
- Single server named "supabase" (matches what Cursor expects)

## Next Steps

1. **Restart Cursor** completely (`Cmd+Q` and reopen)
2. **Check MCP Dashboard** - Should still show one "supabase" server
3. **Test authentication** - The new server should pick up the token from command-line args

## Why This Should Work

Command-line arguments are more reliable than environment variables because:
- They're explicitly passed to the process
- Don't depend on shell environment
- Cursor's MCP manager should pass them through

---

**Last Updated**: 2025-11-23





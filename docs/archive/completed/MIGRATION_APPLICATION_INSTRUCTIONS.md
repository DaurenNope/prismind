# Migration Application Instructions

**Migration**: Add `action_items` Column to Posts Table  
**File**: `migrations/2025_11_22_add_action_items_column.sql`  
**Status**: ⚠️ Requires manual application

---

## Overview

The `action_items` column migration needs to be applied to your Supabase database. The Supabase MCP server requires authentication, so the migration must be applied manually through the Supabase dashboard.

---

## Steps to Apply Migration

### Option 1: Supabase Dashboard (Recommended)

1. **Open Supabase Dashboard**:
   - Go to: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new
   - Or navigate to: Your Project → SQL Editor → New Query

2. **Copy Migration SQL**:
   - Open the file: `migrations/2025_11_22_add_action_items_column.sql`
   - Copy the entire SQL content

3. **Paste and Execute**:
   - Paste the SQL into the SQL Editor
   - Click "Run" or press `Ctrl+Enter` (Mac: `Cmd+Enter`)
   - Wait for execution to complete

4. **Verify Migration**:
   - Run the verification query at the bottom of the migration file
   - Should show: `data_type = 'ARRAY', udt_name = '_text'`

### Option 2: Command Line (if Supabase CLI is installed)

```bash
# If you have Supabase CLI installed and configured
supabase db execute migrations/2025_11_22_add_action_items_column.sql
```

---

## Migration SQL

The migration does the following:

1. **Adds the column** (if it doesn't exist):
   ```sql
   ALTER TABLE public.posts 
   ADD COLUMN IF NOT EXISTS action_items TEXT[];
   ```

2. **Converts existing TEXT column** to TEXT[] (if it exists as TEXT):
   - Handles NULL values → empty array
   - Handles empty strings → empty array
   - Handles JSON array strings → parsed array
   - Handles single strings → array with one element

---

## Verification

After applying the migration, verify it worked:

```sql
-- Check column exists and type is correct
SELECT 
    column_name, 
    data_type,
    udt_name
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
  AND column_name = 'action_items';
```

**Expected Result**:
- `data_type` = `'ARRAY'`
- `udt_name` = `'_text'`

---

## Next Steps After Migration

Once the migration is applied:

1. **Re-analyze posts**:
   ```bash
   python scripts/validation/re_analyze_posts.py --limit 10
   ```

2. **Run validation**:
   ```bash
   python scripts/validation/system_validation.py
   ```

3. **Check logs** for successful `action_items` population:
   - Should see: `action_items: ✅ (X items)` in logs

---

## Troubleshooting

### Error: Column already exists
- **Solution**: The migration uses `ADD COLUMN IF NOT EXISTS`, so this should be safe
- If you see this error, the column might already exist with wrong type - the migration should convert it

### Error: Permission denied
- **Solution**: Ensure you're using the service role key or have proper permissions
- Check your Supabase project settings

### Migration succeeds but action_items still empty
- **Solution**: Re-analyze posts after migration:
  ```bash
  python scripts/validation/re_analyze_posts.py --limit 10 --force
  ```

---

## Migration File Location

```
migrations/2025_11_22_add_action_items_column.sql
```

---

**Status**: Migration SQL ready. Please apply manually via Supabase dashboard.







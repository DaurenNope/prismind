# How to Fix Supabase Sync Issues

## Current Situation

The application is trying to insert data with fields that don't exist in your Supabase table schema. This causes sync failures, but data is still safely stored in the local SQLite database.

## Solution

You need to update your Supabase table schema to include all the fields that the application is trying to insert.

## Steps to Fix

1. **Apply the schema update**:
   Run the SQL commands in `supabase_schema_update.sql` to add the missing columns to your posts table:

   ```sql
   ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS content_summary TEXT;
   ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS action_items TEXT;
   ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS insights TEXT;
   ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS recommendations TEXT;
   ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS educational_value TEXT;
   -- ... and all other missing columns
   ```

2. **Alternative approach**:
   If you prefer to keep your current schema and modify the application to work with it, you can:
   - Update the application code to only send fields that exist in your schema
   - Modify the field mapping in `src/services/database_operations.py`

## Why This Happens

The application was designed to work with a more extensive schema that includes fields for AI analysis results, content insights, and other metadata. Your current schema is more minimal and doesn't include these fields.

## Verification

After updating your schema:
1. Restart your application
2. Run a collection process
3. Check that you no longer see "schema cache" errors
4. Verify that data is being inserted into both SQLite and Supabase

## Important Notes

- The local SQLite database is the primary storage - data is always saved there first
- Supabase is a secondary sync - it's an additional backup/storage option
- Even with sync failures, your data collection is working correctly
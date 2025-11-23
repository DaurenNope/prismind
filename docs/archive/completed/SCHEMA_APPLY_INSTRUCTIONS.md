# Applying the Final Schema Migration

## Quick Apply (Recommended)

1. **Open Supabase Dashboard**: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc
2. **Go to SQL Editor** (left sidebar)
3. **Click "New Query"**
4. **Copy and paste** the entire contents of `migrations/2025_11_04_final_schema.sql`
5. **Click "Run"** (or press Cmd/Ctrl + Enter)

## Verify Migration Success

After running, you should see a query result showing all the new columns. The migration uses `ADD COLUMN IF NOT EXISTS`, so it's safe to run multiple times.

## Expected Columns Added

The migration adds these essential fields:

### Rewrite-Focused Fields:
- `rewrite_score` (numeric)
- `rewrite_readiness` (text)
- `rewrite_reasons` (text[])
- `rewrite_risks` (text[])
- `analysis_confidence` (numeric)
- `analysis_depth` (text)
- `needs_deep_analysis` (boolean)

### Persona-Aware Scoring:
- `persona_fit_scores` (jsonb)
- `persona_fit_reasons` (jsonb)
- `best_persona_key` (text)
- `best_persona_score` (numeric)
- `best_persona_reasons` (text[])

## After Migration

Once the migration is applied:
1. ✅ Analyzer will start saving all fields correctly
2. ✅ PostInserter is already updated to include these fields
3. ✅ No code changes needed - just restart your analyzer

## Troubleshooting

If you get permission errors:
- Make sure you're using the SQL Editor (has admin access)
- If using service role key, ensure it has proper permissions





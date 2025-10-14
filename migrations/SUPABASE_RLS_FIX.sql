-- ============================================================================
-- Supabase RLS Fix for PrisMind
-- ============================================================================
-- This script fixes Row-Level Security policies to allow post inserts
-- Run this in your Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql
-- ============================================================================

-- Step 1: Drop any existing restrictive policies
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.posts;
DROP POLICY IF EXISTS "Enable read access for all users" ON public.posts;
DROP POLICY IF EXISTS "Users can insert posts" ON public.posts;
DROP POLICY IF EXISTS "Users can read posts" ON public.posts;

-- Step 2: Create permissive policies that allow all operations
-- This allows your service role key to insert/update/delete posts

-- Allow ALL operations (insert, update, delete, select)
CREATE POLICY "Allow all operations" 
ON public.posts 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- ============================================================================
-- Verification Query (run this after the policy is created)
-- ============================================================================

-- Check that the policy was created
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies 
WHERE tablename = 'posts';

-- ============================================================================
-- Alternative: More Secure Policy (if you want to restrict by role)
-- ============================================================================
-- If you want to be more restrictive, comment out the "Allow all operations" 
-- policy above and uncomment these instead:

-- CREATE POLICY "Service role can do anything"
-- ON public.posts
-- FOR ALL
-- TO service_role
-- USING (true)
-- WITH CHECK (true);

-- CREATE POLICY "Authenticated users can insert"
-- ON public.posts
-- FOR INSERT
-- TO authenticated
-- WITH CHECK (true);

-- CREATE POLICY "Anyone can read"
-- ON public.posts
-- FOR SELECT
-- TO authenticated, anon
-- USING (true);

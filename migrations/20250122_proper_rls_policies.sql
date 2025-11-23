-- ============================================================================
-- Proper Row-Level Security Policies for PrisMind
-- ============================================================================
-- This migration implements proper RLS policies that distinguish between
-- service role (full access) and authenticated users (read-only).
-- Replaces the overly permissive "Allow all operations" policy.
-- ============================================================================
-- Run this in your Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql
-- ============================================================================

-- Step 1: Drop existing overly permissive policies
DROP POLICY IF EXISTS "Allow all operations" ON public.posts;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.posts;
DROP POLICY IF EXISTS "Enable read access for all users" ON public.posts;
DROP POLICY IF EXISTS "Users can insert posts" ON public.posts;
DROP POLICY IF EXISTS "Users can read posts" ON public.posts;
DROP POLICY IF EXISTS "Service role can do anything" ON public.posts;

-- Step 2: Enable RLS on posts table (if not already enabled)
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

-- Step 3: Create proper policies

-- Service role policy: Full access (for backend services)
-- The service role key has elevated permissions and can perform all operations
CREATE POLICY "Service role full access"
ON public.posts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Authenticated users policy: Read-only access
-- Regular authenticated users can only read posts, not modify them
CREATE POLICY "Authenticated users read only"
ON public.posts
FOR SELECT
TO authenticated
USING (true);

-- Anonymous users: No access by default
-- (If you need anonymous read access, uncomment the policy below)
-- CREATE POLICY "Anonymous read access"
-- ON public.posts
-- FOR SELECT
-- TO anon
-- USING (true);

-- ============================================================================
-- Verification Queries (run after applying policies)
-- ============================================================================

-- Check that RLS is enabled
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'posts';

-- Check all policies on posts table
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'posts'
ORDER BY policyname;

-- Test policy effectiveness (should only return rows for service_role)
-- This query should work with service_role key but not with anon key
SELECT COUNT(*) as post_count FROM public.posts;

-- ============================================================================
-- Notes
-- ============================================================================
-- 
-- Service Role Key:
--   - Has full access to all tables
--   - Bypasses RLS when used correctly
--   - Should be used by backend services only
--   - Never expose in client-side code
--
-- Authenticated Users:
--   - Can only SELECT (read) posts
--   - Cannot INSERT, UPDATE, or DELETE
--   - Protected by RLS policies
--
-- Anonymous Users:
--   - No access by default (secure)
--   - Uncomment anonymous policy if public read access is needed
--
-- To allow specific authenticated users to insert posts:
--   CREATE POLICY "Authenticated users insert"
--   ON public.posts
--   FOR INSERT
--   TO authenticated
--   WITH CHECK (true);
--
-- ============================================================================







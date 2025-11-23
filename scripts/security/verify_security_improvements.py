#!/usr/bin/env python3
"""
Security Improvements Verification Script
Verifies that all security improvements have been properly implemented.
"""

import os
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()


def extract_project_ref_from_url(url: str) -> str:
    """Extract project reference from Supabase URL"""
    if not url:
        return None
    
    # Supabase URLs are typically: https://<project-ref>.supabase.co
    pattern = r"https://([a-zA-Z0-9]+)\.supabase\.co"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def verify_sql_injection_fixes():
    """Verify SQL injection fixes in search_methods.py"""
    print("\n🔍 Verifying SQL Injection Fixes...")
    
    file_path = project_root / "src" / "core" / "research" / "search_methods.py"
    if not file_path.exists():
        # Try alternative path
        file_path = Path(__file__).resolve().parents[3] / "src" / "core" / "research" / "search_methods.py"
    
    if not file_path.exists():
        print("❌ File not found: search_methods.py")
        return False
    
    content = file_path.read_text()
    
    # Check for vulnerable patterns
    vulnerable_patterns = [
        r'LIMIT\s+\{.*\}',  # String interpolation in LIMIT
        r'LIMIT\s+f".*"',   # f-string in LIMIT
        r'LIMIT\s+%.*%',    # Format string in LIMIT
    ]
    
    vulnerable_found = False
    for pattern in vulnerable_patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"❌ Found vulnerable LIMIT pattern: {matches}")
            vulnerable_found = True
    
    # Check for secure patterns
    secure_pattern = r'LIMIT\s+\?'  # Parameterized LIMIT
    secure_matches = len(re.findall(secure_pattern, content))
    
    if secure_matches >= 4:
        print(f"✅ Found {secure_matches} parameterized LIMIT clauses")
        if not vulnerable_found:
            print("✅ No vulnerable LIMIT patterns found")
            return True
    else:
        print(f"⚠️  Only found {secure_matches} parameterized LIMIT clauses (expected 4+)")
    
    return not vulnerable_found


def verify_authentication_enforcement():
    """Verify production authentication enforcement"""
    print("\n🔍 Verifying Authentication Enforcement...")
    
    file_path = project_root / "src" / "api" / "auth.py"
    
    if not file_path.exists():
        print("❌ File not found: auth.py")
        return False
    
    content = file_path.read_text()
    
    # Check for production detection
    has_production_check = "_is_production" in content or "is_production" in content
    has_production_fail = "PRODUCTION MODE" in content or "500" in content or "Internal Server Error" in content
    
    if has_production_check and has_production_fail:
        print("✅ Production authentication enforcement found")
        return True
    else:
        print("⚠️  Production authentication enforcement not found")
        return False


def verify_rate_limiting():
    """Verify rate limiting enforcement"""
    print("\n🔍 Verifying Rate Limiting Enforcement...")
    
    file_path = project_root / "src" / "api" / "main.py"
    
    if not file_path.exists():
        print("❌ File not found: main.py")
        return False
    
    content = file_path.read_text()
    
    # Check for rate limiting enforcement
    has_limiter = "Limiter" in content
    has_production_check = "PRODUCTION MODE" in content and "slowapi" in content.lower()
    has_default_limits = 'default_limits' in content or '"100/minute"' in content
    
    if has_limiter and has_production_check and has_default_limits:
        print("✅ Rate limiting enforcement found")
        return True
    else:
        print("⚠️  Rate limiting enforcement may be incomplete")
        return False


def verify_security_headers():
    """Verify security headers middleware"""
    print("\n🔍 Verifying Security Headers...")
    
    file_path = project_root / "src" / "api" / "main.py"
    
    if not file_path.exists():
        print("❌ File not found: main.py")
        return False
    
    content = file_path.read_text()
    
    # Check for security headers
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Content-Security-Policy",
        "Strict-Transport-Security",
    ]
    
    headers_found = []
    for header in required_headers:
        if header in content:
            headers_found.append(header)
    
    if len(headers_found) >= 4:
        print(f"✅ Found {len(headers_found)} security headers: {', '.join(headers_found)}")
        return True
    else:
        print(f"⚠️  Only found {len(headers_found)} security headers (expected 4+)")
        return False


def verify_rls_migration():
    """Verify RLS migration file exists"""
    print("\n🔍 Verifying RLS Migration...")
    
    migration_file = project_root / "migrations" / "20250122_proper_rls_policies.sql"
    
    if not migration_file.exists():
        print("❌ RLS migration file not found: 20250122_proper_rls_policies.sql")
        return False
    
    content = migration_file.read_text()
    
    # Check for proper policies
    has_service_role = "Service role full access" in content
    has_authenticated = "Authenticated users read only" in content
    has_drop_permissive = '"Allow all operations"' in content
    
    if has_service_role and has_authenticated and has_drop_permissive:
        print("✅ RLS migration file found with proper policies")
        return True
    else:
        print("⚠️  RLS migration file may be incomplete")
        return False


def get_supabase_project_info():
    """Get Supabase project information for MCP verification"""
    print("\n🔍 Gathering Supabase Project Information...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url:
        print("⚠️  SUPABASE_URL not found in environment")
        return None, None
    
    project_ref = extract_project_ref_from_url(supabase_url)
    
    if project_ref:
        print(f"✅ Found Supabase project reference: {project_ref}")
        print(f"   URL: {supabase_url}")
        if supabase_key:
            print(f"   Key: {supabase_key[:10]}... (redacted)")
        else:
            print("   ⚠️  No API key found")
        return project_ref, supabase_url
    else:
        print(f"⚠️  Could not extract project reference from URL: {supabase_url}")
        return None, None


def print_supabase_mcp_verification_guide(project_ref: str):
    """Print guide for verifying with Supabase MCP"""
    if not project_ref:
        print("\n⚠️  Cannot provide MCP verification guide - project reference not found")
        return
    
    print("\n" + "=" * 70)
    print("📋 Supabase MCP Verification Guide")
    print("=" * 70)
    
    print(f"\n1. Verify RLS Policies are Applied:")
    print(f"   Run this SQL in Supabase SQL Editor:")
    print(f"   https://supabase.com/dashboard/project/{project_ref}/sql/new")
    print(f"\n   SQL Query:")
    print(f"   SELECT policyname, permissive, roles, cmd")
    print(f"   FROM pg_policies")
    print(f"   WHERE tablename = 'posts'")
    print(f"   ORDER BY policyname;")
    
    print(f"\n2. Check Security Advisors:")
    print(f"   Use Supabase MCP: mcp_supabase_get_advisors")
    print(f"   project_id: {project_ref}")
    print(f"   type: security")
    
    print(f"\n3. Verify RLS is Enabled:")
    print(f"   SQL Query:")
    print(f"   SELECT schemaname, tablename, rowsecurity")
    print(f"   FROM pg_tables")
    print(f"   WHERE schemaname = 'public' AND tablename = 'posts';")
    
    print(f"\n4. Test Policies:")
    print(f"   - Service role should have full access")
    print(f"   - Authenticated users should only have SELECT access")
    print(f"   - Anonymous users should have no access")
    
    print("=" * 70)


def main():
    """Run all verification checks"""
    print("=" * 70)
    print("🔒 Security Improvements Verification")
    print("=" * 70)
    
    results = {}
    
    # Run all checks
    results["sql_injection"] = verify_sql_injection_fixes()
    results["authentication"] = verify_authentication_enforcement()
    results["rate_limiting"] = verify_rate_limiting()
    results["security_headers"] = verify_security_headers()
    results["rls_migration"] = verify_rls_migration()
    
    # Get Supabase info
    project_ref, supabase_url = get_supabase_project_info()
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Verification Summary")
    print("=" * 70)
    
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check.replace('_', ' ').title():30} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ All security improvements verified!")
    else:
        print("\n⚠️  Some security improvements need attention")
    
    # Print MCP verification guide
    if project_ref:
        print_supabase_mcp_verification_guide(project_ref)
    
    # Print next steps
    print("\n" + "=" * 70)
    print("📝 Next Steps")
    print("=" * 70)
    print("1. Apply RLS migration in Supabase SQL Editor")
    print("2. Verify RLS policies with SQL queries above")
    print("3. Check security advisors via Supabase MCP")
    print("4. Test authentication in production environment")
    print("5. Verify rate limiting is active")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())


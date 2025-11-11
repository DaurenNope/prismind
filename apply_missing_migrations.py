#!/usr/bin/env python3
"""
Apply missing database migrations
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

migrations = [
    "migrations/2025_11_04_user_preferences.sql",
    "migrations/2025_11_10_rewrite_feedback.sql"
]

print("🔧 Applying missing migrations...\n")

for migration_path in migrations:
    path = Path(migration_path)
    if not path.exists():
        print(f"⚠️  Migration not found: {migration_path}")
        continue

    print(f"📄 Applying {path.name}...")

    with open(path, 'r') as f:
        sql = f.read()

    try:
        # Execute SQL using Supabase RPC
        result = client.rpc('exec', {'sql': sql}).execute()
        print(f"✅ Applied {path.name}")
    except Exception as e:
        # If RPC doesn't work, try direct query
        print(f"⚠️  RPC failed, trying direct execution...")
        try:
            # Split by statement and execute each
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for stmt in statements:
                if stmt:
                    client.postgrest.rpc('query', {'sql': stmt}).execute()
            print(f"✅ Applied {path.name}")
        except Exception as e2:
            print(f"❌ Failed to apply {path.name}: {e2}")
            print(f"\n📋 Please apply manually via Supabase SQL Editor:")
            print(f"   1. Go to https://supabase.com/dashboard")
            print(f"   2. Open SQL Editor")
            print(f"   3. Copy and paste from: {migration_path}")
            print(f"   4. Click Run\n")

print("\n✅ Migration check complete!")
print("\n💡 If any migrations failed, apply them manually via Supabase SQL Editor.")
print("   The app will work fine without them, but some features may be limited.")

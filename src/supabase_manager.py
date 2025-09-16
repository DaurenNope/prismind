import scripts.supabase_manager as _s

# Re-export commonly used symbols and bind module-level names so test patches work
SupabaseManager = _s.SupabaseManager
# Expose create_client even if not defined in shim originally
try:
    create_client = _s.create_client
except AttributeError:
    from supabase import create_client as create_client  # type: ignore
Client = getattr(_s, 'Client', object)
load_dotenv = _s.load_dotenv
os = _s.os

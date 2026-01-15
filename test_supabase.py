from common.supabase_client import get_supabase
import os

def test_connection():
    print("Testing Supabase Connection...")
    
    if not os.environ.get("SUPABASE_URL"):
        print("❌ Missing SUPABASE_URL")
        return
        
    manager = get_supabase()
    
    if manager.enabled:
        print(f"✅ Client Initialized for: {manager.url}")
        try:
            # Check permissions by trying to read run table
            res = manager.client.table("runs").select("*").limit(1).execute()
            print("✅ 'runs' table read access confirmed.")
        except Exception as e:
            print(f"⚠️  'runs' table access issue: {e}")
            print("   (This is expected if tables are not created yet)")
    else:
        print("❌ Supabase client failed to initialize.")

if __name__ == "__main__":
    test_connection()

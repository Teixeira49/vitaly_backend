from app.core.database import supabase

try:
    res = supabase.table("student").select("*").limit(1).execute()
    print("Student table structure:", res.data[0] if res.data else "Empty table, cannot infer schema")
except Exception as e:
    print(f"Error querying table: {e}")

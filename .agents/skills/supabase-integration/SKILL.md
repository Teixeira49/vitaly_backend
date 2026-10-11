---
name: supabase-integration
description: Complete Supabase setup including PostgreSQL schema, RLS policies, vector search with pgvector, and connection pooling for FastAPI projects. Use when setting up database schemas, configuring RLS, or integrating Supabase Auth with FastAPI.
---

# Supabase Integration

This skill provides a complete guide for setting up and integrating Supabase as the backend for FastAPI projects, including PostgreSQL schema design, security via RLS, and performance optimizations.

## When to use this skill

- Use this when **initializing a new Supabase project** or configuring database extensions like `pgvector`.
- Use this when **defining the database schema** (Tables, Foreign Keys, JSONB).
- Use this to implement **Row Level Security (RLS)** for user or tenant isolation.
- Use this when configuring **connection pooling** or **backup strategies** for production.

## Decision Tree

**How should you configure the Supabase feature?**
- **Do you need semantic search?** -> Follow **Phase 2** to enable `pgvector` and **Phase 4** for HNSW indexes.
- **Do you need to secure data by user?** -> Follow **Phase 5** to implement User Isolation RLS policies.
- **Is the application multi-tenant (Organizations)?** -> Implementation **Pattern 2** for Org-level isolation.
- **Is the application experiencing connection errors?** -> Check **Phase 6** for connection pooling strategy.

## How to use it

### 1. Project Setup & Extensions

First, ensure the environment is configured and necessary extensions like `pgvector` are enabled.

```bash
# Enable pgvector for semantic search
SELECT * FROM pg_extension WHERE extname = 'vector';
-- If missing:
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Core Schema Pattern

Design tables with observability and isolation in mind.

```sql
CREATE TABLE items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  content text,
  metadata jsonb,
  embedding vector(1536), -- Dimension depends on your model
  created_at timestamptz DEFAULT now()
);
```

### 3. Security: Row Level Security (RLS)

Always enable RLS to prevent unauthorized cross-user data access.

```sql
-- Enable RLS
ALTER TABLE items ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own items
CREATE POLICY "Users access own items"
ON items FOR ALL
USING (auth.uid()::text = user_id);
```

### 4. Performance: HNSW Indexes

For vector searches, use HNSW indexes for speed.

```sql
CREATE INDEX idx_items_embedding ON items
USING hnsw (embedding vector_cosine_ops);
```

### 5. FastAPI Integration Pattern

```python
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Usage in a route
@app.get("/items")
async def get_items(current_user: User = Depends(get_current_user)):
    response = supabase.table("items").select("*").eq("user_id", current_user.id).execute()
    return response.data
```

## Best Practices

- **Service Key Protection:** Never expose the `SERVICE_ROLE_KEY` to the client or in frontend-facing code.
- **Context Filtering:** Even with RLS enabled, always include `user_id` filters in your queries for better performance and explicit safety.
- **Connection Management:** Use transaction pooling (port 6543) for high-concurrency FastAPI applications.
- **HNSW vs IVFFlat:** Use HNSW for most cases; it's faster for search though slower to build.

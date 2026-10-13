# Sync vs Async

## The rule

- supabase-py (shared client in `app/core/database.py`) is **blocking**. Handlers and services that use it are `def`.
- FastAPI runs `def` handlers and `def` dependencies in a threadpool, so blocking calls don't stall the event loop.
- `async def` runs **on** the event loop. Any blocking call inside it freezes every concurrent request.
- Use `async def` only when every I/O call inside is awaited and truly async (e.g. `httpx.AsyncClient`).

## 1. The real bug: blocking I/O in `async def`

```python
# BAD - blocks the event loop on every request
@router.get("/students/{student_id}", response_model=APIResponse[StudentRead])
async def get_student(student_id: int, admin_payload: dict = Depends(get_current_admin_escuela)):
    resp = supabase.table("student").select("*").eq("id", student_id).execute()  # blocking
    ...

# GOOD - sync def, threadpool handles the blocking call
@router.get("/students/{student_id}", response_model=APIResponse[StudentRead])
def get_student(student_id: int, admin_payload: dict = Depends(get_current_admin_escuela)):
    student = school_admin_service.get_student(user_id=int(admin_payload["sub"]), student_id=student_id)
    return APIResponse(data=student, message="Estudiante obtenido exitosamente")
```

Other blocking calls to flag inside `async def`: `requests.*`, `time.sleep`, `open()`, sync SMTP, CPU-heavy loops (e.g. bulk PDF/Excel generation).

## 2. Do NOT flag

- `def` handlers that call supabase-py: correct by design.
- `def` dependencies (`get_current_user_token` and the role gates).
- Converting a `def` handler to `async def` is **not** an improvement here; flag such a suggestion if it appears in a PR.

## 3. Mixed cases

If a handler genuinely needs an async client, keep blocking work out of it:

```python
async def notify(...):
    await async_http.post(...)                    # truly async
    rows = await run_in_threadpool(service.load)  # blocking supabase work offloaded
```

Prefer simply staying `def` unless there is a measured reason.

## 4. Background work

`BackgroundTasks` with a `def` function also runs in the threadpool; fine for short side effects (emails, audit). Long or retried jobs belong in a real worker, not a request.

## Review questions

1. Does any `async def` handler or dependency call supabase-py or other blocking I/O?
2. Does any PR "modernize" `def` handlers to `async def` without making the I/O async?
3. Are long-running tasks kept out of the request path?

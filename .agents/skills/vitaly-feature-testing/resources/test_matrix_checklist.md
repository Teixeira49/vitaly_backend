# Vitaly feature test checklist

Validate before opening a PR with a new or changed feature.

- [ ] **Location:** tests live in `tests/test_<feature>.py` and are collected by `pytest` (`pytest.ini`: `testpaths = tests`).
- [ ] **Envelope:**
  - [ ] 2xx responses assert `success is True`, `data` and `message`.
  - [ ] Error responses assert `success is False` and `message` (global handlers in `app/core/exceptions.py`; there is no `detail` key).
  - [ ] Unexpected supabase error is wrapped by the service as `HTTPException(500)` → 500 + envelope (raw exceptions skip the handlers and `TestClient` re-raises them).
- [ ] **Authentication fixtures:**
  - [ ] Gates overridden via `app.dependency_overrides[get_current_<role>]` with a realistic payload (`sub` as string, `role`, `email`, `name`, ...). Never `get_current_user` (it does not exist).
  - [ ] Overrides cleared in `finally` / fixture teardown.
- [ ] **Tenant isolation (`school_id`):**
  - [ ] `school_id` resolved server-side from `sub` (resolver such as `_get_school_id_for_admin` asserted or patched); never read from body/query/path on non-`admin_sistema` routes.
  - [ ] Directly scoped queries assert `.eq("school_id", <resolved id>)`.
  - [ ] A row that exists in another school → **403**.
  - [ ] User not linked to any school → **403**.
- [ ] **Missing and empty data:**
  - [ ] Single resource with `data = []` → **404**, no `IndexError` / 500.
  - [ ] Collection with no rows → **200 + `data=[]`** (never 404). Legacy endpoints that still 404 are fixed or covered by a strict `xfail`.
- [ ] **RBAC matrix:**
  - [ ] Allowed role → 2xx.
  - [ ] Wrong role → **403** (override `get_current_user_token`, so the real gate runs).
  - [ ] Invalid token and revoked token → **401**.
  - [ ] Route protection guard test exists (`vitaly-rbac`, `tests/api/test_route_protection.py`).
- [ ] **Validation:** bad path/query/body → **422** with a non-empty `errors` list.
- [ ] **Network isolation:** supabase patched where used (`app.services.<module>.supabase`); ImageKit and other external services mocked. Tests run offline.
- [ ] **Honesty:** no test claims "isolation verified" based on mocks alone.

# Future Skills

Skills parked for a possible future implementation. They live outside `.agents/skills/` on
purpose, so no agent discovers or loads them in this project.

| Skill | Parked because | Re-enable when |
| --- | --- | --- |
| `sqlalchemy-postgres` | The backend has no ORM; it uses the supabase-py client (see `vitaly-architecture`). | An explicit, approved decision to migrate to SQLAlchemy. |
| `sqlalchemy-code-review` | Same as above. | Same as above. |

To re-enable a skill: move it back to `.agents/skills/` and recreate its symlinks in
`.claude/skills/` and `.grok/skills/`.

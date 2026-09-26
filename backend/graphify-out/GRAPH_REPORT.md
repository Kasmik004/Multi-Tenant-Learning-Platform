# Graph Report - backend  (2026-09-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 407 nodes · 930 edges · 32 communities (9 shown, 9 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `25a90e4b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- create_tenant
- TenantService
- User
- users.py
- CourseService
- deps.py
- config.py
- services/auth.py
- test_health.py
- CurrentUser
- TenantManager
- model_validator
- FastAPI
- BaseModel
- AsyncSession
- learning-platform-api
- TenantMember
- Any

## God Nodes (most connected - your core abstractions)
1. `create_tenant()` - 35 edges
2. `User` - 23 edges
3. `TenantService` - 22 edges
4. `Tenant` - 19 edges
5. `UserService` - 18 edges
6. `invite_user()` - 18 edges
7. `send_invite()` - 16 edges
8. `CourseService` - 15 edges
9. `AuthService` - 15 edges
10. `Course` - 14 edges

## Surprising Connections (you probably didn't know these)
- `_expire_trials()` --calls--> `TenantService`  [INFERRED]
  tests/test_trial_lifecycle.py → app/services/tenant.py
- `create_platform_user()` --calls--> `UserRepository`  [INFERRED]
  tests/conftest.py → app/repositories/user.py
- `create_platform_user()` --calls--> `User`  [EXTRACTED]
  tests/conftest.py → app/models/user.py
- `create_platform_user()` --calls--> `hash_password()`  [EXTRACTED]
  tests/conftest.py → app/core/security.py
- `TenantContext` --uses--> `Tenant`  [INFERRED]
  app/api/deps.py → app/models/tenant.py

## Import Cycles
- None detected.

## Communities (32 total, 9 thin omitted)

### Community 0 - "create_tenant"
Cohesion: 0.08
Nodes (71): Any, fixture, Response, accept_invite(), _clean_tables(), client(), create_platform_user(), create_tenant() (+63 more)

### Community 1 - "TenantService"
Cohesion: 0.08
Nodes (37): create_tenant(), current_tenant(), delete_tenant(), extend_trial(), get_tenant(), list_tenants(), DBSession, delete (+29 more)

### Community 2 - "User"
Cohesion: 0.07
Nodes (29): create_superadmin(), expire_trials(), main(), Operator commands that must not be reachable over HTTP. uv run python -m…, Base, UUID, Every row owned by a tenant carries tenant_id. Repositories filter on it., TenantScopedMixin (+21 more)

### Community 3 - "users.py"
Cohesion: 0.11
Nodes (33): invite_user(), list_users(), DBSession, delete, get, Pagination, patch, post (+25 more)

### Community 4 - "CourseService"
Cohesion: 0.11
Nodes (28): create_course(), delete_course(), get_course(), list_courses(), DBSession, delete, get, Page (+20 more)

### Community 5 - "deps.py"
Cohesion: 0.08
Nodes (30): get_current_user(), get_tenant_context(), DBSession, PlatformRole, UUID, active_trial: also refuse once the tenant's trial is over (learning features,…, Dependency factory: `Depends(require_platform_roles(PlatformRole.SUPERADMIN))`., Who is acting, in which tenant (from X-Tenant-Slug), and with what rights. (+22 more)

### Community 6 - "config.py"
Cohesion: 0.08
Nodes (21): do_run_migrations(), run_migrations_online(), liveness(), DBSession, get, readiness(), get_settings(), Settings (+13 more)

### Community 7 - "services/auth.py"
Cohesion: 0.15
Nodes (22): accept_invite(), login(), me(), CurrentUser, DBSession, get, post, UnauthorizedError (+14 more)

### Community 8 - "test_health.py"
Cohesion: 0.67
Nodes (3): AsyncClient, test_liveness(), test_readiness_checks_database()

## Knowledge Gaps
- **1 isolated node(s):** `learning-platform-api`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 122 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TenantService` connect `TenantService` to `create_tenant`, `User`, `users.py`, `CourseService`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `User` connect `User` to `create_tenant`, `users.py`, `services/auth.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `Tenant` connect `TenantService` to `User`, `deps.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `User` (e.g. with `TenantUserRepository` and `UserRepository`) actually correct?**
  _`User` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `TenantService` (e.g. with `create_tenant()` and `delete_tenant()`) actually correct?**
  _`TenantService` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Tenant` (e.g. with `TenantContext` and `TenantRepository`) actually correct?**
  _`Tenant` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `UserService` (e.g. with `ConflictError` and `NotFoundError`) actually correct?**
  _`UserService` has 4 INFERRED edges - model-reasoned connections that need verification._
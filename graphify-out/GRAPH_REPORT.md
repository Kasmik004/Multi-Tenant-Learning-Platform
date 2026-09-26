# Graph Report - MLEExperts2  (2026-09-26)

## Corpus Check
- Corpus is ~14,508 words - fits in a single context window. You may not need a graph.

## Summary
- 510 nodes · 1060 edges · 31 communities (16 shown, 4 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 75 edges (avg confidence: 0.89)
- Token cost: 76,743 input · 0 output

## Community Hubs (Navigation)
- Tenant Context & Permissions
- Migrations & Platform Admin
- Test Fixtures & Database
- Architecture Docs & Rules
- Users Endpoints
- Frontend Dependencies
- Courses Endpoints
- Auth & Security
- TypeScript Config
- App Config & Startup
- Frontend API Client
- Generated API Types
- Health Endpoints
- Frontend Root Layout
- Health Tests
- Frontend Agent Rules
- ESLint Config
- Next.js Config
- PostCSS Config
- Backend Project Metadata

## God Nodes (most connected - your core abstractions)
1. `User` - 29 edges
2. `create_tenant()` - 28 edges
3. `UserService` - 18 edges
4. `TenantService` - 17 edges
5. `Tenant` - 16 edges
6. `CourseService` - 16 edges
7. `send_invite()` - 16 edges
8. `compilerOptions` - 16 edges
9. `Course` - 15 edges
10. `AuthService` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Add Tenant-Scoped Resource Workflow` --semantically_similar_to--> `Tenant-Owned Feature Checklist`  [INFERRED] [semantically similar]
  README.md → .claude/skills/backend-architecture/SKILL.md
- `Tenant from JWT tid claim (stale)` --conceptually_related_to--> `X-Tenant-Slug Header Tenant Resolution`  [AMBIGUOUS]
  README.md → .claude/skills/backend-architecture/SKILL.md
- `Open Self-Service Tenant Onboarding (stale)` --conceptually_related_to--> `Invite-Only Onboarding`  [AMBIGUOUS]
  README.md → .claude/skills/backend-architecture/SKILL.md
- `check_migrations.py (round-trip + drift check)` --semantically_similar_to--> `CI Backend Job (ruff, mypy, alembic, pytest)`  [INFERRED] [semantically similar]
  .claude/skills/backend-migrations/SKILL.md → .github/workflows/ci.yml
- `CI Backend Job (ruff, mypy, alembic, pytest)` --semantically_similar_to--> `Compose db Service (postgres:17-alpine)`  [INFERRED] [semantically similar]
  .github/workflows/ci.yml → compose.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Tenant Isolation Enforcement** — _claude_skills_backend_architecture_skill_tenantscopedmixin, _claude_skills_backend_architecture_skill_tenantscopedrepository, _claude_skills_backend_architecture_skill_x_tenant_slug_header, _claude_skills_backend_architecture_skill_permission_dependencies, _claude_skills_backend_testing_skill_tenant_isolation_test_pattern [INFERRED 0.85]
- **AGENT.md Rules Operationalized by Backend Skills** — agent_agent_rules, _claude_skills_backend_architecture_skill_backend_architecture_skill, _claude_skills_backend_migrations_skill_backend_migrations_skill, _claude_skills_backend_testing_skill_backend_testing_skill [EXTRACTED 1.00]
- **Docker Compose Dev Stack** — compose_db_service, compose_backend_service, compose_frontend_service [EXTRACTED 1.00]

## Communities (31 total, 4 thin omitted)

### Community 0 - "Tenant Context & Permissions"
Cohesion: 0.06
Nodes (47): get_current_user(), get_tenant_context(), CurrentUser, DBSession, UUID, Who is acting, in which tenant (from X-Tenant-Slug), and with what rights., _require(), TenantContext (+39 more)

### Community 1 - "Migrations & Platform Admin"
Cohesion: 0.06
Nodes (35): do_run_migrations(), run_migrations_online(), Dependency factory: `Depends(require_platform_roles(PlatformRole.SUPERADMIN))`., require_platform_roles(), create_superadmin(), main(), Operator commands that must not be reachable over HTTP. uv run python -m…, Base (+27 more)

### Community 2 - "Test Fixtures & Database"
Cohesion: 0.09
Nodes (55): accept_invite(), _clean_tables(), client(), create_platform_user(), create_tenant(), _database(), _ensure_test_database(), in_tenant() (+47 more)

### Community 3 - "Architecture Docs & Rules"
Cohesion: 0.05
Nodes (57): API v1 Endpoint Map, App Error Hierarchy ({error:{code,message}}), Backend Architecture Skill, Course Enrollment (planned next feature), Enums Stored By Value Gotcha, Invite-Only Onboarding, JWT Carries Identity Only, Layered Backend Architecture (endpoints/services/repositories) (+49 more)

### Community 4 - "Users Endpoints"
Cohesion: 0.10
Nodes (32): invite_user(), list_users(), DBSession, delete, get, Pagination, patch, post (+24 more)

### Community 5 - "Frontend Dependencies"
Cohesion: 0.05
Nodes (38): eslint, eslint-config-next, dependencies, next, openapi-fetch, react, react-dom, devDependencies (+30 more)

### Community 6 - "Courses Endpoints"
Cohesion: 0.14
Nodes (24): create_course(), delete_course(), get_course(), list_courses(), DBSession, delete, get, Pagination (+16 more)

### Community 7 - "Auth & Security"
Cohesion: 0.15
Nodes (23): accept_invite(), login(), me(), CurrentUser, DBSession, get, post, UnauthorizedError (+15 more)

### Community 8 - "TypeScript Config"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 9 - "App Config & Startup"
Cohesion: 0.12
Nodes (17): get_settings(), model_validator, Settings, FastAPI, register_exception_handlers(), configure_logging(), create_app(), lifespan() (+9 more)

### Community 10 - "Frontend API Client"
Cohesion: 0.29
Nodes (7): Home(), getApiBaseUrl(), ApiStatus, getApiStatus(), ApiError, createApiClient(), Schemas

### Community 11 - "Generated API Types"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 12 - "Health Endpoints"
Cohesion: 0.50
Nodes (4): liveness(), DBSession, get, readiness()

### Community 13 - "Frontend Root Layout"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 14 - "Health Tests"
Cohesion: 0.67
Nodes (3): AsyncClient, test_liveness(), test_readiness_checks_database()

### Community 15 - "Frontend Agent Rules"
Cohesion: 0.67
Nodes (3): CI Frontend Job (lint, typecheck, build), Next.js Agent Rules (read bundled docs, breaking changes), frontend CLAUDE.md

## Ambiguous Edges - Review These
- `X-Tenant-Slug Header Tenant Resolution` → `Tenant from JWT tid claim (stale)`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to
- `Invite-Only Onboarding` → `Open Self-Service Tenant Onboarding (stale)`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to
- `Five Roles Permission Matrix` → `Legacy Roles admin/instructor/learner (stale)`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **75 isolated node(s):** `learning-platform-api`, `eslintConfig`, `nextConfig`, `name`, `version` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 174 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `X-Tenant-Slug Header Tenant Resolution` and `Tenant from JWT tid claim (stale)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Invite-Only Onboarding` and `Open Self-Service Tenant Onboarding (stale)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Five Roles Permission Matrix` and `Legacy Roles admin/instructor/learner (stale)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `User` connect `Migrations & Platform Admin` to `Tenant Context & Permissions`, `Test Fixtures & Database`, `Users Endpoints`, `Auth & Security`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `Base` connect `Migrations & Platform Admin` to `Tenant Context & Permissions`, `Courses Endpoints`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `BaseRepository` connect `Migrations & Platform Admin` to `Tenant Context & Permissions`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `User` (e.g. with `get_current_user()` and `require_platform_roles()`) actually correct?**
  _`User` has 7 INFERRED edges - model-reasoned connections that need verification._
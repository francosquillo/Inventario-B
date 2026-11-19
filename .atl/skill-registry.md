# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

Project: Inventario-B (Python stdlib + SQLite CLI -> FastAPI + Supabase PostgreSQL + static HTML/Tailwind CDN/vanilla JS on Vercel serverless; unittest; Strict TDD; OpenSpec; design-system + mockups).
Skills marked **[RELEVANT]** are the primary matches for this project.

## User Skills

Paths: G = `C:/Users/Franco/.claude/skills`, A = `C:/Users/Franco/.agents/skills`, P = project `.agents/skills`.

| Trigger | Skill | Path |
|---------|-------|------|
| [RELEVANT] ANY Supabase task: Python client usage, RPC, RLS/security checklist, CLI, debugging (JS/SSR parts do not apply) | supabase | A/supabase/SKILL.md |
| [RELEVANT] Pydantic v2 models, Field constraints, validators for HTTP input validation | pydantic | A/pydantic/SKILL.md |
| [RELEVANT] Writing/changing anything in Postgres: schema, RLS, indexes, functions/RPC, migrations, slow queries | supabase-postgres-best-practices | A/supabase-postgres-best-practices/SKILL.md |
| [RELEVANT] Postgres schema/index/RLS quick patterns | postgres-patterns | A/postgres-patterns/SKILL.md |
| [RELEVANT] Designing/reviewing PostgreSQL tables, types, constraints | postgresql-table-design | A/postgresql-table-design/SKILL.md |
| [RELEVANT] FastAPI routes, Pydantic models, dependencies (HTTP layer, Phase 2/3) | fastapi | A/fastapi/SKILL.md |
| [RELEVANT] Writing Python tests, mocking, DB tests (pytest-oriented; project uses unittest) | python-testing-patterns | A/python-testing-patterns/SKILL.md |
| [RELEVANT] Implementing any feature/bugfix, before implementation code | test-driven-development | A/test-driven-development/SKILL.md |
| [RELEVANT] Any bug/test failure, before fixing | systematic-debugging | A/systematic-debugging/SKILL.md |
| [RELEVANT] Testing local web apps with Playwright (Python) | webapp-testing | A/webapp-testing/SKILL.md |
| [RELEVANT] Browser automation / Playwright via CLI | playwright-cli | A/playwright-cli/SKILL.md |
| [RELEVANT] Define/audit visual identity (policy system-and-mockups) | design-system | G/design-system/SKILL.md |
| [RELEVANT] Distinctive UI visual design | frontend-design | G/frontend-design/SKILL.md |
| [RELEVANT] UI polish, animation decisions | emil-design-eng | G/emil-design-eng/SKILL.md |
| [RELEVANT] Frontend taste (v1) | design-taste-frontend-v1 | G/design-taste-frontend-v1/SKILL.md |
| [RELEVANT] Design/critique/audit/polish interfaces | impeccable | G/impeccable/SKILL.md |
| [RELEVANT] UI/UX intelligence, a11y, responsive | ui-ux-pro-max | G/ui-ux-pro-max/SKILL.md |
| [RELEVANT] Web UI guidelines review | web-design-guidelines | A/web-design-guidelines/SKILL.md |
| [RELEVANT] Implement OpenSpec change tasks | openspec-apply-change | P/openspec-apply-change/SKILL.md |
| [RELEVANT] Archive completed change | openspec-archive-change | P/openspec-archive-change/SKILL.md |
| [RELEVANT] Explore mode | openspec-explore | P/openspec-explore/SKILL.md |
| [RELEVANT] Create change with all artifacts | openspec-propose | P/openspec-propose/SKILL.md |
| [RELEVANT] Sync delta specs to main specs | openspec-sync-specs | P/openspec-sync-specs/SKILL.md |
| [RELEVANT] Revise change planning artifacts | openspec-update-change | P/openspec-update-change/SKILL.md |
| Review code | code-review | A/code-review/SKILL.md |
| Architecture patterns | architecture-patterns | A/architecture-patterns/SKILL.md |
| Minimal-change coding mode | ponytail | G/ponytail/SKILL.md |
| Codebase knowledge graph | graphify | G/graphify/SKILL.md |
| Project foundation flow | active-orchestrator | G/active-orchestrator/SKILL.md |
| Generate AGENTS.md/CLAUDE.md | agent-instruction | G/agent-instruction/SKILL.md |
| Discovery research | discovery-research | G/discovery-research/SKILL.md |
| Discover/install skills | find-skill | G/find-skill/SKILL.md |
| Create knowledge base | kb-creator | G/kb-creator/SKILL.md |
| Generate CHANGES.md | roadmap-generator | G/roadmap-generator/SKILL.md |
| Competitor scraping | web-scraper | G/web-scraper/SKILL.md |
| SEO audit | seo-audit | G/seo-audit/SKILL.md |
| Create/improve skills | skill-creator | G/skill-creator/SKILL.md |
| Docker Compose verify (FastAPI/Vite; not applicable) | tp-verify-docker | G/tp-verify-docker/SKILL.md |
| Not applicable to this stack | fastapi-templates, java-springboot, springboot-patterns, redis-core, redis-patterns, vercel-react-best-practices, pdf, xlsx | A/<name>/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### fastapi
- Use `Annotated[..., Depends(...)]` for dependencies (e.g. `get_current_user` -> 401 without session).
- Pydantic models for request bodies: `Field(gt=0)` for quantities, `min_length=1` for required strings, `datetime.date` for dates; do not use ellipsis or `RootModel`.
- Prefer return type annotations; use `response_model` only when the public schema differs from the internal value.
- Declare prefix/tags/shared dependencies on `APIRouter`. Supabase client is sync: use plain `def` endpoints, not `async def`.
- Domain services keep their own validation (shared with CLI); Pydantic is only the HTTP-layer guard. Tests: `TestClient` (needs `httpx`).

### supabase
- Project uses the Python `supabase` client with the `service_role` key ONLY inside the FastAPI backend, and RPC (Postgres functions) for atomic ops. JS/SSR guidance (supabase-js, @supabase/ssr, Next.js cookies, getClaims/getSession) does NOT apply.
- Supabase changes often: verify against current docs/changelog before implementing; verify every fix with a test query; after 2-3 failed attempts stop and rethink.
- Never expose `service_role`/secret key to the browser or `NEXT_PUBLIC_`-style vars; pin package versions and commit lockfiles.
- Enable RLS on every table in exposed schemas (`public`); `TO authenticated` alone is not authorization (add ownership predicate); UPDATE policies need USING + WITH CHECK and a SELECT policy.
- Avoid `SECURITY DEFINER` to fix permission errors (bypasses RLS, callable by PUBLIC in `public`); prefer SECURITY INVOKER, or keep in a non-exposed schema with auth checks. Views: `security_invoker = true`.
- Never use `user_metadata` for authorization; use `app_metadata`. Never `auth.role()` (deprecated).
- CLI: discover commands via `--help`; new migrations via `supabase migration new <name>`; run `supabase db advisors` after schema changes.

### pydantic
- Pydantic v2 is only the HTTP-layer guard for untrusted input; do not use it for internal classes (use dataclasses/plain classes). Domain services keep their own validation.
- Prefer built-in constraints over custom validators: `Annotated[int, Field(gt=0)]` (quantities/ids > 0), `Annotated[str, Field(min_length=1)]` with `StringConstraints(strip_whitespace=True, min_length=1)` for non-empty/trimmed strings, `datetime.date` for dates (ISO strings coerced).
- Prefer the Annotated pattern; use assignment form for `alias`/`default`/`default_factory`. Field-specific metadata goes on the top-level type (`Annotated[int | None, Field(...)]`).
- If a validator is unavoidable use `AfterValidator`/`mode='after'` (+ `@classmethod`), not before validators.
- Pydantic coerces by default (`'123'` -> 123); avoid `int | str` unions and abstract collections; use `strict` when coercion is unwanted.
- Avoid `from __future__ import annotations` in model modules; quote only undefined forward refs. Polymorphic models: discriminated unions (`Field(discriminator='type')`) or generics.

### supabase-postgres-best-practices
- Load before ANY SQL/schema/RLS/function/migration work.
- Priorities: query performance > connection management > security/RLS > schema design > locking > data access.
- Atomic multi-step logic (create order + decrement stock) goes in a Postgres function (RPC), not several client calls.
- Index FK columns manually; composite indexes equality columns first, then range.
- Enable RLS on exposed tables; wrap `auth.uid()` as `(SELECT auth.uid())`. Service-role key must never reach the browser.
- Use pooled connections in serverless (Vercel) to avoid connection exhaustion.
- Short transactions; consistent row-lock order (`SELECT ... FOR UPDATE`) on stock rows.

### postgres-patterns
- Types: bigint IDs, text, timestamptz, numeric for money, boolean. Avoid varchar(255), timestamp, float money.
- UPSERT via `ON CONFLICT ... DO UPDATE SET x = EXCLUDED.x`.
- Keyset pagination over OFFSET; partial index for soft-delete (`WHERE activo`).

### postgresql-table-design
- PK `BIGINT GENERATED ALWAYS AS IDENTITY`; NOT NULL + DEFAULT where required; snake_case unquoted names.
- Postgres does not auto-index FKs; UNIQUE allows multiple NULLs.
- CHECK constraints for business rules (quantity > 0, stock >= 0); normalize to 3NF.

### python-testing-patterns
- AAA structure; independent tests, no shared state, clean up after each.
- Project uses stdlib `unittest` (not pytest): `unittest.TestCase`, `setUp/tearDown`, `unittest.mock`; SQLite `:memory:` or temp files for DB tests.
- Mock Supabase client at the repository boundary; test business logic via the repository interface.
- Cover happy path + edges (empty, zero, over-stock, duplicates).

### test-driven-development
- No production code without a failing test first; watch it fail for the right reason.
- RED (one minimal test) -> verify fail -> GREEN (minimal code) -> verify pass -> REFACTOR staying green.
- Code written before its test is deleted and redone from the test.
- Test behavior not mocks; one behavior per test; bug fixes start with a reproducing test.

### systematic-debugging
- No fixes before root cause: read errors fully, reproduce, check recent changes.
- Multi-layer flows (frontend -> FastAPI -> Supabase): add boundary logging to find the failing layer first.
- One hypothesis, one change at a time; after 3 failed fixes question the design.

### webapp-testing
- Native Python Playwright scripts, headless chromium, wait for `networkidle` before inspecting DOM.
- Run `scripts/with_server.py --help` first (black box) to start the FastAPI server (uvicorn), then the script.
- Recon-then-act: screenshot/inspect rendered DOM, then pick selectors; close the browser.

### playwright-cli
- `playwright-cli open|goto|snapshot|click <ref>|fill <ref> "text"|screenshot|resize W H|close`; refs come from snapshot.
- Capture at 390x844 and 1440x900; use `eval` for attributes missing from snapshot; always `close`.

### design-system
- Policy `system-and-mockups`, revision 1, approved: reuse `design-system/` (tokens.css, brand.js, components.html, assets); do not regenerate per screen.
- Never change approved tokens silently: bump Revision, list affected mockups, rerender, ask re-approval.
- Unknown brand facts stay `(TBD)` and visibly provisional.
- Each visual change needs mockups in `openspec/changes/<name>/mockups/` and recorded user approval before apply.

### frontend-design
- Deliberate, subject-specific choices for palette/typography/layout; avoid templated defaults.
- Ground design in real content (inventory, work orders); defer to approved design-system tokens.

### emil-design-eng
- Polish: easing, short purposeful animations (<300ms), generous hit areas, press/focus states; respect prefers-reduced-motion.

### design-taste-frontend-v1
- Avoid generic AI-looking UI; consistent spacing scale, restrained palette, clear typographic hierarchy; defer to design-system tokens.

### impeccable
- For critique/audit/polish: hierarchy, typography, color, empty/loading/error states, a11y, responsive.
- Cover edge cases: long text, validation messages, empty lists.

### ui-ux-pro-max
- Contrast >= 4.5:1, visible focus, touch targets >= 44px, responsive layout, clear form validation.
- Stack: HTML + Tailwind CDN + vanilla JS, no build step.

### web-design-guidelines
- Review UI against Web Interface Guidelines (a11y, forms, focus, touch, performance) and report findings.

### openspec-* (apply-change, archive-change, explore, propose, sync-specs, update-change)
- `openspec` CLI owns state: run `openspec status --change <name> --json` first; never hand-create `openspec/` structure.
- Artifacts: proposal.md, design.md, tasks.md, specs/ under `openspec/changes/<name>/`; archive to `openspec/changes/archive/YYYY-MM-DD-<name>/`.
- apply: implement tasks in order, mark `[x]`, pause on blockers; Strict TDD applies.
- propose: change + all artifacts in one pass; explore: no implementation.
- archive/sync: sync delta specs into `openspec/specs/<capability>/spec.md`.

### code-review
- Review the diff for correctness bugs first, report with severity; fix only when asked.

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| (none) | - | CLAUDE.md / AGENTS.md do not exist yet; openspec/config.yaml and knowledge-base/ hold project context |

Read the convention files listed above for project-specific patterns and rules.

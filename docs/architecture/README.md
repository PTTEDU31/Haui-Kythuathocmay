# HaUI Assist architecture

Open [the interactive overview](index.html). All eight diagrams are standalone Archify HTML files with theme, focus and export controls. The [relationship explorer](explorer.html) filters calls, imports, callbacks and HTTP interactions by evidence status. The [source explorer](source.html) contains line-linked committed text snapshots, so references work without a remote or a web server.

## Scope and method

Repository: `student-support`. Pinned revision: `ded15187b5fe25dc9eb6733c64292097943f3f1d`. Analysis refreshed on 2026-10-22 (Asia/Ho_Chi_Minh) with GitNexus 1.6.12, using `analyze --force --index-only`. GitNexus context, schema, clusters, process resources, concept query, symbol contexts and full Cypher extracts are retained under `evidence/`. The index was fresh for this source snapshot; creating these documentation artifacts subsequently makes GitNexus report added documentation files. Application source is unchanged; generated documentation was not recursively indexed into its own evidence.

GitNexus reports **458 graph nodes, 1,074 edges, 15 clusters, 36 heuristic flows and 65 indexed files**. There are **343 CALLS edges and 18 IMPORTS edges**, including three Markdown links that are documentation relationships rather than Python imports. `evidence/inventory.json` inventories **all 73 tracked files** with committed-byte hashes. Runtime code, all scripts, test fixtures, deployment files and dependency declarations were inspected; data, saved model binaries, reference documents and historical reports are inventoried, not misrepresented as executable modules. Dependencies' internal implementation and live services are outside this repository.

**VERIFIED** means the relation is supported by the inspected committed source, including registration or exact HTTP call/route pairs. It does not mean a runtime trace was recorded. **INFERRED** identifies an unverified GitNexus graph candidate or a deployment assumption; the explorer keeps the analyzer's confidence separately. Native diagram flows are source-verified except the architecture's explicitly labelled inferred tunnel edge. Optional and early-return paths carry conditions. Sequence diagrams depict conditional alternatives; they do not claim every message happens on every request.

The checkout has **no origin remote**. Archify requires an origin for its repository identity check, so native SRC provenance verification is unavailable. No origin was invented or configured. Exact citations are retained in diagram source cards and `evidence/source-map.json`, independently range-checked against Git blobs at the pinned revision. The diagram HTML passed ordinary Archify artifact and browser gates; these gates do not prove semantic correctness. Source snapshots are local, commit-pinned evidence. Pre-existing untracked `.claude/`, `AGENTS.md` and `CLAUDE.md` were preserved; no runtime/application source was changed.

## Diagrams

| Diagram | What it covers |
| --- | --- |
| [Runtime architecture](architecture.html) | JavaScript, FastAPI, SQLite, Engine, model artifacts, providers and qualified tunnel configuration |
| [Module dependencies](modules.html) | Verified Python imports; runtime modules, API maintenance, model/data scripts and tests |
| [Startup](startup.html) | Uvicorn import, Engine construction, lifespan/init_db, FAQ seed/rebuild and browser start |
| [Chat](chat.html) | Callback → HTTP → handler → route/generate → persistence → rendering → feedback |
| [Routing](routing.html) | All priority rules, context, classifier/retrieval decisions and terminal statuses |
| [Knowledge/admin](knowledge-admin.html) | Authentication, document draft import, human approval, FAQ write/rebuild and public search |
| [Training/research](research-training.html) | Train/Validation/Test, persisted model choice, inference artifact loading, report UI and stateless experiments |
| [Operations](operations.html) | systemd, backup timer, SQLite snapshot/archive, auth utilities and development tooling |

## Entry points and module ownership

| File / entry point | Responsibility and dependencies |
| --- | --- |
| app/main.py:16,75,77 | `ENGINE=Engine()` at import; `lifespan()` → `init_db()`; exported ASGI `app`. Owns SQLite I/O, authentication, middleware and routes. Imports app.engine. |
| app/engine.py:48 | `Engine.__init__`, `rebuild`, `search`, `classify`, `route`, `generate`; pure-memory retrieval plus explicit model/config-file reads and provider HTTP. Imports app.text. |
| app/text.py:8 | `normalize_classification`: Unicode NFC/lower/space; persisted preprocessing callback. |
| app/static/index.html:2 | Deferred `/static/app.js`; static HTML/CSS UI, no frontend bundler or Node server. |
| app/static/app.js:70–71 | `start()` bootstraps session/history/status and calls `setView()`. Event handlers drive all later execution. |
| app/__init__.py | Package marker; no independent execution path. |
| scripts/train.py:59,164 | `main()` fits sklearn pipelines, selects by Validation, writes reports/models; imports app.text and labels from app.engine. |
| scripts/evaluate_faq.py:14,53 | `main()` loads public FAQ/cases, creates Engine, routes four modes, writes FAQ evaluation. |
| scripts/prepare_data.py:9 | Module-level DOCX extraction and saved-source curation; `src()` and `add()` helpers; writes CSV/FAQ/manifest. Optional regeneration utility. |
| scripts/initialize_auth.py:4 | Module-level create-once credentials using `password_hash`; imports app.main, therefore also constructs ENGINE. |
| scripts/reset_admin.py:5 | Module-level interactive password reset, atomic auth-file replacement and session revocation; imports app.main. |
| scripts/backup.py:3 | Standalone module-level SQLite snapshot, tar archive and 14-copy retention; no app import. |
| scripts/check_alignment_inprocess.py:89,105 | `main()` isolates STUDENT_ROOT and invokes `asyncio.run(check(...))`; lifespan + ASGITransport; heartbeat task. |
| scripts/check_alignment_ui.js:27 | Async IIFE; extracts `loadExperiments()` into node:vm, runs stub API/DOM callbacks and writes report. |
| scripts/browser_qa.py:7 | Module-level Playwright live-deployment checks; `pageerror` callbacks; reads real admin credentials. Inspected only. |
| scripts/start_report_alignment.sh:25,57 | Shell launcher / `--worker` entry paths: snapshot, worktree, tmux, codex, ready-marker, pytest, commit. Inspected only. |
| tests/conftest.py:4,20,29 | Import-time temporary root, `client()` / `logged()` fixtures and `pytest_sessionfinish()` cleanup. |
| tests/test_application.py:19 | pytest test functions exercise Engine, API, sessions, admin edits, uploads and generation fallbacks. |
| tests/test_research_routing.py:20 | `engine()` fixture; test functions cover callback normalization, mode semantics, priority, evidence and training provenance. |
| deploy/*.service / *.timer | Configured Uvicorn/Ollama/cloudflared and backup process entry points; not evidence of current activation. |

## Important call chains

- Startup: `uvicorn app.main:app` → import-time `Engine.__init__()` → FastAPI `lifespan()` → `init_db()` → `reload_engine()` → `Engine.rebuild()` → sklearn `fit_transform()` → `normalize()` callback.
- Chat: `chat-form.onsubmit` / Enter / suggestion callback → `ask()` → `api()` → `fetch(POST /api/chat)` → `guard()` / framework validation → `chat()` → `limit()` / `visitor()` → recent assistant results → `Engine.route()` → optional `Engine.generate()` → strip private evidence → two message inserts → `message()` / feedback callbacks.
- Retrieval: `Engine.route()` → `normalize()` → priority/context rules → optional `classify()` → `search()` globally and by category → `active()` / `evidence_matches()` → source-backed answer or clarify/out_of_scope. Greeting and safety rules return early.
- Generation: `generate()` requires answered status and enabled settings; acquires a lock (2s), posts with `httpx.Client` (55s timeout, 5s connect), parses JSON, validates supported/length/numbers/no URLs and always releases the lock. Busy, invalid or unavailable provider retains FAQ text. `use_ai=false` skips the call entirely.
- Publication: upload callback → `upload_document()` → extracted `documents.status=draft`; later human `openFaq()` edits → FAQ form callback → `create_faq()` / `update_faq()` → `validate_faq()` → SQL + audit → `reload_engine()` → `rebuild()` → `active()` filters approved/unexpired rows. Upload does not publish or automatically rebuild.
- Training: `train.main()` → fixed CSV splits → Pipeline with `normalize_classification` callback → Train fit → `measure(Validation)` → select family/application winners → write `selection.json` → `measure(Test)` → joblib + experiment report. Runtime loads artifacts on new Engine construction, not automatically when files change.
- Research: `loadExperiments()` → GET reports; installed form callback → POST research route → `research_route()` → `Engine.route(model_mode=...)` → remove evidence → JSON. It does not call generate, write messages or change default model.
- Backup: timer → service → Python module → SQLite `Connection.backup()` → tar allowlist → permissions/cleanup/retention. The allowlist contains intent.joblib but omits the runtime-loaded mlp.joblib, linearsvc.joblib and selection.json; this is visible in source, not assumed full model recovery.

## Callback and cross-language boundaries

`evidence/relationships.json` includes source-verified callbacks and transport links in addition to the raw GitNexus graph. Important registrations: browser `hashchange → setView`; onclick suggestion/retry → ask; `setTimeout(loadKnowledge,250)` debounce; message vote closures; dynamically installed research/admin forms; FastAPI lifespan, HTTP middleware `call_next` and `Depends(admin)`; sklearn preprocessing callbacks; asyncio heartbeat/create_task; pytest fixtures; Playwright pageerror callbacks; node:vm renderer evaluation.

JavaScript calls Python through same-origin HTTP JSON (multipart for uploads). Shell/systemd launch Python, Uvicorn, Ollama, cloudflared and the historical codex worker as processes. Python calls Ollama or an OpenAI-compatible provider through HTTP JSON; no in-repository provider internals, FFI wrappers, WebSockets, streaming callbacks or message broker were found. SQLite and sklearn/NumPy native implementation details belong to installed dependencies and were not traced as repository code. DOCX/PDF parsing is a file-format boundary, not a cross-language function-call edge.

## HTTP entry points

All handlers below are source-verified in app/main.py. Mutating requests pass through `guard()`; protected endpoints also use `Depends(admin)`. Login/logout implement their own session operations. Public chat/history/feedback use visitor ownership rather than administrator authentication.

| Method | Route | Handler | Admin dependency | Source |
| --- | --- | --- | --- | --- |
| GET | `/api/health` | `health()` | no | [app/main.py:125](source.html#path=app/main.py&line=125) |
| GET | `/api/bootstrap` | `bootstrap()` | no | [app/main.py:129](source.html#path=app/main.py&line=129) |
| GET | `/api/history` | `history()` | no | [app/main.py:134](source.html#path=app/main.py&line=134) |
| DELETE | `/api/history` | `clear_history()` | no | [app/main.py:139](source.html#path=app/main.py&line=139) |
| POST | `/api/chat` | `chat()` | no | [app/main.py:146](source.html#path=app/main.py&line=146) |
| POST | `/api/feedback` | `feedback()` | no | [app/main.py:162](source.html#path=app/main.py&line=162) |
| GET | `/api/knowledge` | `knowledge()` | no | [app/main.py:170](source.html#path=app/main.py&line=170) |
| GET | `/api/experiments` | `experiments()` | no | [app/main.py:175](source.html#path=app/main.py&line=175) |
| POST | `/api/experiments/route` | `research_route()` | no | [app/main.py:187](source.html#path=app/main.py&line=187) |
| GET | `/api/ai-status` | `ai_status()` | no | [app/main.py:197](source.html#path=app/main.py&line=197) |
| POST | `/api/admin/login` | `login()` | no | [app/main.py:207](source.html#path=app/main.py&line=207) |
| POST | `/api/admin/logout` | `logout()` | no | [app/main.py:220](source.html#path=app/main.py&line=220) |
| POST | `/api/admin/password` | `change_password()` | yes | [app/main.py:224](source.html#path=app/main.py&line=224) |
| GET | `/api/admin/overview` | `overview()` | yes | [app/main.py:237](source.html#path=app/main.py&line=237) |
| POST | `/api/admin/faqs` | `create_faq()` | yes | [app/main.py:254](source.html#path=app/main.py&line=254) |
| PUT | `/api/admin/faqs/{id}` | `update_faq()` | yes | [app/main.py:260](source.html#path=app/main.py&line=260) |
| POST | `/api/admin/documents` | `upload_document()` | yes | [app/main.py:267](source.html#path=app/main.py&line=267) |
| PUT | `/api/admin/ai` | `ai_settings()` | yes | [app/main.py:295](source.html#path=app/main.py&line=295) |
| GET | `/` | `index()` | no | [app/main.py:312](source.html#path=app/main.py&line=312) |

`app.mount("/static", StaticFiles(...))` is an additional static-file mount at app/main.py:314. There is no route OpenAPI/docs entry: docs_url, redoc_url and openapi_url are disabled.

## Source-verified internal imports

| Importer | Module | Names | Source |
| --- | --- | --- | --- |
| `app/engine.py` | `app/text.py` | `normalize_classification` | [app/engine.py:9](source.html#path=app/engine.py&line=9) |
| `app/main.py` | `app/engine.py` | `Engine, ROOT, LABELS, safe_url, normalize, active` | [app/main.py:13](source.html#path=app/main.py&line=13) |
| `scripts/check_alignment_inprocess.py` | `app/main.py` | `app, ENGINE, password_hash` | [scripts/check_alignment_inprocess.py:97](source.html#path=scripts/check_alignment_inprocess.py&line=97) |
| `scripts/evaluate_faq.py` | `app/engine.py` | `Engine` | [scripts/evaluate_faq.py:11](source.html#path=scripts/evaluate_faq.py&line=11) |
| `scripts/initialize_auth.py` | `app/main.py` | `password_hash` | [scripts/initialize_auth.py:4](source.html#path=scripts/initialize_auth.py&line=4) |
| `scripts/prepare_data.py` | `app/engine.py` | `LABELS` | [scripts/prepare_data.py:7](source.html#path=scripts/prepare_data.py&line=7) |
| `scripts/reset_admin.py` | `app/main.py` | `password_hash, conn` | [scripts/reset_admin.py:5](source.html#path=scripts/reset_admin.py&line=5) |
| `scripts/train.py` | `app/text.py` | `NORMALIZATION_VERSION, normalize_classification` | [scripts/train.py:28](source.html#path=scripts/train.py&line=28) |
| `scripts/train.py` | `app/engine.py` | `LABELS, RESEARCH_LABELS` | [scripts/train.py:29](source.html#path=scripts/train.py&line=29) |
| `tests/conftest.py` | `app/main.py` | `password_hash, init_db` | [tests/conftest.py:13](source.html#path=tests/conftest.py&line=13) |
| `tests/conftest.py` | `app/main.py` | `app` | [tests/conftest.py:19](source.html#path=tests/conftest.py&line=19) |
| `tests/test_application.py` | `app/main.py` | `app, ENGINE, conn, read_settings, rates` | [tests/test_application.py:5](source.html#path=tests/test_application.py&line=5) |
| `tests/test_application.py` | `app/engine.py` | `normalize, safe_url` | [tests/test_application.py:6](source.html#path=tests/test_application.py&line=6) |
| `tests/test_research_routing.py` | `app/engine.py` | `Engine, RESEARCH_LABELS, normalize` | [tests/test_research_routing.py:13](source.html#path=tests/test_research_routing.py&line=13) |
| `tests/test_research_routing.py` | `app/text.py` | `normalize_classification` | [tests/test_research_routing.py:14](source.html#path=tests/test_research_routing.py&line=14) |
| `tests/test_research_routing.py` | `app/main.py` | `ENGINE` | [tests/test_research_routing.py:179](source.html#path=tests/test_research_routing.py&line=179) |

## Uncertainty and analyzer limitations

- GitNexus explicitly reported **48 property sites** with matching field definitions only in another language; it declined those links. The exact HTTP paths and JSON producer/consumer sources were inspected to bridge the browser/backend boundary. A missing graph edge is not evidence of an absent interaction.
- Process generation was bounded: **29 ranked entry points were not traced, 295 callees were skipped, one walk hit its budget and two deduplicated flows were dropped**. The 36 process candidates are not complete executions. Full call/import extraction plus source inspection complements those bounded paths.
- Raw Cypher symbol lines are **zero-based**. The normalized explorer data and diagram citations are **one-based**. Original MCP receipts are retained unchanged.
- A graph edge with confidence 1 can still describe heuristic matching, callback approximation or documentation links. Unchecked edges remain inferred in the explorer. Source-verified relationships are explicitly promoted; graph provenance is retained.
- `deploy/cloudflared-ttech.yml.example` names a public tunnel destination, but cloudflared reads an external config. The effective public routing, credentials, host firewall, active units, provider availability and runtime model contents were not inspected or measured. Systemd `After=` expresses ordering rather than proof a dependency is enabled or healthy.
- `STUDENT_ROOT` relocates the application DB/model/settings root; training and most utilities derive their root from their own file. The static directory always remains adjacent to app/main.py.
- Training exports `intent.joblib`, but Engine loads `mlp.joblib` and `linearsvc.joblib`, selecting the default via selection.json. The training diagram shows this actual handoff rather than treating intent.joblib as the runtime loader input.
- Classifier/retrieval scores and thresholds are distinct and uncalibrated. The routing diagram describes source control flow, not validated prediction quality.

## Reproduce and inspect

The authoritative native diagram inputs are `candidates/*.json`. Run Archify `finalize <diagram_type> <candidate> <output.html> --quality showcase --json` using the installed Archify CLI. Existing browser evidence requires a new `--out-dir` on a later delivery. No network library or build step is needed to view the HTML files locally.

Evidence files include `scope.json`, tracked file hashes, raw GitNexus resources/contexts/query/results, normalized full symbols/relations/processes, source maps and per-diagram Archify receipts. The overview, relationship explorer and pinned source viewer are lightweight companion HTML pages, not Archify-native diagrams.

Documentation verification checks citation bounds and committed snapshot identity, automated artifact and browser gates for all eight Archify diagrams, internal local links and browser interaction of the companion pages. No production API, credentials, database, service manager, training job, backup or historical automation script was invoked.

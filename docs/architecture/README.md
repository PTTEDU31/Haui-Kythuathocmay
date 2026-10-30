# HaUI Assist architecture

Open [the interactive overview](index.html). All eight diagrams are standalone Archify HTML files with theme, focus and export controls. The [relationship explorer](explorer.html) filters calls, imports, callbacks and HTTP interactions by evidence status. The [source explorer](source.html) contains line-linked committed text snapshots, so references work without a remote or a web server.

## Học máy và nhận dạng: mô hình chạy như thế nào?

Mở [bài học chi tiết](https://ttech.io.vn/static/hoc-mo-hinh.html), cũng có liên kết từ menu chatbot, trang hướng dẫn bảo vệ và trace. Gồm 12 phần, 81 thuật ngữ và 25 câu vấn đáp: biểu diễn TF-IDF; forward MLP; cross-entropy, gradient/backprop và L-BFGS; hình học, squared hinge và OvR của LinearSVC; đánh giá và giới hạn thực nghiệm.

Phòng khám phá có 9 ví dụ được tính từ artifact đã lưu: từng đặc trưng TF/DF/IDF, đóng góp vào nơ-ron/điểm OvR, ReLU, logits, softmax và argmax. Đây là snapshot suy luận, tách khỏi trace runtime. Ví dụ tương tác 2 chiều dùng trọng số minh họa riêng, hiển thị mạng và biên SVM cùng loss/gradient, không huấn luyện hay đổi artifact.

[Phần đối chiếu phản hồi của cô](https://ttech.io.vn/static/hoc-mo-hinh.html#teacher-feedback) trả lời từng ý về thuật toán, đầu vào văn bản/vector, kiến trúc MLP 327→16→5, số lớp và nhãn đầu ra. Có bảng phân bố 50 câu theo nhãn/split, đủ 327 tọa độ và tên cột, cùng 16 nơ-ron ẩn có thể bấm để xem phép tính. Phần phạm vi đối chiếu 18 lượt route cục bộ (9 câu × 2 mô hình) trên FAQ công khai với nhãn classifier trực tiếp; chỉ rõ trường hợp ngoài từ vựng, thời tiết ngoài phạm vi và ký túc xá được quy tắc mở rộng hỗ trợ. Các lượt này không phải trace runtime hay phép đo khả năng phát hiện mọi câu ngoài miền.

Sau khi đổi artifact hoặc tài nguyên trang học, chạy:

```bash
.venv/bin/python scripts/build_model_lab.py
```

Bộ dựng bài kiểm tra phép forward với sklearn trên toàn bộ 50 câu công khai và 9 ví dụ cho cả hai mô hình (118 lượt), kiểm tra TF-IDF với DF từ Train, rồi xuất snapshot và cập nhật URL tài nguyên theo hash nội dung để tránh cache cũ. Route được chạy bằng Engine mới trên `data/faqs.json`, quan sát lời gọi classifier và giữ nguyên hash artifact. Không import `app.main`, đọc DB/cấu hình runtime, chạy train hay gọi provider. Code đối chiếu dùng `defense-lessons.js`; nếu nguồn code thay đổi, dựng lại bằng `scripts/build_defense_lessons.py` như hướng dẫn bên dưới.

## Trace chạy thật theo thời gian thực

Các trang học mô hình, hướng dẫn, lưu đồ, xem source và trace dùng chung `app/static/code-viewer.js` / `.css`: tô màu cú pháp bằng Highlight.js 11.11.1 lưu tại chỗ, giữ thụt dòng, tách số dòng, cuộn ngang, bật/tắt xuống dòng, tăng/giảm cỡ chữ và sao chép code không kèm số dòng. Liên kết và tìm kiếm theo dòng của snapshot được giữ nguyên. Đây là thay đổi cách trình bày, không viết lại code được trích dẫn. Giấy phép thư viện ở `app/static/vendor/highlight-LICENSE`.

Các bộ dựng trang gọi `scripts/code_viewer_assets.py` để thêm tài nguyên cùng origin và URL có hash nội dung. Sau khi đổi JS/CSS trình đọc code, chạy `.venv/bin/python scripts/code_viewer_assets.py` rồi `.venv/bin/python docs/architecture/build_live.py`; chạy lại các bộ dựng trang như bên dưới cũng giữ trình đọc code.

### Đối chiếu lưu đồ, phương pháp và code khi vấn đáp

Mở [hướng dẫn bảo vệ trên web](https://ttech.io.vn/static/huong-dan-bao-ve.html) hoặc [lưu đồ từng bước](https://ttech.io.vn/static/huong-dan-mo-phong.html). Menu chatbot và trang trace đều có liên kết tới hướng dẫn. Các trang public dùng script/style cùng origin, phù hợp CSP của FastAPI.

Theo yêu cầu của giáo viên, với mỗi bước trình bày theo thứ tự: **lưu đồ viết gì → phương pháp sử dụng → code triển khai ở đâu → giải thích input/output và điều kiện chuyển nhánh**. Hướng dẫn có bài riêng cho TF-IDF, MLP, LinearSVC, truy hồi cosine, kiểm tra bằng chứng, Qwen/Ollama và Train/Validation/Test; kèm câu hỏi vấn đáp và câu trả lời gợi ý. Chỉ rõ code gọi `sklearn` để fit/predict, không nhận là dự án tự viết nội bộ thuật toán.

Trong trace, chọn lời gọi để xem phần **Đối chiếu lưu đồ với code**. Chú giải hiển thị dưới dữ liệu thật, dùng `routing.classifier_used`, kết quả mô hình và trạng thái lời gọi để phân biệt nhánh thực tế. Lời gọi đang chạy chưa có output; khối chưa quan sát không được gán dữ liệu hay phương pháp thực thi giả. Nội bộ sklearn, huấn luyện và nội bộ Qwen không được trace từ request chat.

Trích đoạn code công khai được dựng từ các file allowlist; mỗi đoạn ghi file, dòng và hash nguồn. Sau khi sửa code hoặc nội dung hướng dẫn, chạy theo thứ tự:

```bash
.venv/bin/python scripts/build_defense_lessons.py
.venv/bin/python docs/architecture/build_live.py
.venv/bin/python docs/architecture/build_presentation.py
.venv/bin/python scripts/publish_defense_player.py
```

`defense-lessons.js` là snapshot code hiện tại khi dựng bài. Các input/output trong player offline vẫn là minh họa của revision được ghim; không gọi chúng là trace thật. Bản public player và source viewer chỉ tách script/style ra file, không sửa các sơ đồ Archify gốc. Nội dung này không đọc SQLite, cấu hình bí mật, cookie hoặc API key; đọc hướng dẫn không chạy train/provider.

**Link trình diễn dự phòng hiện tại: [mở trace](https://macro-empty-podcast-kinda.trycloudflare.com/architecture/live) · [mở chat web](https://macro-empty-podcast-kinda.trycloudflare.com/#chat)**. Đây là quick tunnel; hostname có thể đổi khi tunnel khởi động lại. Tên miền chính `https://ttech.io.vn/architecture/live` đang gặp lỗi DNSSEC ở DNS công khai (xem `evidence/live-dns-fallback.json`). Trang live và stream dùng chung origin với ứng dụng.

**Trace cả chat trên web chính:** mở hai tab cùng tên miền trong cùng trình duyệt, bật **Tự động trace chat từ web chính** ở tab trace và chờ **Đang nghe chat web**. Gửi câu hỏi ở tab chat; sơ đồ, input/output và mã nguồn bên tab trace cập nhật theo lời gọi thật. Trang chat có nút **Xem trace trực tiếp** khi server bật trace. Hai trình duyệt, hai thiết bị hoặc hai tên miền dùng phiên khác nhau nên không tự chia sẻ trace. Chỉ nhận sự kiện của những lượt hỏi bắt đầu sau khi kết nối; không lưu/phát lại trace cũ.

Nếu chạy riêng trên máy để phát triển, bật trace từ thư mục gốc repository:

```bash
STUDENT_TRACE=1 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Mở **http://127.0.0.1:8090/architecture/live**, nhập câu hỏi và bấm **Gửi và trace thật**. Khối sáng cùng dữ liệu khi hàm bắt đầu/kết thúc; output còn đang chờ được ghi rõ. Chọn lời gọi trong danh sách hoặc bấm khối để xem lại dữ liệu đã thu. **Phóng theo khối** giúp đọc trên máy chiếu; tắt **Theo dõi sự kiện mới** để giữ nguyên lời gọi đang giải thích. Hàm nhanh có thể hoàn tất trong vài mili giây; trang không thêm delay giả để làm chậm ứng dụng.

Đây là request thật vào cùng `chat()` của `/api/chat`: đọc lịch sử của phiên hiện tại, chạy `Engine.route()`, các hàm phân loại/truy hồi/kiểm tra bằng chứng thực sự được gọi và ghi hai tin nhắn vào SQLite. Chọn AI sẽ gọi provider thật nếu điều kiện `generate()` cho phép; trace hiện cả lời gọi HTTP, kết quả và fallback. `observe_chat()` bao quanh handler thường để gửi sự kiện tới các tab trace cùng phiên đang kết nối; phản hồi JSON, mã lỗi và cookie của `/api/chat` vẫn giữ nguyên. Không mở observer thì chat không khởi tạo recorder. Khối không có sự kiện ghi **chưa quan sát**, không được suy ra là đã chạy hoặc chưa từng chạy ở nơi khác. Callback JavaScript của tab chat thông thường không được quan sát từ server.

Giao thức `POST /api/chat/trace` trả NDJSON qua `StreamingResponse`: sự kiện `start`, `end`/`error`, `result` và `done`; mỗi lời gọi có parent ID, timestamp UTC, thời gian monotonic và input/output có giới hạn kích thước. Server dùng ContextVar theo request; không ghi trace ra file hoặc phát sang phiên khác. Cần cookie visitor hợp lệ từ `/api/bootstrap`; các kiểm tra origin, schema và giới hạn chat vẫn áp dụng. Lỗi sau khi bắt đầu stream nằm trong `request_error.status_code` dù transport đã trả HTTP 200; mất kết nối không tự gửi lại vì handler có thể đã ghi DB. Đóng tab dừng quan sát, không hủy tác vụ đã bắt đầu.

`POST /api/chat/trace/events` mở kênh NDJSON chờ chat web (không có body). Client dùng POST vì quick tunnel đang giữ lại các chunk GET nhỏ; route GET vẫn có cho client nội bộ. Kênh, xác thực cookie phiên trước khi đăng ký. `observer_ready` xác nhận đã nghe; mỗi lượt chat có `trace_id` riêng trên mọi sự kiện. Kênh có heartbeat 10 giây và tự nối lại khi mất mạng; không phát lại các sự kiện đã mất. Mỗi tab giữ hàng đợi tối đa 256 sự kiện; quá chậm thì báo thiếu sự kiện và đóng kênh, không ảnh hưởng phản hồi chat. Tối đa 4 tab trên mỗi phiên và 32 tab trên mỗi process. UI hiển thị lượt chat mới nhất khi có nhiều lượt đồng thời; lượt gửi trực tiếp từ trang trace được ưu tiên tới khi kết thúc. Quan sát dùng bộ nhớ của một process, phù hợp dịch vụ Uvicorn một worker hiện tại; triển khai nhiều worker cần thêm broker và cơ chế phân phối riêng.

Trace tắt mặc định; tối đa 4 lượt gửi trực tiếp qua `/api/chat/trace` đồng thời trên mỗi process. Không thu thập cookie/token/API key/cấu hình bí mật; các trường không thu thập và phần rút gọn được đánh dấu. File source/function line và code của hàm Python lấy từ checkout đang phục vụ, không trỏ về snapshot cũ. Thời gian có overhead quan sát và truyền dữ liệu, không phải benchmark; thời gian browser/server có đồng hồ riêng. Luồng hiện gắn quan sát chat/Engine/SQLite/provider, không phải profiler mọi callback hoặc mọi dòng lệnh; không quan sát nội bộ Ollama/sklearn/SQLite, khởi động, quản trị, huấn luyện hay backup từ một lượt chat.

`live.html` cần mở qua FastAPI để dùng session và stream cùng origin, không mở trực tiếp bằng `file://` hay `python -m http.server`. URL `127.0.0.1:8090` chỉ dùng cho máy đang chạy lệnh phát triển ở trên; khi truy cập từ máy khác, dùng URL tunnel.

Dịch vụ hiện tại `student-support.service` ở cổng **8088** đã được khởi động lại với `STUDENT_TRACE=1` qua drop-in `~/.config/systemd/user/student-support.service.d/live-trace.conf`:

```ini
[Service]
Environment=STUDENT_TRACE=1
```

Sau khi thay đổi drop-in, chạy `systemctl --user daemon-reload` rồi `systemctl --user restart student-support.service`. Tunnel giữ nguyên đích `http://127.0.0.1:8088`. Nếu trang live trả 404 trong khi `/api/health` vẫn hoạt động, kiểm tra dịch vụ đã nạp code mới và flag trace. Kết quả kiểm tra HTTPS/stream thực tế nằm trong `evidence/live-tunnel-verification.json`.

Dựng lại giao diện bằng `python docs/architecture/build_live.py` sau khi sửa `live.template.html`, `live.js` hoặc `live.css`. Bản đồ dùng lại hình học SVG Archify; `live-diagram.css` được tách để tuân thủ CSP của ứng dụng mà không cần inline script/style. Các file Archify gốc và receipt giữ nguyên; `evidence/live-build.json` ghi hash của giao diện live. Kiểm thử ở `tests/test_live_trace.py` có kết nối HTTP thật chứng minh sự kiện provider đến trước khi provider hoàn tất, kiểm tra cách ly phiên, số đo/kết quả thật, nhánh trả về sớm và fallback lỗi.

## Trình diễn input/output cho giáo viên

Mở [bản trình diễn offline](presentation.html), chọn sơ đồ và kịch bản rồi bấm **Phát** hoặc **Tiếp →**. Khối đang xử lý sáng lên cùng bảng **Input / Output**, tên hàm, trích dẫn nguồn và gợi ý lời thuyết trình. Có thể bấm trực tiếp vào bất kỳ khối nào để xem dữ liệu, bật **Phóng theo khối**, đổi tốc độ, mở JSON hoặc dùng toàn màn hình.

Có 8 sơ đồ, 58 khối có dữ liệu, 12 kịch bản và 72 bước minh họa. Các nhánh định tuyến bao gồm answered, clarify, out_of_scope và greeting; nhánh AI lỗi giữ lại FAQ. Sơ đồ module giải thích phụ thuộc import, không được diễn giải thành thứ tự thực thi request.

**Đây là mô phỏng offline, không phải trace runtime.** Payload, điểm số, token và kết quả là ví dụ theo mã nguồn đã trích dẫn. Trang không gọi API, chạy AI, ghi DB hay đọc dữ liệu riêng tư. FAQ mẫu và cấu hình lựa chọn mô hình lấy từ dữ liệu công khai tại revision được ghim. Các sơ đồ Archify gốc và receipt giữ nguyên; presentation.html tái sử dụng SVG và thêm bộ điều khiển riêng.

Space = phát/dừng và ←/→ = lùi/tiếp khi không focus nút/ô nhập. Bản trình diễn tự dừng khi chuyển tab; chọn sơ đồ/kịch bản hoặc bấm khối sẽ dừng để tránh nhảy bước khi đang giải thích.

Dựng lại bản trình diễn bằng `python docs/architecture/build_presentation.py`. Các nguồn chỉnh sửa là `build_presentation.py`, `presentation.js` và `presentation.css`; HTML đầu ra nhúng đầy đủ CSS, JavaScript và dữ liệu nên mở trực tiếp được, không cần server hoặc Internet. `evidence/presentation-build.json` ghi coverage và hash artifact.

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

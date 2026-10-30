"""Build an offline teaching player from the checked Archify diagrams.

No app imports, database access, provider requests or model execution occur.
All payloads below are explicitly illustrative; citations pin the actual code.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCE_REVISION = json.loads((ROOT / 'evidence/scope.json').read_text())['revision']


def committed_json(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{SOURCE_REVISION}:{path}'], cwd=PROJECT))


def step(node, title, input_value, output_value, explain, fn='', **extra):
    return dict(node=node, title=title, input=input_value, output=output_value,
                explain=explain, fn=fn, **extra)


def scenario(label, description, *steps):
    return dict(label=label, description=description, steps=list(steps))


def build():
    faq = committed_json('data/faqs.json')[0]
    q = faq['question']
    answer = faq['answer']
    source = dict(id=faq['id'], title=faq['source_title'], url=faq['source_url'],
                  reviewed_at=faq['reviewed_at'], valid_until=faq.get('valid_until'),
                  kind=faq.get('kind', 'guidance'))
    result = dict(status='answered', answer=answer, intent='hoc_phi', sources=[source])
    ranked = [dict(id='FAQ-001', intent='hoc_phi', score=0.82, status='approved')]
    input_q = dict(question=q, model_mode='retrieval', history=[])
    selection = committed_json('reports/selection.json')['selected']
    source_map = json.loads((ROOT / 'evidence/source-map.json').read_text())

    plans = {}
    plans['architecture'] = dict(label='01 · Kiến trúc tổng thể', scenarios=[scenario(
        'Một lượt hỏi học phí', 'Đi theo dữ liệu từ trình duyệt đến FAQ và quay về giao diện. Payload, điểm số và trạng thái trong bản này là minh họa offline.',
        step('browser', 'Sinh viên gửi câu hỏi', {'Nội dung nhập': q, 'AI tạo sinh': False}, {'method': 'POST', 'path': '/api/chat', 'body': {'question': q, 'use_ai': False}}, 'Callback của biểu mẫu gọi ask(), rồi api() dùng fetch cùng cookie trình duyệt.', 'ask() → api()', edges=['browser-to-api']),
        step('api', 'API kiểm tra và lấy ngữ cảnh', {'question': q, 'cookie': 'haui_visitor=<minh họa>'}, {'Câu hỏi hợp lệ': True, 'Lịch sử gần nhất': [], 'Bước tiếp': 'ENGINE.route(q, history)'}, 'guard() và kiểm tra dữ liệu chạy trước chat(); visitor() tìm phiên và chat() đọc tối đa 4 kết quả trợ lý.', 'guard() → chat() → visitor()', edges=['api-to-db']),
        step('db', 'SQLite trả lại lịch sử', {'SELECT': "result FROM messages WHERE session_id=? AND role='assistant' LIMIT 4"}, {'past': [], 'Ý nghĩa': 'Phiên minh họa chưa có câu trả lời trước'}, 'SQLite chỉ trả dữ liệu phiên đang sử dụng; Engine không trực tiếp đọc cơ sở dữ liệu.', 'conn() / sqlite3', edges=['api-to-db']),
        step('engine', 'Truy hồi câu trả lời có nguồn', input_q, result, 'Engine chuẩn hóa, chọn chủ đề, tìm FAQ và kiểm tra bằng chứng. Điểm 0.82 trong phần định tuyến là số minh họa.', 'Engine.route() → search()', edges=['api-to-engine']),
        step('api', 'Bỏ bằng chứng nội bộ và lưu hai tin nhắn', {'result': result, 'use_ai': False}, {'generation': {'used': False, 'reason': 'disabled_for_request'}, 'Số bản ghi messages được thêm': 2, 'evidence trả cho trình duyệt': False}, 'Với use_ai=false, API không gọi provider; câu trả lời và câu hỏi được lưu theo phiên.', 'chat()', edges=['api-to-db']),
        step('browser', 'Hiển thị trả lời và nguồn', {'JSON từ API': result}, {'Bong bóng trả lời': answer, 'Nguồn dẫn': faq['source_title'], 'Nút thao tác': ['Hữu ích', 'Chưa hữu ích']}, 'message() tạo nội dung đã escape, hiển thị dẫn nguồn và đăng ký callback phản hồi.', 'message()'),
    ), scenario(
        'Nhánh AI không sẵn sàng', 'Minh họa nhánh gọi AI rồi quay lại FAQ khi provider lỗi. Không gửi yêu cầu AI thật.',
        step('config', 'Đọc cấu hình AI', {'File': 'data/ai-settings.json'}, {'enabled': True, 'provider': 'ollama', 'model': 'qwen3:4b'}, 'read_settings() cung cấp cấu hình cho generate(); API key không xuất hiện trên trang trình diễn.', 'read_settings()'),
        step('engine', 'Chỉ gọi AI khi đã có bằng chứng', {'status': 'answered', 'enabled': True, 'evidence': answer}, {'Gói gửi provider': {'question': q, 'FAQ được chọn': answer}, 'generator_lock': 'đã lấy · minh họa'}, 'generate() không sinh câu trả lời cho trạng thái clarify hoặc out_of_scope.', 'Engine.generate()', edges=['engine-to-provider']),
        step('provider', 'Provider lỗi · tình huống minh họa', {'endpoint': 'http://127.0.0.1:11435/api/chat'}, {'Kết quả minh họa': 'Kết nối không thành công'}, 'Provider là dịch vụ HTTP ngoài mã nguồn; nhánh này chỉ mô phỏng lỗi kết nối.', 'httpx.Client.post()', condition='Nhánh tùy chọn · answered + enabled + có khóa'),
        step('engine', 'Giữ lại câu trả lời đã duyệt', {'Ngoại lệ provider': 'minh họa', 'Câu trả lời FAQ': answer}, {'answer': answer, 'generation': {'used': False, 'reason': 'provider_unavailable'}, 'generator_lock': 'đã giải phóng'}, 'except giữ FAQ; finally giải phóng khóa để lượt sau tiếp tục sử dụng AI.', 'Engine.generate()'),
    )])

    plans['chat'] = dict(label='02 · Chat và phản hồi', scenarios=[scenario(
        'Trả lời FAQ → phản hồi hữu ích', 'Kịch bản chính đặt use_ai=false. Các bước gửi dữ liệu thật được mô phỏng để không ghi vào lịch sử của ứng dụng.',
        step('web', 'Callback gửi câu hỏi', {'textarea': q, 'use_ai': False}, {'question': q, 'use_ai': False}, 'Enter hoặc submit gọi ask(); busy ngăn người dùng gửi lặp trong khi đang chờ.', 'ask() / api()', edges=['m1']),
        step('main', 'chat() nhận HTTP JSON', {'method': 'POST', 'path': '/api/chat', 'body': {'question': q, 'use_ai': False}}, {'sid': '<phiên minh họa>', 'q': q, 'history': []}, 'Sau kiểm tra origin và dữ liệu, chat() áp giới hạn tần suất và đọc lịch sử của đúng phiên.', 'chat()', edges=['m2']),
        step('db', 'Đọc ngữ cảnh phiên', {'sid': '<phiên minh họa>', 'limit': 4}, {'past': []}, 'Cơ sở dữ liệu trả lại các result trợ lý gần nhất, không phải toàn bộ lịch sử của mọi người dùng.', 'conn()', edges=['m2']),
        step('engine', 'Engine.route() chọn FAQ', input_q, {**result, 'evidence': answer}, 'Bằng chứng là nội dung FAQ đã duyệt; đây là dữ liệu nội bộ để kiểm soát trả lời.', 'Engine.route()', edges=['m3', 'm4']),
        step('main', 'API bỏ evidence rồi ghi lịch sử', {'result có evidence': True, 'use_ai': False}, {'result có evidence': False, 'messages thêm': ['user', 'assistant'], 'generation.reason': 'disabled_for_request'}, 'Không đi qua các mũi tên provider trong kịch bản này.', 'chat()', edges=['m9']),
        step('web', 'message() hiển thị câu trả lời', {'answer': answer, 'sources': [source]}, {'Hiển thị': answer, 'Nguồn': faq['source_title']}, 'Nguồn được server gắn; trình duyệt escape văn bản trước khi đưa vào giao diện.', 'message()', edges=['m10']),
        step('main', 'Nhận đánh giá hữu ích', {'message_id': '<id minh họa>', 'value': 1}, {'Kiểm tra': 'message thuộc đúng sid và role=assistant'}, 'Callback nút phản hồi gửi POST /api/feedback; server kiểm tra quyền sở hữu tin nhắn.', 'feedback()', edges=['m11']),
        step('db', 'Lưu phản hồi', {'message_id': '<id minh họa>', 'value': 1, 'note': ''}, {'INSERT OR REPLACE': 'feedback', 'response': {'ok': True}}, 'Bản trình diễn chỉ hiển thị thao tác; không tạo phản hồi trong ứng dụng đang chạy.', 'conn()', edges=['m12']),
    )])

    routing_steps = [
        step('input', 'Nhận câu hỏi và chuẩn hóa', input_q, {'normalized': 'quy dinh hoc phi nam hoc 2026 2027 o dau', 'model_mode hợp lệ': True}, 'normalize() mở rộng viết tắt và bỏ dấu để truy hồi; đây không phải bộ chuẩn hóa classifier.', 'Engine.route() → normalize()'),
        step('rules', 'Kiểm tra chào hỏi và an toàn', {'normalized': 'quy dinh hoc phi nam hoc 2026 2027 o dau'}, {'greeting': False, 'unsafe / excluded': False, 'Tiếp tục': True}, 'Nếu khớp quy tắc trả về sớm, những bước classifier và truy hồi phía sau không chạy.', 'Engine.route():103–108'),
        step('topics', 'Nhận diện chủ đề tường minh', {'Câu hỏi': q, 'history': []}, {'topics': ['hoc_phi'], 'context_used': False}, 'Regex nhận ra học phí; ngữ cảnh chỉ được dùng cho một số câu ngắn, khi chưa có chủ đề tường minh.', 'Engine.route():109–123'),
        step('multiple', 'Có nhiều chủ đề không?', {'topics': ['hoc_phi']}, {'len(topics)': 1, 'Trả về clarify ngay': False}, 'Chỉ một chủ đề nên chưa cần yêu cầu người dùng chọn chủ đề.', 'Engine.route():124–125'),
        step('vague', 'Có cần hỏi rõ câu mơ hồ?', {'topics': ['hoc_phi']}, {'Kiểm tra câu không có chủ đề': 'bỏ qua', 'Tiếp tục': True}, 'Nhánh câu mơ hồ chỉ áp dụng khi chưa nhận ra chủ đề.', 'Engine.route():126–129'),
        step('classify', 'Chế độ chỉ truy hồi', {'model_mode': 'retrieval'}, {'classification': None}, 'Không có pipeline mang tên retrieval, nên classify() trả None; chủ đề tường minh vẫn được giữ.', 'Engine.classify()'),
        step('global', 'Tìm FAQ trong toàn kho', {'q': q, 'category': None}, {'Top ứng viên minh họa': ranked, 'Công thức': '0.55 × word cosine + 0.45 × char cosine'}, 'Các score là ví dụ để giải thích; không phải điểm đo từ một lượt chạy thật.', 'Engine.search()'),
        step('category', 'Giữ chủ đề học phí', {'topics': ['hoc_phi'], 'classification': None}, {'category': 'hoc_phi', 'reason': 'explicit_topic'}, 'Chủ đề tường minh được ưu tiên; nhãn mô hình chỉ thu hẹp tìm kiếm khi phù hợp.', 'Engine.route():138–144'),
        step('ranked', 'Tìm lại trong đúng chủ đề', {'q': q, 'category': 'hoc_phi'}, {'ranked': ranked}, 'Truy hồi theo chủ đề vẫn phải tìm FAQ đang được duyệt và còn hạn.', 'Engine.search(q, category)'),
        step('enough', 'Có ứng viên đủ để xét tiếp?', {'ranked': ranked, 'topics': ['hoc_phi']}, {'Có ứng viên': True, 'Ngưỡng toàn kho .30': 'chỉ bắt buộc với câu không có chủ đề'}, 'Không có ứng viên hoặc câu không rõ chủ đề có score thấp sẽ dẫn đến out_of_scope.', 'Engine.route():149–150'),
        step('conflict', 'Kiểm tra độ khớp và xung đột', {'score minh họa': 0.82, 'Ngưỡng theo chủ đề': 0.13, 'topics': ['hoc_phi']}, {'score >= .13': True, 'conflict': False, 'close_topics': False}, 'Hai phép kiểm tra xung đột giữa chủ đề chỉ áp dụng khi không có chủ đề tường minh.', 'Engine.route():151–154'),
        step('lexical', 'Kiểm tra từ vựng và năm học', {'Câu hỏi': q, 'FAQ': answer, 'Năm trong câu hỏi': ['2026', '2027']}, {'Năm có trong FAQ': True, 'evidence_matches': True}, 'Nếu có từ hai từ khóa ngoài stopword/chủ đề, tỷ lệ khớp phải ít nhất 25%; năm hỏi phải có trong nguồn.', 'evidence_matches()'),
        step('answer', 'Trả lời bằng FAQ có nguồn', {'top': ranked[0], 'evidence_matches': True}, {**result, 'evidence': answer}, 'Trả lời đến từ FAQ, không đến từ nhãn classifier. chat() sẽ bỏ evidence trước khi trả ra ngoài.', 'Engine.route():156–157'),
    ]
    plans['routing'] = dict(label='03 · Định tuyến và bằng chứng', scenarios=[
        scenario('Trả lời học phí · chỉ truy hồi', 'Nhánh answered với một chủ đề tường minh. Điểm 0.82 là minh họa; các điều kiện và tên hàm được đối chiếu mã nguồn.', *routing_steps),
        scenario('Hai chủ đề → hỏi lại', 'Cho thấy early return: sau khi nhận ra hai chủ đề, classifier và truy hồi không chạy.',
                 step('input', 'Nhận câu hỏi nhiều chủ đề', {'question': 'Học phí và học bổng có gì mới?'}, {'normalized': 'hoc phi va hoc bong co gi moi'}, 'Chuẩn hóa câu hỏi trước khi kiểm tra quy tắc.', 'Engine.route() → normalize()'),
                 step('rules', 'Qua kiểm tra ưu tiên', {'normalized': 'hoc phi va hoc bong co gi moi'}, {'greeting': False, 'unsafe': False}, 'Câu hỏi vẫn thuộc phạm vi sinh viên.', 'Engine.route():103–108'),
                 step('topics', 'Phát hiện hai chủ đề', {'Câu hỏi': 'Học phí và học bổng có gì mới?'}, {'topics': ['hoc_phi', 'hoc_bong']}, 'Hai regex cùng khớp.', 'Engine.route():109–123'),
                 step('multiple', 'Dừng nhánh tìm câu trả lời', {'len(topics)': 2}, {'Điều kiện len(topics) > 1': True}, 'Hệ thống ưu tiên yêu cầu làm rõ trước khi chạy classifier.', 'Engine.route():124–125', edges=['multiple-to-multiple-exit']),
                 step('multiple-exit', 'Trả về clarify', {'topics': ['hoc_phi', 'hoc_bong']}, {'status': 'clarify', 'sources': [], 'suggestions': ['Học phí', 'Học bổng']}, 'Kết thúc lượt này; không chạy các khối phía dưới.', 'Engine.route():125')),
        scenario('Nội dung ngoài phạm vi → từ chối', 'Nhánh ưu tiên trả về out_of_scope trước khi truy hồi FAQ.',
                 step('input', 'Nhận câu hỏi ngoài phạm vi', {'question': 'Dự đoán giá cổ phiếu giúp em'}, {'normalized': 'du doan gia co phieu giup em'}, 'Chuẩn hóa để áp quy tắc phạm vi.', 'Engine.route() → normalize()'),
                 step('rules', 'Nhận ra nội dung bị loại', {'normalized': 'du doan gia co phieu giup em'}, {'Regex khớp': 'co phieu'}, 'Khối quy tắc dừng lượt hỏi này.', 'Engine.route():107–108', edges=['rules-to-rules-out-exit']),
                 step('rules-out-exit', 'Trả về out_of_scope', {'Regex khớp': 'co phieu'}, {'status': 'out_of_scope', 'sources': [], 'Gọi classifier / search': False}, 'Không tự bịa câu trả lời khi câu hỏi nằm ngoài phạm vi.', 'Engine.route():108')),
        scenario('Chào hỏi → trả lời ngay', 'Câu chào được trả lời bằng quy tắc, không cần mô hình hoặc FAQ.',
                 step('input', 'Nhận lời chào', {'question': 'Xin chào'}, {'normalized': 'xin chao'}, 'Chuẩn hóa lời chào.', 'normalize()'),
                 step('rules', 'Khớp danh sách chào hỏi', {'normalized': 'xin chao'}, {'greeting': True}, 'Trả về ngay khi có lời chào được liệt kê.', 'Engine.route():103', edges=['rules-to-rules-greeting-exit']),
                 step('rules-greeting-exit', 'Trả lời lời chào', {'greeting': True}, {'status': 'greeting', 'sources': [], 'Gọi search / AI': False}, 'Kết thúc ở nhánh greeting.', 'Engine.route():104')),
    ])

    plans['startup'] = dict(label='04 · Khởi động ứng dụng', scenarios=[scenario(
        'Import Python → lifespan → trình duyệt', 'Minh họa thứ tự khởi động. Điều kiện tạo bảng/seed được thể hiện bằng ví dụ kho ban đầu rỗng.',
        step('asgi', 'Uvicorn nạp ASGI app', {'ExecStart': 'uvicorn app.main:app --port 8088'}, {'Module': 'app.main', 'Đối tượng': 'app'}, 'Lệnh đến từ cấu hình systemd trong repository; không khởi chạy dịch vụ trong bản trình diễn.', 'Uvicorn import'),
        step('engine', 'Tạo ENGINE trong lúc import', {'models': ['mlp.joblib', 'linearsvc.joblib'], 'selection': 'reports/selection.json'}, {'models': ['mlp', 'linearsvc'], 'default_model': selection.lower()}, 'Engine đọc hai pipeline có tên và model mặc định từ selection, không đọc intent.joblib.', 'Engine.__init__()'),
        step('main', 'Framework gọi lifespan', {'lifespan': 'lifespan(app)'}, {'Lệnh tiếp': 'init_db()'}, 'FastAPI gọi callback khởi tạo trước khi sẵn sàng xử lý yêu cầu.', 'lifespan()'),
        step('disk', 'Tạo bảng và seed nếu cần', {'faqs hiện có': 0, 'Nguồn seed': 'data/faqs.json'}, {'journal_mode': 'WAL', 'Bảng': ['faqs', 'sessions', 'messages', 'feedback', 'admin_sessions', 'audit', 'documents'], 'FAQ seed minh họa': 25}, 'Chỉ seed khi bảng faqs rỗng; không ghi đè FAQ do quản trị đã thay đổi.', 'init_db()'),
        step('engine', 'Xây chỉ mục trong bộ nhớ', {'rows từ SQLite': 'FAQ đã lưu'}, {'Bộ lọc': 'approved + chưa hết hạn', 'Chỉ mục': ['word TF-IDF (1,2)', 'char_wb TF-IDF (3,5)']}, 'reload_engine() đọc DB rồi đưa rows vào rebuild(); vectorizer gọi normalize qua callback.', 'reload_engine() → Engine.rebuild()'),
        step('web', 'Trình duyệt bắt đầu start()', {'Trang HTML': '/', 'Script defer': '/static/app.js'}, {'Lượt tải': ['/api/bootstrap', '/api/history', '/api/ai-status'], 'View mặc định': 'chat'}, 'start() lấy cấu hình công khai, lịch sử và tình trạng AI rồi gọi setView().', 'start()'),
    )])

    plans['knowledge-admin'] = dict(label='05 · Quản trị và duyệt FAQ', scenarios=[scenario(
        'Tài liệu nháp → người quản trị duyệt', 'Tài khoản, token, tài liệu và SQL đều là ví dụ. Không tạo hay sửa dữ liệu ứng dụng.',
        step('web', 'Quản trị gửi biểu mẫu đăng nhập', {'Biểu mẫu': 'login-form', 'password': '<không hiển thị>'}, {'method': 'POST', 'path': '/api/admin/login'}, 'renderLogin() đăng ký onsubmit; không đưa mật khẩu thật vào sơ đồ.', 'renderLogin() callback'),
        step('main', 'Kiểm tra mật khẩu và tạo phiên', {'password': '<không hiển thị>', 'admin-auth.json': '<hash/salt ngoài sơ đồ>'}, {'Cookie': 'haui_admin=<token minh họa>', 'Thời hạn': '8 giờ'}, 'login() dùng scrypt/compare_digest; DB chỉ lưu digest token.', 'login()'),
        step('web', 'Nhập tài liệu tham khảo', {'file': 'quy-dinh-minh-hoa.txt', 'Nội dung': 'Văn bản tham khảo cần được rà soát.'}, {'method': 'POST', 'path': '/api/admin/documents', 'encoding': 'multipart/form-data'}, 'Upload không đồng nghĩa với công bố vào kho trả lời.', 'renderAdmin() upload callback'),
        step('db', 'Lưu tài liệu ở trạng thái nháp', {'Văn bản được trích xuất': 'Ví dụ văn bản tham khảo'}, {'documents.status': 'draft', 'FAQ mới được công bố': False}, 'upload_document() chỉ thêm documents và audit, không gọi reload_engine().', 'upload_document() → conn()'),
        step('web', 'Con người biên tập FAQ', {'Tài liệu nháp': 'Văn bản tham khảo'}, {'question': q, 'answer': answer, 'source_url': faq['source_url'], 'status': 'approved'}, 'Người quản trị phải đọc, gắn nguồn HTTPS chính thức và chủ động chọn approved.', 'openFaq() → faq-form.onsubmit'),
        step('main', 'Kiểm tra nguồn và ghi FAQ', {'status': 'approved', 'intent': 'hoc_phi', 'source_url': faq['source_url']}, {'validate_faq': 'hợp lệ', 'SQL': 'INSERT/UPDATE faqs + audit'}, 'validate_faq() kiểm tra chủ đề, trạng thái, loại, tên miền nguồn và ngày rà soát.', 'create_faq() / update_faq()'),
        step('engine', 'Nạp lại FAQ được phép trả lời', {'rows từ SQLite': ['approved', 'draft', 'archived']}, {'rows trong Engine': 'chỉ approved + chưa hết hạn', 'Tác dụng': 'Lượt hỏi sau dùng kho đã cập nhật'}, 'rebuild() thay chỉ mục trong bộ nhớ với khóa bảo vệ.', 'reload_engine() → Engine.rebuild()'),
    )])

    plans['research-training'] = dict(label='06 · Huấn luyện và thực nghiệm', scenarios=[scenario(
        'Chọn mô hình → demo không lưu lịch sử', 'Dữ liệu chia tập và thuật toán đúng theo source; thao tác huấn luyện, thời gian và gọi API được minh họa offline.',
        step('train', 'Đọc bộ dữ liệu cố định', {'file': 'data/original_50.csv'}, {'Train': 30, 'Validation': 10, 'Test': 10, 'Số nhãn': 5}, 'Giữ nguyên 50 câu và chia tập; không tạo một holdout độc lập mới.', 'scripts/train.py:main()'),
        step('pipe', 'Fit pipeline trên Train', {'Train': '30 câu', 'Cấu hình': '4 MLP + 2 LinearSVC'}, {'Pipeline': 'TF-IDF → classifier', 'Callback': 'normalize_classification', 'Đánh giá chọn': 'Validation Macro-F1'}, 'TF-IDF chỉ fit Train; normalization giữ dấu, từ phủ định và được lưu trong pipeline.', 'Pipeline.fit() → measure()'),
        step('train', 'Chọn trước khi xem Test', {'Ứng viên': 'điểm Validation'}, {'Lựa chọn được lưu': 'reports/selection.json', 'Nếu hòa': 'ưu tiên LinearSVC'}, 'Lưu lựa chọn ứng dụng trước khi tính Test; không refit Train+Validation.', 'scripts/train.py:main()'),
        step('disk', 'Lưu artifacts và báo cáo', {'Pipeline đã chọn': selection, 'Kết quả Test': '10 câu đã từng được xem'}, {'models': ['mlp.joblib', 'linearsvc.joblib', 'intent.joblib'], 'reports': ['selection.json', 'experiments.json']}, 'Runtime nạp hai pipeline theo tên và selection khi tạo Engine mới.', 'joblib.dump() / write()'),
        step('web', 'Chạy câu hỏi ở trang thực nghiệm', {'question': q, 'model_mode': 'retrieval'}, {'POST': '/api/experiments/route'}, 'Lựa chọn mode chỉ áp dụng cho lượt thử này.', 'loadExperiments() form callback'),
        step('api', 'Định tuyến không lưu hội thoại', input_q, {'status': 'answered', 'Gọi generate()': False, 'Ghi messages': False, 'Đổi default_model': False}, 'research_route() gọi route(), bỏ evidence rồi trả JSON; không gọi provider.', 'research_route() → Engine.route()'),
    )])

    plans['operations'] = dict(label='07 · Vận hành và sao lưu', scenarios=[scenario(
        'Timer → snapshot SQLite → lưu archive', 'Chỉ trình diễn cấu hình và thao tác I/O. Không gọi systemd, không đọc DB hoặc bí mật đang vận hành.',
        step('sys', 'Timer đến lịch sao lưu', {'OnCalendar': '03:00 Asia/Ho_Chi_Minh', 'Persistent': True}, {'Unit': 'student-backup.service'}, 'Timer systemd tương ứng kích hoạt service sao lưu.', 'student-backup.timer'),
        step('backup', 'Chạy script sao lưu', {'ExecStart': 'python scripts/backup.py'}, {'Bước tiếp': 'SQLite Connection.backup()'}, 'Script backup dùng thư viện chuẩn, không import app.main.', 'scripts/backup.py'),
        step('disk', 'Tạo snapshot nhất quán', {'Nguồn': 'data/student.db'}, {'Snapshot minh họa': 'backups/snapshot-demo.db', 'Permission': '0600'}, 'Connection.backup() tạo bản sao SQLite trước khi nén archive.', 'sqlite3.Connection.backup()'),
        step('backup', 'Nén các file trong allowlist', {'Snapshot': 'snapshot-demo.db', 'File nếu tồn tại': ['admin-auth.json', 'ai-settings.json', 'faqs.json', 'intent.joblib', 'experiments.json']}, {'Archive minh họa': 'backups/backup-demo.tar.gz', 'Permission': '0600'}, 'Chỉ hiển thị tên file; không lấy nội dung mật khẩu, token hoặc API key.', 'tarfile.open() / tar.add()'),
        step('disk', 'Dọn snapshot và giữ 14 bản', {'Danh sách archive': 'được sắp theo tên timestamp'}, {'Snapshot tạm': 'xóa sau khi nén', 'Số archive giữ lại': 14}, 'Allowlist hiện tại không bao gồm mlp.joblib, linearsvc.joblib hay selection.json.', 'scripts/backup.py:13–15'),
    )])

    plans['modules'] = dict(label='08 · Phụ thuộc giữa các module', scenarios=[scenario(
        'Khám phá import · không phải một request', 'Mỗi khối cho thấy module nhận phụ thuộc nào và cung cấp symbol nào. Đây là sơ đồ phụ thuộc, không phải thứ tự chạy của một request.',
        step('main', 'API phụ thuộc Engine', {'Import': 'from .engine import Engine, ROOT, LABELS, safe_url, normalize, active'}, {'Module cung cấp': 'ASGI app + handlers + DB/auth helpers'}, 'app.main sở hữu I/O SQLite và gọi Engine; không import mã JavaScript.', 'app.main', edges=['main-to-engine']),
        step('engine', 'Engine phụ thuộc bộ chuẩn hóa', {'Import': 'from .text import normalize_classification'}, {'Module cung cấp': ['Engine', 'normalize', 'safe_url', 'active', 'LABELS']}, 'Retrieval normalize() dùng normalize_classification() làm bước nền rồi mở rộng/bỏ dấu.', 'app.engine', edges=['engine-to-text']),
        step('text', 'Hàm chuẩn hóa dùng chung', {'text': '  Em KHÔNG đăng ký được  '}, {'normalize_classification(text)': 'em không đăng ký được'}, 'Giữ dấu và phủ định; callback này được pipeline huấn luyện lưu cùng joblib.', 'app.text.normalize_classification'),
        step('model-tools', 'Script dữ liệu và mô hình', {'Phụ thuộc': ['app.engine', 'app.text (train)']}, {'Đầu ra': ['FAQ/CSV/manifest', 'pipeline joblib', 'báo cáo JSON']}, 'Các script thực nghiệm đọc dữ liệu công khai đã lưu; không dùng DB hội thoại.', 'train / evaluate_faq / prepare_data'),
        step('api-tools', 'Script quản trị và smoke check', {'Phụ thuộc': 'app.main'}, {'Sử dụng': ['password_hash', 'conn', 'app', 'ENGINE']}, 'Import app.main cũng dựng ENGINE; smoke check tách STUDENT_ROOT tạm trước khi import.', 'initialize_auth / reset_admin / check_alignment_inprocess'),
        step('tests', 'Tests kiểm tra các module', {'Phụ thuộc': ['app.main', 'app.engine', 'app.text']}, {'Đầu ra': 'assertions / pytest results', 'Dữ liệu': 'thư mục tạm'}, 'Tests dùng fixtures và dữ liệu thử; không phải một lớp trong đường đi production.', 'tests/conftest.py + test modules'),
    )])

    # Every node, including branches and optional components, has an inspector.
    extras = {
        'architecture': {
            'models': step('models', 'Pipeline phân loại đã lưu', {'Tệp': ['mlp.joblib', 'linearsvc.joblib'], 'Lựa chọn': 'selection.json'}, {'Engine.models': ['mlp', 'linearsvc'], 'default_model': selection.lower()}, 'Đọc trong __init__; file thay đổi không tự nạp lại Engine đang chạy.', 'Engine.__init__()'),
            'train': step('train', 'Nhánh thực nghiệm offline', {'Dữ liệu': 'original_50.csv · 30/10/10'}, {'Artifacts': ['mlp.joblib', 'linearsvc.joblib', 'intent.joblib'], 'Báo cáo': 'experiments.json'}, 'Không phải bước bắt buộc trong mỗi lượt hỏi của sinh viên.', 'scripts/train.py:main()'),
            'tunnel': step('tunnel', 'Tunnel · quan hệ triển khai suy luận', {'Cấu hình example': 'hostname ttech.io.vn'}, {'Đích example': 'http://127.0.0.1:8088', 'Trạng thái đang chạy': 'chưa xác minh'}, 'Service đọc cấu hình ngoài repository; không thể suy ra tình trạng deployment chỉ từ file example.', 'cloudflared configuration', inferred=True, condition='SUY LUẬN · cấu hình mẫu, chưa xác minh runtime'),
        },
        'chat': {
            'llm': step('llm', 'Nhánh AI tùy chọn', {'Điều kiện': 'answered + use_ai + enabled + lấy được khóa', 'Payload': 'question + selected FAQ evidence'}, {'Ví dụ JSON': {'answer': answer, 'supported': True}, 'Sau đó': 'Engine kiểm tra length / URL / numbers'}, 'Đây là payload minh họa; không phải câu trả lời thu được từ provider thật.', 'Engine.generate() → httpx.Client.post()', condition='Nhánh tùy chọn · không chạy trong kịch bản use_ai=false'),
        },
        'routing': {
            'vague-exit': step('vague-exit', 'Hỏi rõ câu quá mơ hồ', {'topics': [], 'top score': '< .30 hoặc không có FAQ'}, {'status': 'clarify', 'sources': []}, 'Nhánh câu không rõ chủ đề kết thúc sớm nếu tìm toàn kho chưa đủ khớp.', 'Engine.route():126–129'),
            'enough-exit': step('enough-exit', 'Chưa có nguồn đủ để xét', {'ranked': [], 'Hoặc câu không có chủ đề': 'top score < .30'}, {'status': 'out_of_scope', 'fallback_reason': 'insufficient_retrieval_evidence'}, 'Thiếu bằng chứng truy hồi thì không trả lời bằng FAQ.', 'Engine.route():149–150'),
            'conflict-exit': step('conflict-exit', 'Bằng chứng yếu hoặc xung đột', {'Điều kiện một trong': ['score < .13', 'conflict', 'close_topics']}, {'status': 'clarify', 'fallback_reason': 'weak_or_conflicting_evidence'}, 'Các kiểm tra chạy trước lexical gate; khi điều kiện trước đã đúng thì Python short-circuit.', 'Engine.route():154–155'),
            'lexical-exit': step('lexical-exit', 'Không khớp năm hoặc từ vựng', {'evidence_matches': False}, {'status': 'clarify', 'fallback_reason': 'weak_or_conflicting_evidence'}, 'Nhận đúng chủ đề vẫn chưa đủ để kết luận FAQ là bằng chứng phù hợp.', 'evidence_matches() → Engine.route()'),
        },
        'operations': {
            'app': step('app', 'Các process dịch vụ', {'ExecStart': ['uvicorn app.main:app', 'ollama serve']}, {'Cổng cấu hình': ['8088', '127.0.0.1:11435'], 'Đang hoạt động': 'chưa đo trong bản trình diễn'}, 'Quan hệ là cấu hình đã đối chiếu; service đã active hay chưa cần kiểm tra runtime riêng.', 'deploy/*.service'),
        },
    }

    common_style = ''
    coverage = {}
    for diagram_id, plan in plans.items():
        native = (ROOT / f'{diagram_id}.html').read_text()
        if not common_style:
            common_style = '\n'.join(re.findall(r'<style[^>]*>([\s\S]*?)</style>', native.split('</head>', 1)[0]))
        start = native.index('<svg', native.index('<div class="diagram-container"'))
        plan['svg'] = native[start:native.index('</svg>', start) + 6]
        candidate = json.loads((ROOT / f'candidates/{diagram_id}.json').read_text())
        nodes = candidate.get('components', candidate.get('participants', candidate.get('nodes')))
        plan['nodeLabels'] = {n['id']: n['label'] for n in nodes}
        plan['sources'] = source_map[diagram_id]
        inspector = {}
        for item in plan['scenarios']:
            for entry in item['steps']:
                inspector.setdefault(entry['node'], entry)
        inspector.update(extras.get(diagram_id, {}))
        missing = set(plan['nodeLabels']) - set(inspector)
        assert not missing, (diagram_id, missing)
        edge_ids = set(re.findall(r'data-edge-id="([^"]+)"', plan['svg']))
        for item in plan['scenarios']:
            for index, entry in enumerate(item['steps']):
                assert entry['node'] in plan['nodeLabels']
                assert set(entry.get('edges', [])) <= edge_ids, (diagram_id, entry)
                if index and not entry.get('edges'):
                    previous = item['steps'][index - 1]['node']
                    matched = re.findall(r'<[^>]+data-edge-from="' + re.escape(previous) + r'"[^>]+data-edge-to="' + re.escape(entry['node']) + r'"[^>]+data-edge-id="([^"]+)"', plan['svg'])
                    entry['edges'] = list(dict.fromkeys(matched))
        plan['inspector'] = inspector
        coverage[diagram_id] = dict(nodes=len(nodes), inspectable_nodes=len(inspector), scenarios=len(plan['scenarios']), steps=sum(len(s['steps']) for s in plan['scenarios']))

    data = dict(mode='illustrative-offline', revision=SOURCE_REVISION, diagrams=plans)
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    shell = '''<!doctype html>
<html lang="vi" data-theme="dark" data-motion="still" data-preset="classic">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HaUI Assist · Trình diễn input và output</title>
<style>__ARCHIFY_STYLE__</style><style>__PLAYER_STYLE__</style><style>__DEFENSE_STYLE__</style></head>
<body class="presentation-shell">
<header><div><div class="eyebrow">HAUI ASSIST / THUYẾT TRÌNH KIẾN TRÚC</div><h1>Theo dõi dữ liệu qua từng khối</h1><p class="subtitle">Khối sáng đến đâu · đầu vào và đầu ra hiện đến đó</p></div><nav class="header-actions"><a href="index.html">Tổng quan</a><button id="theme" type="button">Sáng / Tối</button><button id="fullscreen" type="button">⛶ Toàn màn hình</button></nav></header>
<div class="demo-banner"><strong>MÔ PHỎNG OFFLINE</strong> · Payload, điểm số và kết quả là ví dụ minh họa theo mã nguồn. Trang này không gọi API, không chạy AI và không ghi dữ liệu ứng dụng.</div>
<div class="toolbar"><label>Sơ đồ<select id="diagram-select"></select></label><label class="scenario">Kịch bản<select id="scenario-select"></select></label><a id="original-link" href="architecture.html" target="_blank" rel="noopener">Mở sơ đồ Archify gốc ↗</a></div>
<main class="workspace"><section class="graph-card" aria-label="Sơ đồ đang trình diễn"><div class="graph-heading"><h2 id="diagram-title"></h2><label class="follow"><input type="checkbox" id="follow-node"> Phóng theo khối</label></div><div class="diagram-container" id="diagram-stage"></div><div class="graph-legend"><span><b>●</b> Khối đang xử lý</span><span>Đã đi qua: sáng vừa</span><span>Bấm vào khối để xem input/output</span></div><div class="scenario-copy" id="scenario-description"></div><div class="controls"><button id="restart" type="button" aria-label="Về bước đầu">↺</button><button id="previous" type="button">← Lùi</button><button id="play" class="primary" type="button" aria-pressed="false">▶ Phát</button><button id="next" type="button">Tiếp →</button><label class="speed-label" for="speed">Mỗi bước</label><select id="speed"><option value="1">1 giây</option><option value="3">3 giây</option><option value="5" selected>5 giây</option><option value="8">8 giây</option></select></div><div class="progress-row"><input id="progress" type="range" min="0" max="1" value="0" aria-label="Chọn bước trình diễn"><span id="step-number"></span></div><p id="playback-status" class="playback-status" role="status"></p><div id="step-list" class="step-list" role="group" aria-label="Các bước trong kịch bản"></div></section>
<aside class="io-panel" aria-label="Đầu vào và đầu ra của khối đang sáng"><div class="step-meta"><span id="branch-status"></span><h2 id="step-title"></h2><code id="function-name"></code><p id="step-explanation"></p></div><section class="io-section"><h3 class="io-title input">↘ INPUT · ĐẦU VÀO</h3><div id="input-value"></div><details><summary>Xem JSON đầu vào</summary><pre id="input-json"></pre></details></section><section class="io-section"><h3 class="io-title output">↗ OUTPUT · ĐẦU RA</h3><div id="output-value"></div><details><summary>Xem JSON đầu ra</summary><pre id="output-json"></pre></details></section><div class="speaker"><div class="speaker-label">GỢI Ý LỜI THUYẾT TRÌNH</div><p id="speaker-note"></p></div><div class="sources">Đối chiếu mã nguồn tại __REVISION__<div id="source-links"></div></div></aside></main>
<section id="defense-step" class="defense-panel" aria-label="Đối chiếu lưu đồ, phương pháp và code"></section>
<footer class="footer-note">Phím tắt khi không chọn nút hoặc ô nhập: Space = phát / dừng · ← / → = lùi / tiếp. Mỗi bước có phần đối chiếu lưu đồ, phương pháp, đoạn code và gợi ý vấn đáp. Mũi tên và bố cục lấy từ SVG Archify đã kiểm tra; thứ tự và dữ liệu minh họa thuộc lớp trình diễn riêng.</footer>
<script type="application/json" id="presentation-data">__DATA__</script><script>__DEFENSE_DATA__</script><script>__DEFENSE_SCRIPT__</script><script>__PLAYER_SCRIPT__</script></body></html>'''
    replacements = {'__ARCHIFY_STYLE__': common_style, '__PLAYER_STYLE__': (ROOT / 'presentation.css').read_text(), '__PLAYER_SCRIPT__': (ROOT / 'presentation.js').read_text(), '__DATA__': encoded, '__REVISION__': SOURCE_REVISION[:12], '__DEFENSE_STYLE__': (PROJECT / 'app/static/defense-guide.css').read_text(), '__DEFENSE_DATA__': (PROJECT / 'app/static/defense-lessons.js').read_text(), '__DEFENSE_SCRIPT__': (PROJECT / 'app/static/defense-guide.js').read_text()}
    for marker, content in replacements.items():
        shell = shell.replace(marker, content)
    destination = ROOT / 'presentation.html'
    destination.write_text(shell)
    (ROOT / 'evidence/presentation-build.json').write_text(json.dumps(dict(mode=data['mode'], source_revision=SOURCE_REVISION, native_diagrams_modified=False, coverage=coverage, artifact_sha256=hashlib.sha256(destination.read_bytes()).hexdigest()), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()

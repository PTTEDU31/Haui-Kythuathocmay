"""Publish only selected, public code excerpts for the flowchart defense guide.

No app import, runtime settings, conversation DB or model/provider calls.
Run again after changing a cited source file so the line numbers stay current.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SOURCES = {
    'app/main.py', 'app/engine.py', 'app/text.py', 'scripts/train.py',
    'scripts/backup.py', 'app/live_trace.py', 'app/tracing.py',
}


def excerpt(path, needle, count=8):
    assert path in PUBLIC_SOURCES
    text = (ROOT / path).read_text()
    lines = text.splitlines()
    matches = [i for i, line in enumerate(lines) if needle in line]
    assert len(matches) == 1, (path, needle, matches)
    start = matches[0]
    end = min(len(lines), start + count)
    return dict(path=path, line=start + 1, end_line=end,
                code='\n'.join(lines[start:end]),
                sha256=hashlib.sha256(text.encode()).hexdigest())


def lesson(key, title, group, flow, method, implementation, say, caution, refs, qa):
    return dict(id=key, title=title, group=group, flow=flow, method=method,
                implementation=implementation, say=say, caution=caution,
                refs=refs, qa=dict(question=qa[0], answer=qa[1]))


def build():
    lessons = [
        lesson('request', '01 · Nhận câu hỏi', 'Luồng chat',
               'Khối Trình duyệt → API: nhận câu hỏi và lựa chọn bật/tắt AI.',
               'HTTP JSON, kiểm tra schema Pydantic và giới hạn đầu vào.',
               'Chat khai báo question dài 1–1500 ký tự. chat() bỏ khoảng trắng và từ chối câu không có nội dung, rồi chuyển q cho Engine.route(). Đây là xử lý đầu vào, chưa phải bước học máy.',
               'Em nhận câu hỏi qua API, kiểm tra dữ liệu hợp lệ rồi mới đưa vào bước định tuyến. Khối này tương ứng Chat và chat() trong app/main.py.',
               'Một request hợp lệ chưa bảo đảm nội dung thuộc phạm vi hoặc có câu trả lời.',
               [excerpt('app/main.py', 'class Chat(BaseModel):', 3), excerpt('app/main.py', 'def chat(body:Chat', 6)],
               ('Câu rỗng được xử lý ở đâu?', 'Pydantic kiểm tra độ dài; chat() kiểm tra lại sau strip() và normalize(), trả HTTP 422 khi không còn nội dung.')),
        lesson('history', '02 · Đọc ngữ cảnh', 'Luồng chat',
               'Khối SQLite → API: đọc các câu trả lời trước của phiên hiện tại.',
               'SQLite, truy vấn tham số hóa và ngữ cảnh hội thoại bằng quy tắc.',
               'chat() lấy tối đa 4 result của assistant theo session_id. route() chỉ dùng câu trả lời gần nhất khi câu hỏi ngắn và có mẫu tiếp nối; không dùng toàn bộ lịch sử để huấn luyện lại mô hình.',
               'Em lấy lịch sử của đúng phiên bằng truy vấn có tham số. Ngữ cảnh chỉ hỗ trợ một số câu hỏi tiếp nối như “Vậy hồ sơ cần gì?”.',
               'Đây là ngữ cảnh theo quy tắc, không phải bộ nhớ dài hạn hay mô hình tự học sau mỗi lượt chat.',
               [excerpt('app/main.py', "with span('db','chat() · SELECT history'", 4), excerpt('app/engine.py', 'if not topics and len(n.split())<=12', 7)],
               ('Bot có tự học từ hội thoại không?', 'Không. Tin nhắn được lưu để xem lịch sử/ngữ cảnh; pipeline chỉ thay đổi khi chạy huấn luyện và nạp lại mô hình.')),
        lesson('normalize', '03 · Chuẩn hóa tiếng Việt', 'Luồng chat',
               'Khối Nhận câu hỏi và chuẩn hóa: đưa cách viết về dạng nhất quán.',
               'Unicode NFC, chữ thường, gộp khoảng trắng; tách chuẩn hóa phân loại và truy hồi.',
               'normalize_classification() giữ dấu và từ phủ định. normalize() dùng bước nền đó, mở rộng viết tắt rồi bỏ dấu cho truy hồi. Pipeline đã lưu chứa đúng bộ biến đổi dùng lúc huấn luyện.',
               'Em có hai kiểu chuẩn hóa: phân loại giữ dấu để nhất quán dữ liệu huấn luyện; truy hồi hỗ trợ câu gõ không dấu và viết tắt.',
               'Không nói toàn bộ hệ thống đều bỏ dấu. Chuẩn hóa phân loại cũng không loại từ “không”, “chưa”.',
               [excerpt('app/text.py', 'def normalize_classification(', 3), excerpt('app/engine.py', 'def normalize(s):', 7)],
               ('Vì sao phải dùng cùng chuẩn hóa khi train và dự đoán?', 'Nếu biến đổi khác nhau, từ/cụm từ có thể không khớp từ vựng đã học, khiến vector đầu vào và dự đoán thay đổi.')),
        lesson('rules', '04 · Kiểm tra quy tắc và chủ đề', 'Luồng chat',
               'Các khối chào hỏi/an toàn → chủ đề → nhiều chủ đề? → hỏi lại hoặc đi tiếp.',
               'So khớp danh sách và biểu thức chính quy; trả về sớm theo thứ tự ưu tiên.',
               'route() xét chào hỏi và nội dung bị loại trước. topic_patterns nhận chủ đề tường minh; nếu len(topics)>1 thì trả clarify. CTSV/KTX là nhánh mở rộng, không ép vào 5 lớp đã huấn luyện.',
               'Các hình thoi trong lưu đồ được triển khai bằng if và return. Khi điều kiện hỏi lại đúng, hàm kết thúc nên các bước phía sau không chạy.',
               'Regex là quy tắc do người viết, không phải kiến thức tự học của MLP hoặc LinearSVC. Quy tắc hiện tại không nhận biết được mọi câu ngoài phạm vi.',
               [excerpt('app/engine.py', "if n in ['chao'", 6), excerpt('app/engine.py', 'if len(topics)>1:', 2)],
               ('Câu hỏi có cả học phí và học bổng thì sao?', 'route() trả clarify để người dùng chọn chủ đề trước; không cần chạy bộ phân loại cho nhánh đã kết thúc.')),
        lesson('routing', 'Định tuyến · Chọn nhánh thực thi', 'Luồng chat',
               'Toàn bộ lưu đồ định tuyến: kiểm tra quy tắc → tìm chủ đề → phân loại/truy hồi khi cần → kiểm tra bằng chứng → trả lời hoặc hỏi lại.',
               'Kết hợp quy tắc if/return, bộ phân loại học có giám sát và truy hồi FAQ. Mỗi phương pháp đảm nhiệm một phần của luồng.',
               'Engine.route() điều phối các bước. Các return sớm dừng ở nhánh chào hỏi, ngoài phạm vi hoặc cần làm rõ. Nếu đi tiếp, code chọn nhóm tìm kiếm, gọi search(), rồi xét ngưỡng điểm, xung đột chủ đề và evidence_matches(). Không phải câu nào cũng chạy hết lưu đồ.',
               'Em chỉ vào điều kiện if tương ứng với hình thoi và lệnh return tương ứng với nhánh kết thúc. Với lượt hỏi này, em dùng Output và các lời gọi con trong trace để chứng minh những bước đã thực sự chạy.',
               'Một sự kiện Engine.route() chỉ chứng minh hàm điều phối được gọi. Phải xem status, routing và các lời gọi con trước khi nói MLP/LinearSVC hay kiểm tra bằng chứng đã chạy.',
               [excerpt('app/engine.py', 'def route(self,q,', 12), excerpt('app/engine.py', 'if len(topics)>1:', 8), excerpt('app/engine.py', "trace={'model_mode'", 12)],
               ('Vì sao chào hỏi không có sự kiện phân loại?', 'Nhánh chào hỏi return trước vị trí gọi classify(). Lệnh return kết thúc hàm, nên các khối phân loại và truy hồi phía sau không được thực thi.')),
        lesson('classify', '05 · Dự đoán chủ đề', 'Luồng chat',
               'Khối MLP/LinearSVC → chọn chủ đề để định hướng tìm FAQ khi phù hợp.',
               'Học có giám sát: pipeline TF-IDF → một bộ phân loại đã huấn luyện.',
               'classify() chọn pipeline theo model_mode rồi gọi model.predict([q]). Trong route(), nhãn chỉ thu hẹp nhóm tìm kiếm khi chưa có chủ đề tường minh; quy tắc, ngữ cảnh và chủ đề mở rộng được ưu tiên.',
               'Em dùng mô hình để dự đoán ý định, không để viết câu trả lời. Nhãn dự đoán có thể định hướng tìm FAQ nhưng vẫn phải kiểm tra độ khớp riêng.',
               'Hai mô hình là lựa chọn thay thế, không phải MLP chạy trước rồi LinearSVC chạy sau. classifier_used trong routing mới cho biết nhãn đã thực sự quyết định nhóm tìm kiếm.',
               [excerpt('app/engine.py', 'def classify(self,q,', 15), excerpt('app/engine.py', 'if classification and not category:', 8)],
               ('Nhãn mô hình được dùng ở dòng nào?', 'category=classification["intent"] rồi self.search(q,category) khi chưa có chủ đề tường minh. Nếu quy tắc đã chọn chủ đề, nhãn không tự ghi đè chủ đề đó.')),
        lesson('tfidf', 'TF-IDF · Biến câu thành số', 'Phương pháp',
               'Khối Pipeline/TF-IDF trước bộ phân loại; bộ TF-IDF truy hồi là chỉ mục riêng.',
               'Trọng số tần suất từ và độ hiếm trong tập văn bản; word n-gram (1,2), chuẩn L2.',
               'TfidfVectorizer nằm trong Pipeline. pipe.fit() chỉ nhận 30 câu Train nên từ vựng và IDF không học từ Validation/Test. Khi gọi predict(), pipeline tự transform câu mới bằng vectorizer đã fit. Giới hạn 500 đặc trưng, thực tế 327 trong lần thực nghiệm đã lưu.',
               'Em chuyển câu hỏi thành vector số bằng TF-IDF. Những từ/cụm từ có khả năng phân biệt văn bản tạo tín hiệu cho bộ phân loại; phần này do TfidfVectorizer của sklearn thực hiện.',
               'Không phải embedding ngữ nghĩa kiểu Transformer. Từ không có trong từ vựng đã học không tạo đặc trưng mới khi dự đoán.',
               [excerpt('scripts/train.py', 'TFIDF = dict(', 2), excerpt('scripts/train.py', "pipe = Pipeline([('tfidf'", 6)],
               ('fit khác transform thế nào?', 'fit học từ vựng và IDF trên Train; transform dùng những giá trị đã học để đổi câu thành vector, không học lại từ Test.')),
        lesson('mlp', 'MLP · Mạng nơ-ron phân loại', 'Phương pháp',
               'Nhánh MLP trong khối huấn luyện và khối phân loại ý định.',
               'Mạng truyền thẳng: vector TF-IDF → lớp ẩn ReLU → 5 đầu ra softmax.',
               'Code dự án gọi MLPClassifier(..., solver="lbfgs", max_iter=1000, random_state=42), pipe.fit() và model.predict(). Các phép nhân trọng số, ReLU, softmax và tính gradient do sklearn thực hiện; dự án không tự viết lại mạng. Cấu hình đã chọn có 327 đầu vào, 16 nơ-ron ẩn và 5 đầu ra; alpha=0.001.',
               'MLP kết hợp các đặc trưng qua lớp ẩn phi tuyến. Khi train, mạng tính sai lệch với nhãn đúng, lan truyền ngược để tính gradient rồi L-BFGS tối ưu trọng số. Khi dùng, predict chọn nhãn có đầu ra cao nhất.',
               'predict_proba chưa được hiệu chỉnh; không phải xác suất chatbot trả lời đúng. Không nói đang dùng Adam hoặc tự xây mạng bằng vòng lặp nếu code dùng sklearn/L-BFGS.',
               [excerpt('scripts/train.py', 'for name in (\'MLP\', \'LinearSVC\'):', 8), excerpt('scripts/train.py', "pipe = Pipeline([('tfidf'", 6), excerpt('app/engine.py', "kind='predict_proba'", 5)],
               ('Phi tuyến nằm ở đâu và vì sao cần?', 'ReLU ở lớp ẩn tạo tính phi tuyến. Nếu các lớp chỉ cộng/nhân tuyến tính thì ghép nhiều lớp vẫn tương đương một phép biến đổi tuyến tính. Trong code dùng ReLU mặc định của MLPClassifier.')),
        lesson('svc', 'LinearSVC · Ranh giới tuyến tính', 'Phương pháp',
               'Nhánh LinearSVC đối chứng trong huấn luyện và phân loại ý định.',
               'SVM tuyến tính, biên mềm; One-vs-Rest cho 5 lớp, chọn điểm wᵀx+b cao nhất.',
               'LinearSVC(C=..., random_state=42) học trọng số bằng fit(). Mặc định dùng L2 và squared_hinge; C cân bằng điều chuẩn và phạt vi phạm biên. Code khảo sát C=0.1/1.0, chọn C=0.1. Runtime gọi predict() và decision_function(); không dùng kernel RBF.',
               'Em dùng LinearSVC làm đối chứng. Mô hình học các siêu phẳng tuyến tính có biên lớn với mức phạt vi phạm. Với 5 nhãn, mỗi bộ phân biệt một lớp với phần còn lại; nhãn có điểm cao nhất được chọn.',
               'decision_function có thể âm; lớn nhất vẫn được chọn. Không đổi điểm này thành phần trăm hoặc so trực tiếp với predict_proba của MLP. C lớn không đồng nghĩa tổng quát hóa tốt hơn.',
               [excerpt('scripts/train.py', 'for name in (\'MLP\', \'LinearSVC\'):', 8), excerpt('app/engine.py', "pred=str(model.predict([q])[0])", 7)],
               ('Vì sao chọn LinearSVC thay vì khẳng định MLP tốt hơn?', 'Hai mô hình hòa Macro-F1 Validation; quy tắc lưu trước khi tính Test ưu tiên LinearSVC. MLP phức tạp hơn không tự bảo đảm kết quả tốt hơn trên dữ liệu mới.')),
        lesson('search', '06 · Tìm FAQ phù hợp', 'Luồng chat',
               'Khối tìm toàn kho / tìm trong chủ đề → xếp hạng các FAQ.',
               'Truy hồi từ vựng, kết hợp cosine TF-IDF từ/cụm từ và đoạn ký tự.',
               'rebuild() tạo word vectorizer (1,2) và char_wb (3,5). search() tính 0.55 × word cosine + 0.45 × char cosine rồi argsort giảm dần. Vì TF-IDF chuẩn L2, tích vô hướng trong code là cosine. category lọc chủ đề, active() loại FAQ chưa duyệt/hết hạn.',
               'Sau khi biết chủ đề, em còn phải chọn đúng câu trả lời. Em tính độ giống giữa câu hỏi và FAQ bằng hai nhóm đặc trưng rồi xếp hạng; char n-gram giúp hỗ trợ biến thể cách gõ.',
               'Điểm truy hồi không phải xác suất đúng, cũng không phải điểm của MLP/LinearSVC. Đúng chủ đề chưa bảo đảm đúng FAQ.',
               [excerpt('app/engine.py', 'self.word=TfidfVectorizer', 5), excerpt('app/engine.py', 'def search(self,q,', 14)],
               ('Hai bộ TF-IDF có phải dùng chung một từ vựng?', 'Không. Pipeline phân loại fit trên Train có nhãn; chỉ mục truy hồi word/char fit trên nội dung FAQ được duyệt. Hai bước có mục đích và chuẩn hóa khác nhau.')),
        lesson('evidence', '07 · Kiểm tra đủ bằng chứng?', 'Luồng chat',
               'Các hình thoi đủ khớp? xung đột? khớp năm/từ? → answered, clarify hoặc out_of_scope.',
               'Ngưỡng tương đồng và kiểm tra từ vựng/năm học bằng quy tắc kỹ thuật.',
               'route() kiểm tra ứng viên, ngưỡng .30/.13 và chênh lệch .025 theo điều kiện. evidence_matches() kiểm tra năm trong câu hỏi có trong FAQ, rồi kiểm tra tỷ lệ từ ngoài nhóm từ phổ biến. Nếu yếu hoặc xung đột thì return clarify.',
               'Em không coi nhãn dự đoán là bằng chứng. Em kiểm tra nội dung FAQ có đủ khớp không; nếu chưa đủ thì hỏi lại thay vì tự tạo câu trả lời.',
               'Các ngưỡng là quy tắc khởi tạo chưa tối ưu trên tập độc lập; kiểm tra này không chứng minh FAQ luôn đúng về mặt ngữ nghĩa.',
               [excerpt('app/engine.py', 'def evidence_matches(', 7), excerpt('app/engine.py', 'if not ranked or (not topics', 9)],
               ('Vì sao đã phân loại rồi còn hỏi lại?', 'Phân loại chỉ chọn nhóm. Câu có thể thiếu thông tin, sai năm, không có FAQ đủ khớp hoặc mô hình chọn nhầm nhóm nên cần một bước kiểm tra riêng.')),
        lesson('generate', '08 · Diễn đạt bằng Qwen và fallback', 'Luồng chat',
               'Nhánh tùy chọn gọi AI khi đã có FAQ; lỗi hoặc không hợp lệ → giữ FAQ.',
               'Sinh văn bản có điều kiện từ nội dung truy hồi; kiểm tra JSON, số liệu và URL.',
               'generate() chỉ đi tiếp khi status="answered", AI bật và lấy được khóa. Nó gửi câu hỏi + evidence của FAQ; chỉ thay result["answer"] nếu parsed["supported"] là True và các kiểm tra đạt. except hoặc kiểm tra không đạt giữ câu trả lời cũ; finally giải phóng khóa.',
               'Qwen là mô hình có sẵn dùng để diễn đạt thông tin đã tìm được. Em không huấn luyện Qwen bằng 50 câu. Khi AI lỗi, chatbot dùng lại câu trả lời đã duyệt.',
               'Kiểm tra số, URL và supported chỉ giảm lỗi, không bảo đảm mọi diễn đạt được nguồn hỗ trợ. Lời gọi generate() được trace không đồng nghĩa provider thực sự đã được gọi.',
               [excerpt('app/engine.py', 'def generate(self,question,', 6), excerpt('app/engine.py', 'parsed=json.loads(payload)', 13)],
               ('MLP có sinh ra đoạn trả lời này không?', 'Không. MLP/LinearSVC phân loại ý định; FAQ cung cấp nội dung; Qwen có thể diễn đạt lại, còn server gắn nguồn.')),
        lesson('provider', 'Provider · Gọi mô hình có sẵn', 'Luồng chat',
               'Mũi tên Engine → Provider AI → Engine.',
               'HTTP client gọi Ollama hoặc API tương thích OpenAI; JSON theo schema.',
               'Nhánh Ollama gọi /api/chat với model qwen3:4b, stream=false và schema answer/supported. Ollama là phần mềm phục vụ mô hình, Qwen là mô hình. Trace chỉ thấy request/response ở ranh giới HTTP, không thấy từng phép tính trong Qwen.',
               'Ở đây em chỉ ra dòng c.post gửi nội dung tới Ollama. Đây là sử dụng mô hình đã huấn luyện sẵn, khác với phần em huấn luyện bộ phân loại bằng sklearn.',
               'Không gọi Ollama là thuật toán phân loại; không diễn giải sự kiện HTTP thành trace nội bộ của mô hình ngôn ngữ.',
               [excerpt('app/engine.py', "if provider=='ollama':", 4)],
               ('Ollama và Qwen khác nhau thế nào?', 'Qwen là mô hình ngôn ngữ; Ollama chạy mô hình và cung cấp API HTTP để backend gọi.')),
        lesson('persist', '09 · Lưu và trả kết quả', 'Luồng chat',
               'API → SQLite lưu hai tin nhắn → trả JSON cho trình duyệt.',
               'Lưu dữ liệu theo phiên, truy vấn có tham số và tách bằng chứng nội bộ khỏi response.',
               'chat() bỏ trường evidence, đo latency, tạo message ID, rồi INSERT user và assistant bằng dấu ? và tuple tham số. Nguồn được tạo ở route() từ metadata FAQ, không lấy URL do AI tự nghĩ ra.',
               'Sau khi có kết quả, em lưu câu hỏi và câu trả lời theo phiên rồi trả JSON. Phần này là quản lý dữ liệu ứng dụng, không phải huấn luyện mô hình.',
               'Không lấy thời gian của một lượt có trace để công bố benchmark; trace và truyền dữ liệu có overhead.',
               [excerpt('app/main.py', "result.pop('evidence',None);result['latency_ms']", 8), excerpt('app/engine.py', "source={'id':top['id']", 2)],
               ('Vì sao dùng dấu ? trong SQL?', 'Để truyền tham số tách khỏi câu lệnh SQL, tránh nối trực tiếp dữ liệu người dùng vào cấu trúc truy vấn.')),
        lesson('train', 'Huấn luyện · Học, chọn, đánh giá', 'Nghiên cứu',
               'Sơ đồ huấn luyện: đọc 50 câu → Train → Validation → lưu lựa chọn → Test → lưu pipeline.',
               'Học có giám sát, chia tập cố định và lựa chọn theo Macro-F1 Validation.',
               '30 câu Train dùng fit; 10 Validation dùng chọn 4 cấu hình MLP/2 LinearSVC. selection.json được ghi trước Test. 10 Test được measure sau lựa chọn; không refit Train+Validation. joblib.dump lưu cả vectorizer và classifier để suy luận dùng đúng pipeline.',
               'Em tách ba vai trò: Train để học trọng số, Validation để chọn cấu hình, Test để báo cáo sau lựa chọn. Mô hình được lưu cùng tiền xử lý nên khi chạy không train lại mỗi câu hỏi.',
               'Test đã từng được xem trong lần thực nghiệm trước, không phải tập đánh giá độc lập mới. Dữ liệu tự biên soạn ít, chưa đại diện sinh viên thực tế.',
               [excerpt('scripts/train.py', "splits = {s:", 4), excerpt('scripts/train.py', "name, selected_pipe, best = max", 11), excerpt('scripts/train.py', 'for name, pipe, item in finalists:', 3)],
               ('Vì sao không chọn mô hình theo điểm Test?', 'Nếu dùng Test để lựa chọn hoặc chỉnh cấu hình thì Test tham gia phát triển mô hình và đánh giá sẽ lạc quan; vì thế lựa chọn dựa Validation.')),
        lesson('evaluate', 'Đánh giá · Nhãn khác câu trả lời', 'Nghiên cứu',
               'Khối đo kết quả và báo cáo thực nghiệm, tách khỏi đường đi chat trực tiếp.',
               'Accuracy, Macro-F1, precision/recall từng lớp và confusion matrix.',
               'measure() lấy nhãn thật và pipe.predict(), gọi các hàm metrics của sklearn. Accuracy đếm tỷ lệ đúng; Macro-F1 lấy trung bình F1 của 5 lớp. Đánh giá chọn FAQ được lưu riêng trong reports/faq-evaluation.json.',
               'Cả hai mô hình đạt 7/10 câu Test đúng. Em phân biệt đúng nhãn với đúng FAQ: một câu có thể nhận đúng lịch thi nhưng chọn nhầm hướng dẫn cụ thể.',
               'Một lỗi trên 10 câu thay đổi accuracy 10 điểm phần trăm. Không suy ra chất lượng chatbot thực tế hoặc khẳng định MLP luôn thắng.',
               [excerpt('scripts/train.py', 'def measure(pipe, rows):', 10)],
               ('Vì sao dùng Macro-F1 ngoài Accuracy?', 'Macro-F1 cho mỗi lớp trọng số bằng nhau, giúp nhìn chất lượng giữa các chủ đề; confusion matrix cho biết các nhãn bị nhầm với nhau.')),
        lesson('startup', 'Khởi động · Nạp mô hình và chỉ mục', 'Nghiên cứu',
               'Khối Engine lúc startup: nạp pipeline đã lưu; xây chỉ mục từ FAQ được phép dùng.',
               'Nạp artifact joblib và xây chỉ mục TF-IDF trong bộ nhớ.',
               'Engine.__init__() nạp mlp.joblib và linearsvc.joblib, đọc selection.json để chọn mặc định. rebuild() lọc active(), tạo các vectorizer truy hồi và fit trên FAQ. Đây là nạp mô hình đã học, không phải huấn luyện lại bộ phân loại.',
               'Huấn luyện xảy ra ở script riêng. Khi ứng dụng khởi động, em nạp pipeline đã lưu và xây chỉ mục FAQ để phục vụ truy vấn.',
               'Thay file mô hình không tự thay đối tượng đã nạp trong process. Trace một lượt chat không chứng minh startup vừa chạy.',
               [excerpt('app/engine.py', "for name in ('mlp','linearsvc'):", 5), excerpt('app/engine.py', 'def rebuild(self,rows):', 12)],
               ('intent.joblib có phải file Engine đang nạp không?', 'Không. Engine hiện nạp mlp.joblib và linearsvc.joblib theo tên, rồi chọn mặc định qua reports/selection.json.')),
        lesson('approval', 'Quản trị · Duyệt tri thức', 'Nghiên cứu',
               'Tài liệu tải lên → bản nháp → người biên tập FAQ → duyệt → cập nhật chỉ mục.',
               'Trích văn bản, kiểm tra metadata và duyệt thủ công trước khi sử dụng.',
               'upload_document() nhận TXT/PDF/DOCX và lưu documents ở trạng thái draft. validate_faq() kiểm tra nguồn và trạng thái; chỉ active() mới được đưa vào Engine. Việc tải tài liệu không tự huấn luyện MLP hay tự công bố câu trả lời.',
               'Em tách nhập tài liệu với duyệt tri thức. Người quản trị phải biên tập nội dung và gắn nguồn trước khi FAQ được dùng để trả lời.',
               'PDF scan cần OCR trước; không khẳng định hệ thống hiểu hoặc kiểm chứng tự động mọi nội dung tài liệu.',
               [excerpt('app/engine.py', 'def active(r):', 2), excerpt('app/main.py', 'def validate_faq(body):', 9)],
               ('Upload PDF có làm mô hình học thêm không?', 'Không. File được trích văn bản và lưu nháp; kho FAQ cập nhật qua biên tập/duyệt, còn huấn luyện classifier là quy trình riêng.')),
    ]
    ids = [item['id'] for item in lessons]
    assert len(ids) == len(set(ids))
    payload = json.dumps(dict(version=1, lessons=lessons), ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    destination = ROOT / 'app/static/defense-lessons.js'
    destination.write_text('/* Generated by scripts/build_defense_lessons.py; public source excerpts only. */\nwindow.HauiDefenseLessons = ' + payload + ';\n')
    print(f'Built {len(lessons)} lessons with {sum(len(x["refs"]) for x in lessons)} exact source excerpts.')


if __name__ == '__main__':
    build()

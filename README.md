# HaUI Assist

Ứng dụng hỗ trợ sinh viên Đại học Công nghiệp Hà Nội, triển khai tại máy chủ nội bộ. Có trò chuyện tiếng Việt, truy hồi kết hợp đặc trưng từ và ký tự, AI tạo sinh có dẫn nguồn, quản trị FAQ, duyệt tài liệu, phản hồi câu trả lời, lịch sử theo trình duyệt và trang thực nghiệm học máy.

## Sử dụng

- Ứng dụng: http://192.168.1.118:8088
- Quản trị: http://192.168.1.118:8088/#admin
- Mô hình AI mặc định: Qwen3 4B Q4_K_M qua Ollama, sử dụng GPU trên máy chủ. Ollama chỉ lắng nghe localhost:11435.
- Thư mục cài đặt: `/home/phamtung/student-support`.
- Không cần cài phần mềm hoặc mô hình trên máy người dùng.

Mật khẩu quản trị ứng dụng được bàn giao riêng, không có trong mã nguồn. Có thể đổi mật khẩu ở cuối trang quản trị. Đây là mật khẩu riêng với tài khoản SSH.

## Phạm vi dữ liệu

25 câu trả lời/hướng dẫn cho 7 chủ đề: học phí, đăng ký học phần, lịch thi, học bổng, điểm, công tác sinh viên, ký túc xá. Nguồn lấy từ các website chính thức của HaUI và ghi ngày đối chiếu. FAQ loại `guidance` hướng dẫn tới đơn vị hoặc văn bản phù hợp; không tự nhận là đã có đầy đủ nội dung quy định. Ngày `valid_until` là hạn sử dụng nội bộ do ứng dụng đặt để rà soát lại, không khẳng định ngày hết hiệu lực pháp lý của văn bản.

Ứng dụng chưa kết nối tài khoản sinh viên, lịch thi cá nhân, điểm cá nhân, công nợ hay tình trạng phòng trống. Những yêu cầu này được hướng dẫn về hệ thống chính thức. Quản trị viên có thể bổ sung tài liệu TXT/PDF/DOCX có văn bản; bản nhập luôn ở trạng thái nháp. Người quản trị phải trích nội dung, gắn nguồn HTTPS của HaUI và duyệt FAQ trước khi sử dụng. Tài liệu scan cần được OCR trước.

Hai tài liệu gốc nằm trong `sources/`. Không dùng câu hỏi mẫu trong tài liệu để suy diễn chính sách nhà trường. Đây là ứng dụng nghiên cứu độc lập, chưa có xác nhận của nhà trường về toàn bộ kho câu trả lời.

## Kiến trúc

Frontend HTML/CSS/JavaScript thuần để trình duyệt tải nhẹ. Backend FastAPI chạy một tiến trình Uvicorn. SQLite ở chế độ WAL lưu FAQ, tài liệu nháp, lịch sử và audit. Không cần CDN hoặc dịch vụ bên ngoài khi trò chuyện với mô hình nội bộ.

Phân loại dùng `app/text.py`: Unicode NFC, chữ thường, khoảng trắng, giữ dấu tiếng Việt và từ phủ định; không bỏ stopword. Bộ biến đổi được lưu trong pipeline và dùng lại khi suy luận. Truy hồi dùng bộ biến đổi riêng `app.engine.normalize`, có mở rộng viết tắt và bỏ dấu để hỗ trợ cách gõ không dấu. Truy hồi kết hợp cosine TF-IDF word (1,2) và char_wb (3,5), trọng số 0,55/0,45.

Câu hỏi đi qua quy tắc an toàn, nhận diện nhiều chủ đề, ngữ cảnh lượt gần nhất và chủ đề tường minh. Trong năm chủ đề nghiên cứu, nếu chưa có chủ đề tường minh, nhãn mô hình thực sự thu hẹp nhóm FAQ tìm kiếm; khi có xung đột với chủ đề tường minh thì ưu tiên chủ đề đó. CTSV/KTX đi theo nhánh mở rộng và không bị ép vào năm nhãn. Khi truy hồi toàn kho nhận ra ứng viên mở rộng đủ khớp, hệ thống cũng không ép sang nhãn nghiên cứu.

Nhãn dự đoán không phải bằng chứng cho câu trả lời: chỉ dùng FAQ đã duyệt, còn hạn dùng, đủ độ khớp riêng. Ngưỡng tương đồng 0,30 cho câu chưa rõ chủ đề, 0,13 trong chủ đề, chênh lệch 0,025 để phát hiện xung đột/gần hòa giữa chủ đề và kiểm tra khớp từ vựng/năm học là quy tắc kỹ thuật chưa được hiệu chỉnh trên tập độc lập. Thiếu chứng cứ thì hỏi lại hoặc thông báo chưa có nguồn đủ khớp. `predict_proba` của MLP, `decision_function` của LinearSVC và điểm tương đồng truy hồi có ý nghĩa khác nhau; không dùng chung ngưỡng điểm mô hình và không coi chúng là xác suất câu trả lời đúng đã hiệu chỉnh.

AI chỉ nhận câu hỏi và nội dung FAQ được chọn, không nhận khóa quản trị hoặc toàn bộ cơ sở dữ liệu. Đầu ra JSON theo schema được kiểm tra cấu trúc, số liệu, URL và cờ supported trước khi hiển thị. Nguồn dẫn được gắn bởi server. Khi AI lỗi, quá tải hoặc đầu ra không qua kiểm tra, dùng lại câu trả lời đã đối chiếu. Kiểm tra này giảm lỗi nhưng chưa chứng minh mọi diễn đạt sinh ra đều được nguồn hỗ trợ; cần tiếp tục đánh giá bằng câu hỏi thực tế.

## Thực nghiệm

`data/original_50.csv` giữ đúng câu hỏi, năm nhãn và cách chia của phụ lục DOCX: Train 30 / Validation 10 / Test 10. Đây là dữ liệu minh họa tự biên soạn. Lần chạy này là **tái thực nghiệm trên Test đã từng được xem**, không phải đánh giá độc lập mới. Không thêm diễn đạt lại của Test, không đổi nhãn/cách chia và không refit trên Train+Validation.

DOCX là chuẩn TC1/TC2: TF-IDF word (1,2), `max_features=500`, `min_df=1`, `sublinear_tf=True`, giữ dấu và chuẩn L2; chỉ fit trên Train. Có **327 đặc trưng thực tế**. MLP khảo sát 16/32 neuron, alpha 0,001/0,01, ReLU, L-BFGS, max_iter=1000, seed 42. LinearSVC đối chứng khảo sát C 0,1/1,0, seed 42. Mỗi họ chọn Macro-F1 Validation cao nhất; hòa trong họ lấy cấu hình đầu trong thứ tự đã ghi. Chọn mô hình ứng dụng theo Validation, hòa ưu tiên LinearSVC; ghi `reports/selection.json` trước bước tính Test.

| Mô hình | Cấu hình chọn | Macro-F1 Validation | Accuracy Test | Macro-F1 Test |
| --- | --- | ---: | ---: | ---: |
| MLP | 16 neuron, alpha=0,001 | 1.0000 | 0.7000 | 0.7133 |
| LinearSVC | C=0,1 | 1.0000 | 0.7000 | 0.6933 |

MLP là mô hình nghiên cứu chính; LinearSVC là đối chứng và được chọn mặc định do hòa Validation, không vì kết quả Test. Cả hai không có cảnh báo hội tụ trong lần chạy. MLP có Macro-F1 Test cao hơn ở tập nhỏ này, nhưng chưa chứng minh tốt hơn ngoài thực tế. BiLSTM/PhoBERT chưa chạy, tiếp tục là hướng phát triển. Qwen/Ollama là mô hình có sẵn để diễn đạt thông tin FAQ; không được huấn luyện bằng 50 câu và không thay thế bộ phân loại.

Trang **Thực nghiệm mô hình** hiển thị cấu hình, kết quả, confusion matrix, chỉ số từng nhãn, dự đoán Test và lựa chọn chế độ `auto`, `mlp`, `linearsvc`, `retrieval` để thử từng câu. API `POST /api/experiments/route` không lưu lịch sử, không gọi AI tạo sinh và không đổi mặc định của sinh viên. Giao diện trò chuyện sinh viên tiếp tục dùng lựa chọn tự động.

Đánh giá chọn FAQ được tách riêng trong `data/technical_faq_cases.json` và `reports/faq-evaluation.json`: 20 tình huống kỹ thuật tự biên soạn, 13 tình huống mong đợi có FAQ. MLP/LinearSVC chọn đúng 9/13, đúng FAQ trong số câu đã trả lời là 9/11, đúng hành vi 16/20. Chỉ quy tắc và truy hồi chọn đúng 10/13, đúng FAQ trong số câu đã trả lời là 10/12, đúng hành vi 17/20. Hỏi lại/từ chối câu cần FAQ vẫn tính là chưa chọn được FAQ. Đây là chẩn đoán kỹ thuật, không phải phản hồi sinh viên thực tế hay đánh giá độc lập; không suy ra tỷ lệ nhận biết ngoài miền. Các lỗi chọn FAQ và sai nhãn được giữ trong báo cáo, không che bằng tỷ lệ phân loại.

Chi tiết và hướng trình bày khi bảo vệ: [reports/report-alignment.md](reports/report-alignment.md). `reports/experiments.json` lưu tất cả cấu hình Validation, dự đoán Train/Validation/Test, Accuracy/Macro-F1, chỉ số từng lớp, confusion matrix, số vòng lặp/cảnh báo hội tụ, fingerprint dữ liệu/model và phiên bản thư viện. Pipeline lưu đồng bộ trong `models/mlp.joblib`, `models/linearsvc.joblib`; `intent.joblib` là bản của lựa chọn theo Validation. Tài liệu DOCX/PPTX gốc được giữ nguyên; slide có nhãn/cấu hình đề xuất khác, phần bổ sung giải thích vì sao dùng DOCX làm chuẩn.

## Vận hành trên máy chủ đã cài đặt

```bash
cd /home/phamtung/student-support
systemctl --user status student-support student-ai
systemctl --user restart student-support
journalctl --user -u student-support -n 100
journalctl --user -u student-ai -n 100
curl http://127.0.0.1:8088/api/health
curl http://127.0.0.1:8088/api/ai-status
```

Các dịch vụ systemd user đã enable; `loginctl enable-linger phamtung` cho phép chạy khi chưa đăng nhập. Cổng 8088 được mở cho nguồn IPv4 192.168.1.0/24 trong firewalld. Địa chỉ IP phụ thuộc DHCP của mạng; nên giữ DHCP reservation theo MAC D8-43-AE-90-79-77 khi cấu hình router.

Quên mật khẩu quản trị:

```bash
cd /home/phamtung/student-support
.venv/bin/python scripts/reset_admin.py
```

## Kết nối AI bên ngoài

Mở Quản trị → Kết nối AI → API tương thích OpenAI. Điền HTTPS Base URL có `/v1`, tên mô hình và API key. Khóa được ghi trong `data/ai-settings.json` với quyền 0600 và không trả lại trình duyệt. Để trống trường khóa khi cập nhật sẽ giữ khóa hiện có. Provider cần hỗ trợ `/chat/completions` và JSON response format. Khi dùng provider ngoài, câu hỏi và đoạn nguồn đã chọn được gửi đến provider đó. Có thể quay lại Ollama với model `qwen3:4b` bất kỳ lúc nào.

## Sao lưu và khôi phục

Timer `student-backup.timer` chạy hằng ngày 03:00 giờ Việt Nam, giữ 14 bản gần nhất trong `backups/`. Bản sao lưu có dữ liệu người dùng và khóa cấu hình, chỉ owner được đọc. Tạo bản sao ngay:

```bash
systemctl --user start student-backup.service
systemctl --user list-timers student-backup.timer
```

Khôi phục vào thư mục riêng, kiểm tra trước khi thay thế. Dừng `student-support` trước khi đưa SQLite đã khôi phục vào dùng; giữ lại DB hiện tại và các file WAL/SHM để có thể quay lui. Thử đọc DB trong bản sao lưu bằng `PRAGMA integrity_check`. Chỉ giải nén bản sao do hệ thống này tạo và tin cậy.

## Cài lại từ mã nguồn

Cần Linux x86_64, Python 3.12, Node chỉ phục vụ kiểm thử cú pháp, RAM đủ cho mô hình và khoảng 10 GB đĩa cho thư viện/mô hình. Không cần Node để chạy frontend. Trên máy mới:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/initialize_auth.py
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8088
```

Mã nguồn bàn giao có `data/faqs.json`, dữ liệu nghiên cứu, model đã huấn luyện và báo cáo, nhưng không có cơ sở dữ liệu hội thoại, mật khẩu, API key, Python environment hoặc trọng số LLM. Cài Ollama từ https://ollama.com/download, cấu hình `OLLAMA_HOST=127.0.0.1:11435`, tải `qwen3:4b` và chạy dịch vụ. Các file dịch vụ đang dùng được lưu trong `deploy/` để tham khảo; điều chỉnh đường dẫn khi cài sang tài khoản khác.

Tái chạy thực nghiệm bằng `.venv/bin/python scripts/train.py`, rồi `.venv/bin/python scripts/evaluate_faq.py`. Hai script chỉ đọc dữ liệu công khai/giả lập đã lưu và ghi model/báo cáo trong checkout hiện tại, không dùng DB hội thoại. Không cần chạy `prepare_data.py` để tái thực nghiệm; giữ nguyên dữ liệu đã biên tập.

## Kiểm thử

```bash
timeout 120 .venv/bin/python -m pytest tests -q
timeout 60 .venv/bin/python scripts/check_alignment_inprocess.py
node --check app/static/app.js
node scripts/check_alignment_ui.js
```

Tests dùng DB tạm và pipeline đã lưu, không dùng hội thoại hay tài khoản thật. Môi trường `.venv` liên kết từ dự án chính chỉ được dùng để chạy; không cài/nâng cấp gói trong phiên chỉnh sửa này. Phiên kiểm chứng ban đầu gặp giới hạn sandbox, được giữ trong báo cáo lịch sử. Lần kiểm chứng bổ sung trước khi đưa vào main đạt toàn bộ **54 tests**; kiểm tra cú pháp JavaScript và renderer Thực nghiệm bằng Node (6 nhóm) cũng đạt. Node không kiểm tra bố cục trình duyệt. Xem `reports/report-alignment-verification.json` để phân biệt kết quả lịch sử và lần kiểm tra bổ sung.

Kết quả phiên này có tiền tố `reports/report-alignment-*`; `reports/pytest.txt`, ảnh và browser QA cũ là bằng chứng của lần triển khai trước, không xác nhận thay đổi hiện tại. `scripts/browser_qa.py` là script kiểm tra bản triển khai cũ, phụ thuộc máy chủ/tài khoản thật; không chạy script đó trong worktree này. Chưa kiểm chứng lại bố cục bằng Chromium vì sandbox chặn khởi động.

Triển khai hiện dùng HTTP trong LAN. Chưa cấu hình tên miền và chứng chỉ TLS. Đó là phạm vi vận hành được bàn giao; chưa kiểm thử tải lớn hoặc đánh giá độc lập bởi nhà trường.

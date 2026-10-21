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

Chuẩn hóa Unicode, viết tắt và tiếng Việt không dấu được dùng nhất quán. Truy hồi kết hợp cosine TF-IDF word (1,2) với char_wb (3,5), trọng số 0,55/0,45. Ngưỡng 0,30 khi chưa rõ chủ đề và 0,13 trong chủ đề là quy tắc khởi tạo, chưa được hiệu chỉnh trên tập sinh viên độc lập. Điểm tương đồng không phải xác suất đúng. Câu mơ hồ được hỏi lại; một số câu ngoài phạm vi được từ chối. Có ngữ cảnh cơ bản cho câu hỏi tiếp theo về cùng chủ đề.

AI chỉ nhận câu hỏi và nội dung FAQ được chọn, không nhận khóa quản trị hoặc toàn bộ cơ sở dữ liệu. Đầu ra JSON theo schema được kiểm tra cấu trúc, số liệu, URL và cờ supported trước khi hiển thị. Nguồn dẫn được gắn bởi server. Khi AI lỗi, quá tải hoặc đầu ra không qua kiểm tra, dùng lại câu trả lời đã đối chiếu. Kiểm tra này giảm lỗi nhưng chưa chứng minh mọi diễn đạt sinh ra đều được nguồn hỗ trợ; cần tiếp tục đánh giá bằng câu hỏi thực tế.

## Thực nghiệm

`data/original_50.csv` giữ nguyên 50 câu và phân chia Train 30 / Validation 10 / Test 10 trong DOCX. Mỗi câu gốc là một nhóm, không tăng dữ liệu bằng diễn đạt lại từ Test.

MLP: TF-IDF (1,2), 16 hoặc 32 neuron ẩn, alpha 0,001 hoặc 0,01, L-BFGS, max_iter=1000, seed 42. LinearSVC: C 0,1 hoặc 1,0. Mỗi họ mô hình chọn cấu hình theo Macro-F1 Validation. Chọn mô hình ứng dụng trước khi đánh giá Test; nếu hòa ưu tiên LinearSVC. Vì dùng đúng bộ nhỏ và cách chia từ báo cáo, không thay bằng GridSearchCV 3 fold của slide. BiLSTM/PhoBERT chưa được thực nghiệm.

Kết quả lần triển khai: cả hai mô hình đạt 70% accuracy trên 10 câu Test. Macro-F1 MLP khoảng 0,7133; LinearSVC khoảng 0,6933. Lựa chọn LinearSVC dựa trên Validation hòa điểm 1,0, không dựa trên Test. Kết quả này không chứng minh chất lượng chatbot ngoài thực tế. Hai chủ đề bổ sung được xử lý bởi kho FAQ và truy hồi; bộ phân loại gốc vẫn có 5 nhãn và chỉ đóng vai trò thực nghiệm.

Lưu kết quả, cấu hình, dự đoán từng mẫu và môi trường ở `reports/experiments.json`. Trang Thực nghiệm hiển thị số liệu này trực tiếp.

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

Có thể tái tạo dữ liệu và thực nghiệm bằng `scripts/prepare_data.py` và `scripts/train.py`. `prepare_data.py` chỉ tạo file seed, không ghi đè FAQ đã biên tập trong DB đang chạy.

## Kiểm thử

```bash
.venv/bin/python -m pip install pytest playwright
.venv/bin/python -m pytest tests -q
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_qa.py
```

Unit/integration tests dùng DB tạm riêng. Browser QA cần máy chủ đang chạy và mật khẩu ban đầu chưa bị đổi; có thể cập nhật cách lấy mật khẩu khi chạy lại sau bàn giao. Các báo cáo lần triển khai nằm trong `reports/`. AI smoke test thực tế và browser QA chạy trên máy chủ, không trên máy Windows của người dùng.

Triển khai hiện dùng HTTP trong LAN. Chưa cấu hình tên miền và chứng chỉ TLS. Đó là phạm vi vận hành được bàn giao; chưa kiểm thử tải lớn hoặc đánh giá độc lập bởi nhà trường.

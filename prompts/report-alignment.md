# Hoàn thiện HaUI Assist theo đề tài báo cáo

Bạn đang làm tiếp công việc đã được chủ dự án ủy quyền, trong một Git worktree và nhánh riêng. Hãy thực hiện thay đổi và kiểm chứng đến khi hoàn tất, không chỉ trả về kế hoạch. Không cần chờ chủ dự án khi họ ngắt SSH. Không tự tạo thêm agent hoặc task.

## Mục tiêu và tài liệu gốc

Đề tài: “Nghiên cứu trí tuệ nhân tạo hội thoại và ứng dụng trong xây dựng chatbot hỗ trợ sinh viên”. Đọc tài liệu gốc trong `sources/`, README, hướng dẫn AGENTS.md nếu có, mã nguồn và báo cáo thực nghiệm trước khi sửa.

Tài liệu Word hiện mô tả TC1 (50 câu hỏi minh họa, 5 nhãn, Train/Validation/Test 30/10/10) và TC2 (thiết lập TF-IDF + MLP, LinearSVC đối chứng, BiLSTM là hướng mở rộng). Dự án hiện đã huấn luyện MLP/LinearSVC, nhưng chủ yếu chọn FAQ bằng từ khóa và truy hồi; kết quả bộ phân loại chỉ đính kèm trong `classification`.

Chủ dự án muốn phần nghiên cứu có tác dụng trực tiếp trong chatbot và báo cáo khớp với thực nghiệm. Giữ năm nhãn gốc làm phạm vi nghiên cứu; công tác sinh viên và ký túc xá là chức năng mở rộng.

## Các việc cần hoàn thành

1. Đối chiếu cấu hình với báo cáo. Tách chuẩn hóa phục vụ phân loại (giữ dấu tiếng Việt, Unicode NFC, chữ thường, khoảng trắng, giữ từ phủ định) khỏi chuẩn hóa truy hồi không dấu khi cần. Huấn luyện và suy luận dùng nhất quán cùng bộ biến đổi. Sửa `max_features` trong thực nghiệm thành 500 theo tài liệu. Kiểm tra các cấu hình MLP 16/32 neuron, alpha 0.001/0.01; LinearSVC C 0.1/1.0; seed 42; MLP solver lbfgs, max_iter 1000. TF-IDF chỉ fit trên Train.

2. Giữ nguyên 50 câu và cách chia gốc. Chọn cấu hình trên Validation, ghi lại lựa chọn trước khi tính Test. Ghi rõ đây là tái thực nghiệm trên tập Test đã từng được xem, không phải đánh giá độc lập mới. Không thêm diễn đạt lại của Test vào Train/Validation, không chỉnh cách chia hay nhãn để tăng điểm. Chỉ bổ sung một tập kiểm tra mới nếu có nguồn và quy trình hợp lệ; không gọi các câu tự biên soạn là phản hồi sinh viên thực tế.

3. Đưa bộ phân loại vào bước định hướng tìm FAQ trong năm chủ đề nghiên cứu. Làm rõ và cho phép so sánh MLP và LinearSVC trong chế độ nghiên cứu; kết quả dự đoán phải thực sự ảnh hưởng tìm kiếm khi phù hợp. Quy tắc an toàn, câu nhiều chủ đề, phạm vi mở rộng, truy hồi không đủ chứng cứ và câu hỏi tiếp nối cần được xử lý rõ ràng. Không ép câu hỏi ký túc xá/CTSV vào một trong năm nhãn. Không dùng nhãn dự đoán làm bằng chứng rằng FAQ đúng. Nếu có tham số chọn mô hình hoặc chế độ, tránh thêm chi tiết nghiên cứu vào giao diện sinh viên không cần thiết; đặt ở phần thực nghiệm hoặc quản trị phù hợp.

4. Xử lý hỏi lại/từ chối khi thiếu bằng chứng. Phân biệt điểm tương đồng truy hồi, `predict_proba` của MLP và `decision_function` của LinearSVC. Không gọi các điểm này là xác suất đúng đã hiệu chỉnh; không tự công bố ngưỡng tối ưu hay tỷ lệ nhận biết ngoài phạm vi khi chưa có tập độc lập.

5. Chạy lại huấn luyện, lưu đồng bộ pipeline, cấu hình, tên nhãn, kích thước đặc trưng thực tế, seed, phiên bản dữ liệu/thư viện, dự đoán từng câu, Accuracy, Macro-F1, chỉ số từng nhãn, confusion matrix và thông tin hội tụ. MLP là mô hình nghiên cứu chính và LinearSVC là đối chứng; không mặc định MLP thắng hay làm sai quy tắc chọn mô hình vì mục tiêu trình diễn.

6. Bổ sung kiểm thử có ý nghĩa cho luồng dùng nhãn để truy hồi, chuẩn hóa giữ dấu nhất quán, chuyển chế độ mô hình, phạm vi mở rộng và hỏi lại/fallback. Đánh giá chọn FAQ tách khỏi phân loại ý định trên các tình huống được ghi rõ là kiểm tra kỹ thuật; không thổi phồng thành chất lượng thực tế. Chạy bộ kiểm thử hiện có và kiểm tra giao diện liên quan nếu công cụ cho phép. Dùng `timeout 120 .venv/bin/python -m pytest tests -q` để tránh chờ vô hạn. Nếu socket hoặc trình duyệt bị môi trường chặn, ghi rõ giới hạn và dùng kiểm tra trong tiến trình khi phù hợp; không vượt sandbox hoặc yêu cầu người dùng cấp lại quyền. Script host sẽ chạy lại pytest sau phiên Codex; lỗi do môi trường sandbox có thể chuyển cho bước kiểm tra host, nhưng lỗi logic cần sửa trước khi bàn giao.

7. Cập nhật trang thực nghiệm và README để thể hiện đúng kiến trúc cuối cùng, vai trò MLP/LinearSVC, kết quả thực chạy và giới hạn. Qwen/Ollama là mô hình có sẵn hỗ trợ diễn đạt, không phải mô hình được huấn luyện từ 50 câu và không thay thế vai trò phân loại. BiLSTM/PhoBERT chưa chạy thì vẫn ghi là hướng phát triển.

8. Tạo `reports/report-alignment.md` bằng tiếng Việt: mục tiêu nghiên cứu, liên hệ TC1/TC2 với mã nguồn, phương pháp, sơ đồ luồng bằng Mermaid nếu hữu ích, bảng kết quả thật, ví dụ và lỗi thực tế, đánh giá phân loại so với chọn FAQ, giới hạn, hướng phát triển và gợi ý trình bày khi bảo vệ. Đây là phần bổ sung cho báo cáo; giữ nguyên tài liệu DOCX/PPTX gốc, không cần sinh Word/PDF mới.

## Ranh giới vận hành

- Làm việc trong worktree hiện tại. Không sửa bản gốc ở thư mục dự án chính, dịch vụ systemd/firewall hay dữ liệu đang chạy.
- Không đọc/in/commit khóa API, mật khẩu, file auth, SQLite hội thoại, bản sao lưu hoặc dữ liệu riêng tư. Không chạy script reset mật khẩu hoặc `prepare_data.py` nếu việc đó ghi đè dữ liệu đã biên tập không cần thiết.
- Không tải mô hình lớn, không gọi provider tính phí hoặc cài phần mềm toàn hệ thống. Môi trường `.venv` được liên kết từ dự án gốc: dùng để chạy, không cài/xóa/nâng cấp gói trong đó. Dùng thư viện đang có; nếu thiếu gói hãy báo giới hạn cụ thể.
- Không push, merge, deploy, thay đổi nhánh chính hoặc tạo phiên làm việc ngoài nhiệm vụ này.
- Không tự commit: script bên ngoài sẽ chạy lại tests và tạo commit local nếu các bước hoàn tất thành công.
- Không bỏ qua kiểm thử lỗi để tạo báo cáo thành công. Nếu bị chặn, ghi rõ việc đã làm, việc còn thiếu và lỗi thật.

## Điều kiện bàn giao

Chỉ tạo file `reports/report-alignment-ready.txt` với nội dung `ready` sau khi phần triển khai đã hoàn thành, pipeline/báo cáo khớp nhau và các kiểm tra khả dụng đã được thực hiện. Nếu kiểm thử chỉ bị sandbox chặn, ghi rõ để script host chạy lại. Nếu còn thiếu chức năng, thực nghiệm hoặc còn lỗi logic chưa sửa, không tạo marker này. Marker `ready` chỉ cho phép script host bắt đầu kiểm tra cuối; không có nghĩa toàn bộ nhiệm vụ đã thành công. Script host chỉ tạo `reports/report-alignment-complete.txt` và commit sau khi pytest đạt.

Cuối phiên, tóm tắt bằng tiếng Việt: thay đổi chính, kết quả thực nghiệm, kiểm thử đã chạy, hạn chế còn lại và file cần xem. Script sẽ lưu câu trả lời cuối vào log để chủ dự án đọc sau khi kết nối SSH trở lại.

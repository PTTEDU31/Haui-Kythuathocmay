# Bàn giao HaUI Assist

Ứng dụng đã triển khai và chạy trên máy chủ <IP-máy-chủ>, ngày 21/10/2026.

## Mở ứng dụng

- Trò chuyện: http://<IP-máy-chủ>:8088
- Kho thông tin: http://<IP-máy-chủ>:8088/#knowledge
- Thực nghiệm: http://<IP-máy-chủ>:8088/#experiments
- Quản trị: http://<IP-máy-chủ>:8088/#admin

Máy tính hoặc điện thoại cần ở mạng nội bộ truy cập được máy chủ. Không cần cài mô hình trên máy Windows này.

## Mật khẩu quản trị ứng dụng

Trang quản trị chỉ yêu cầu mật khẩu, không yêu cầu tên đăng nhập:

`HaUI-gZgLNRFvhqPVkEvBzP2i`

Đây là mật khẩu riêng của ứng dụng, khác tài khoản SSH. Bạn có thể đổi tại mục “Đổi mật khẩu quản trị” ở cuối trang quản trị. Sau khi đổi, mật khẩu trong tài liệu này sẽ không còn hiệu lực. File này có thông tin truy cập; lưu riêng với mã nguồn.

## Những phần đã có

- Chatbot tiếng Việt cho 7 nhóm: học phí, học phần, lịch thi, học bổng, điểm, công tác sinh viên, ký túc xá.
- 25 FAQ/hướng dẫn có liên kết nguồn của trường và ngày đối chiếu; hỗ trợ câu hỏi không dấu, hỏi làm rõ và ngữ cảnh cơ bản.
- AI tạo sinh Qwen3 4B chạy trên GPU RTX 3070 Ti của máy chủ qua Ollama. Hiện không cần API key hay chi phí dịch vụ AI bên ngoài.
- Nếu AI lỗi hoặc đầu ra không qua kiểm tra, ứng dụng dùng lại câu trả lời đã đối chiếu. Đây là cơ chế giảm lỗi, không phải bảo đảm mọi diễn đạt AI đều chính xác.
- Kho thông tin có tìm kiếm/lọc chủ đề; đánh giá câu trả lời; lưu, xuất và xóa lịch sử theo trình duyệt.
- Quản trị câu trả lời, duyệt nguồn, đọc tài liệu TXT/PDF/DOCX ở bản nháp, đổi mật khẩu, nhật ký thay đổi.
- Cấu hình API tương thích OpenAI để dùng dịch vụ bạn cung cấp sau. Hiện đang dùng mô hình nội bộ.
- Tự khởi động ứng dụng/AI khi máy chủ khởi động; sao lưu mỗi ngày 03:00 giờ Việt Nam, giữ 14 bản.

## Tài liệu và thư mục máy chủ

Toàn bộ dự án: `/home/phamtung/student-support`

Hai tài liệu gốc đã sao chép nguyên vẹn vào:

- `/home/phamtung/student-support/sources/CHATBOT HO TRO SINH VIEN.pptx`
- `/home/phamtung/student-support/sources/Bao_cao_TC1_TC2_Chatbot (1).docx`

Dữ liệu: `data/`; model học máy: `models/`; báo cáo kiểm thử: `reports/`; bản sao lưu: `backups/`.

Mã nguồn bàn giao trong `HaUI_Assist_source.zip` gồm code, tài liệu gốc, dữ liệu nguồn, model MLP/SVC và báo cáo. Không kèm mật khẩu, API key, hội thoại người dùng, môi trường Python hay trọng số LLM. README trong ZIP có hướng dẫn cài lại, khôi phục và vận hành.

## Kết nối dịch vụ AI bạn cung cấp sau

Vào Quản trị → Kết nối AI. Chọn “API tương thích OpenAI”, nhập HTTPS Base URL (thường kết thúc bằng `/v1`), tên model và API key, rồi lưu. Provider cần hỗ trợ chat completions và JSON response format. Khóa chỉ lưu ở máy chủ, không gửi lại trình duyệt. Khi bật dịch vụ ngoài, câu hỏi và đoạn thông tin được chọn sẽ được gửi đến provider đó. Để quay lại nội bộ, chọn Ollama, model `qwen3:4b`.

## Kiểm chứng đã thực hiện

- 37 unit/integration tests đạt; DB kiểm thử tách khỏi dữ liệu đang chạy.
- 10 bước kiểm thử trình duyệt đạt, gồm desktop 1440px, mobile 390px, chat, nguồn, phản hồi, bộ lọc, thực nghiệm, đăng nhập/đăng xuất quản trị và cấu hình AI; không ghi nhận lỗi JavaScript.
- 8 URL nguồn chính thức phản hồi HTTP 200 khi kiểm tra.
- 24 yêu cầu health đồng thời tối đa 8 yêu cầu đều thành công; đây là smoke test, chưa phải benchmark tải lớn.
- Tạo bản sao lưu và đọc DB phục hồi: `PRAGMA integrity_check` đạt, đủ 25 FAQ.
- Kiểm tra truy cập ứng dụng qua IP LAN từ máy Windows thành công.
- AI thực tế tạo câu trả lời có nguồn thành công; các câu thử khi model đã nạp mất khoảng 0,6–0,8 giây. Lần đầu nạp model có thể lâu hơn.

## Kết quả nghiên cứu và giới hạn

Giữ nguyên 50 câu minh họa trong báo cáo: Train 30, Validation 10, Test 10. MLP và LinearSVC đều đạt 70% accuracy trên Test. Macro-F1 MLP 0,7133; LinearSVC 0,6933. Chọn LinearSVC từ kết quả Validation hòa điểm trước khi xem Test. Không sửa Test để tăng điểm. Trang Thực nghiệm trình bày ma trận nhầm lẫn và cấu hình.

Dữ liệu nghiên cứu nhỏ và do tác giả biên soạn; chưa đánh giá trên tập sinh viên thực tế độc lập. Chưa thể lấy số liệu này làm bằng chứng chất lượng triển khai diện rộng. Mô hình phân loại có 5 nhãn theo báo cáo; 2 chủ đề mở rộng được ứng dụng xử lý qua truy hồi FAQ.

Ứng dụng hỗ trợ thông tin công khai, chưa kết nối hệ thống cá nhân để lấy điểm, công nợ, lịch thi hay phòng trống. Một số nguồn chỉ đủ để hướng dẫn tra cứu, chưa đủ để đưa số tiền hoặc hạn cụ thể. Người quản trị cần bổ sung và xác nhận quy định hiện hành theo từng chương trình. Ngày ngừng dùng FAQ là hạn nội bộ để rà soát lại, không thay thế thời hạn pháp lý của nguồn.

Ứng dụng hiện dùng HTTP trong mạng LAN, chưa có tên miền/chứng chỉ TLS. IP có thể thay đổi nếu DHCP đổi; có thể cố định trên router.

## Lệnh vận hành nhanh qua SSH

```bash
cd /home/phamtung/student-support
systemctl --user status student-support student-ai
systemctl --user restart student-support
journalctl --user -u student-support -n 100
systemctl --user start student-backup.service
systemctl --user list-timers student-backup.timer
.venv/bin/python scripts/reset_admin.py
```

`reset_admin.py` chỉ cần khi quên mật khẩu quản trị; công cụ sẽ hỏi mật khẩu mới và thu hồi các phiên quản trị cũ.

# Điều tra DNS ttech.io.vn — 22/10/2026

Kiểm tra lúc khoảng 10:46–10:50, giờ Việt Nam. Bằng chứng thô và lệnh truy vấn: [JSON](ttech-dns-investigation-2026-10-22.json).

## Kết luận

Lỗi truy cập được tái hiện tại bước xác thực DNSSEC của vùng cha `io.vn`. Tunnel tên miền và ứng dụng vẫn phục vụ được HTTPS khi phân giải đúng IP. Không thay đổi DNS, cấu hình hoặc khởi động lại dịch vụ trong cuộc điều tra này.

## Bằng chứng đã xác minh

- Cloudflare `1.1.1.1`, Google `8.8.8.8` và Quad9 `9.9.9.9` trả `SERVFAIL` cho `ttech.io.vn A`. Thông báo mở rộng gồm `NSEC Missing`, `Invalid denial of existence of ttech.io.vn/ds` và thiếu RRSIG của SOA `io.vn`.
- Cùng truy vấn với `+cd` (bỏ kiểm tra DNSSEC chỉ trong phép thử này) trả IP `104.21.46.113` và `172.67.168.118`.
- Cả `celine.ns.cloudflare.com` và `dakota.ns.cloudflare.com` trả A record đúng. Ủy quyền từ vùng cha cũng trỏ đúng hai nameserver này.
- Vùng `io.vn` có DS được xác thực từ `.vn`, key tag `56381`. Vì vậy các câu trả lời của `io.vn` cần chuỗi xác thực hợp lệ.
- Khi hỏi trực tiếp `a.dns-servers.vn` về `ttech.io.vn DS`, phản hồi chỉ chứa SOA và chữ ký SOA, thiếu bằng chứng phủ định NSEC/NSEC3. TCP cũng tái hiện nên đây không đơn thuần là mất gói UDP.
- Máy chủ `a` trả chữ ký cho DNSKEY/SOA `io.vn`; `b` trả DNSKEY/SOA không có chữ ký dù truy vấn bật DNSSEC. Các máy chủ `b`–`h` được kiểm tra cũng không trả chữ ký SOA. Máy chủ `d` trả serial `2023746079`, trong khi các máy chủ còn lại trả `2023746087`. Có sự không đồng nhất ở các máy chủ phục vụ vùng cha.
- Tunnel có **4 ready connections**. Dịch vụ tunnel hoạt động liên tục từ **00:35:45**; mtime cấu hình vẫn là thời điểm đó.
- Cả hai IP Cloudflare, khi kiểm tra với `curl --resolve` và giữ hostname/SNI `ttech.io.vn`, phục vụ `/architecture/live` với **HTTP 200, TLS verify = 0**. Không dùng `-k`.
- DNS của máy chủ đang đặt `DNSSEC=no/unsupported`. Do đó HTTP từ máy chủ thành công chưa chứng minh thiết bị dùng DNS có xác thực sẽ truy cập được.

## Vì sao trước đó vẫn truy cập được?

Cấu hình xác thực và cache DNS khác nhau giữa các thiết bị/resolver có thể làm một bên còn nhận được IP trong khi bên khác từ chối. Hồ sơ triển khai lúc 00:38 ghi nhận kiểm tra DNS công khai đạt; lỗi công khai đã được tái hiện lúc khoảng 10:23. Chưa có log thay đổi của đơn vị quản lý DNS hoặc cấu hình resolver trên điện thoại nên chưa xác định được thời điểm bắt đầu và thay đổi kích hoạt chính xác. Không thể kết luận mọi lần truy cập trước đó đều dùng cache.

## Hướng xử lý

Nhà cung cấp tên miền cần chuyển bằng chứng cho đơn vị vận hành DNS `io.vn`/VNNIC để kiểm tra chữ ký, bằng chứng phủ định DS và việc đồng bộ các nameserver. Sau khi sửa, kiểm tra lại bằng DNS có xác thực. Việc đổi riêng DNS điện thoại sang 1.1.1.1 hoặc 8.8.8.8 hiện chưa giải quyết được vì cả hai đều trả lỗi.

Giữ tunnel dự phòng đang phục vụ buổi trình diễn. Chưa có bằng chứng cho thấy cần tạo lại named tunnel hoặc đổi A/CNAME trong Cloudflare.

## Nội dung có thể gửi bộ phận hỗ trợ

> Nhờ kiểm tra DNSSEC vùng cha io.vn cho tên miền ttech.io.vn. Tại khoảng 10:46–10:50 ngày 22/10/2026 (UTC+7), 1.1.1.1, 8.8.8.8 và 9.9.9.9 trả SERVFAIL, EDE NSEC Missing / Invalid denial of existence of ttech.io.vn/ds. Truy vấn trực tiếp nameserver vùng cha với DNSSEC bật không nhận NSEC/NSEC3 chứng minh không có DS của ttech.io.vn; có máy chủ thiếu RRSIG của io.vn SOA/DNSKEY. SOA serial còn khác nhau giữa máy chủ d và các máy chủ khác. Hai nameserver Cloudflare vẫn trả đúng A record và HTTPS hoạt động khi ghim IP với kiểm tra chứng chỉ đầy đủ. Nhờ kiểm tra việc ký DNSSEC và đồng bộ các máy chủ phục vụ io.vn. Lệnh và phản hồi DNS thô được đính kèm trong báo cáo JSON.

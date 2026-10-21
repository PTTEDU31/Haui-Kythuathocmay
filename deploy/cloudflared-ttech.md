# Truy cập HaUI Assist qua ttech.io.vn

Cloudflare Tunnel chuyển HTTPS công khai về `http://127.0.0.1:8088`.
Không cần mở cổng router. Tên miền dùng DNS Cloudflare; cần đăng nhập
tài khoản có quyền quản lý `ttech.io.vn` trước khi tạo tunnel và bản ghi DNS.

Binary `cloudflared` đặt trong `/home/phamtung/.local/bin/`. Phiên bản đã
cài là 2026.10.3, SHA-256 đã đối chiếu với metadata bản phát hành GitHub.

## Bản triển khai hiện tại

- URL: https://ttech.io.vn
- Tunnel: `ttech-student-support` (`9ee89f6e-0774-46c5-b3a5-cd630755ddf6`).
- Dịch vụ `cloudflared-ttech.service` đã enable; user linger đã bật.
- Cấu hình thực tế: `~/.cloudflared/ttech.yml`, quyền 0600.
- Kiểm tra HTTPS trang chủ, health, hai chế độ phân loại, cookie Secure,
  quản trị yêu cầu đăng nhập và trò chuyện thật qua Qwen đã đạt.
- DNS authoritative, Cloudflare 1.1.1.1 và Google 8.8.8.8 đã trả bản ghi mới.
  DNS của router LAN còn cache kết quả cũ tại thời điểm triển khai. Kiểm tra
  HTTPS đã dùng IP edge được DNS công khai trả về qua `curl --resolve`;
  vẫn giữ kiểm tra chứng chỉ TLS, không dùng `-k`.

Chi tiết kiểm tra có trong `reports/public-deployment.json`. Không chạy lại
bước tạo tunnel cho bản triển khai hiện tại; các bước dưới dành cho cài mới.

## Thiết lập

1. Chạy `~/.local/bin/cloudflared tunnel login`, mở liên kết được in và
   chọn `ttech.io.vn`. Không gửi mật khẩu hoặc API key vào hội thoại.
2. Tạo named tunnel bằng `~/.local/bin/cloudflared tunnel create ttech-student-support`.
3. Sao chép `deploy/cloudflared-ttech.yml.example` thành
   `~/.cloudflared/ttech.yml`, thay `TUNNEL_UUID` bằng UUID vừa tạo.
   Giữ quyền thư mục `.cloudflared` là 0700 và các file xác thực là 0600.
4. Kiểm tra ingress:
   `~/.local/bin/cloudflared tunnel --config ~/.cloudflared/ttech.yml ingress validate`.
5. Gắn DNS:
   `~/.local/bin/cloudflared tunnel route dns TUNNEL_UUID ttech.io.vn`.
   Nếu đã có bản ghi web, kiểm tra trước khi thay thế; không tự dùng overwrite.
6. Sao chép `deploy/cloudflared-ttech.service` vào
   `~/.config/systemd/user/`, rồi chạy `systemctl --user daemon-reload` và
   `systemctl --user enable --now cloudflared-ttech.service`.
7. Kiểm tra `https://ttech.io.vn`, `/api/health`, thử hỏi ở trang
   Thực nghiệm và kiểm tra nguồn trả lời. Kiểm tra trạng thái connector:
   `curl --fail http://127.0.0.1:20245/ready`.

Không đưa cert.pem, credentials JSON hoặc token vào Git. Các file thực tế
nằm ngoài repository. Dịch vụ tunnel chỉ phục vụ hostname trong cấu hình;
hostname khác trả 404. Giữ nguyên Host header để kiểm tra Origin của ứng dụng
hoạt động đúng. Uvicorn tin proxy localhost theo mặc định; cookie phiên tự
bật Secure khi request có scheme HTTPS. Truy cập HTTP trong LAN vẫn dùng được.

## Vận hành

```bash
systemctl --user status cloudflared-ttech student-support
systemctl --user restart cloudflared-ttech
journalctl --user -u cloudflared-ttech -n 50
```

Dừng tunnel tên miền: `systemctl --user disable --now cloudflared-ttech`.
Dịch vụ ứng dụng trong LAN vẫn chạy. Máy chủ cần đang bật và có Internet.

Các file cấu hình mẫu không chứng minh tunnel đã hoạt động. Chỉ công bố
đường dẫn truy cập sau khi DNS, connector và kiểm tra HTTPS thực tế thành công.

# Website Thiên Bảo Logistics – bản nâng cấp

## Chạy bằng VS Code

1. Mở đúng thư mục này trong VS Code.
2. Cài extension **Python** của Microsoft.
3. Mở Terminal trong VS Code và chạy một lần:
   `python -m pip install -r requirements.txt`
4. Nhấn **F5**, chọn **Chạy Thiên Bảo Logistics**.
5. Website: `http://127.0.0.1:5000`
6. Quản trị: `http://127.0.0.1:5000/admin/login`

Tài khoản ban đầu: `admin` / `ThienBao@2026`.
Sau khi đăng nhập, vào **Đổi mật khẩu** để đổi ngay.

## Chức năng mới

- Trang chủ mới, hiệu ứng cuộn, Font Awesome, responsive.
- Trang Giới thiệu chỉnh sửa được trong Admin.
- Cấu hình logo, favicon, hotline, email, địa chỉ, mạng xã hội, Google Maps và tracking.
- Dịch vụ có banner, ảnh đại diện, icon, FAQ và SEO.
- Bài viết có CKEditor, danh mục, ảnh và SEO.
- Khách hàng có tìm kiếm, lọc, trạng thái, ghi chú và xuất CSV.
- CSRF cơ bản, mật khẩu mã hóa, giới hạn upload 8 MB.
- Sitemap, robots.txt, canonical và Open Graph.

## Lưu ý

- CKEditor và Font Awesome được tải qua Internet.
- Dữ liệu nằm tại `instance/thienbao.db`.
- Ảnh upload nằm trong `static/uploads`.
- Sao lưu hai vị trí trên trước khi cập nhật hoặc chuyển máy.
- Trước khi đưa lên Internet, đổi `SECRET_KEY`, mật khẩu Admin và tắt `FLASK_DEBUG`.

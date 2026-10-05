# ScanSocial

Ứng dụng CRM local-first bằng React + Tauri 2 và FastAPI/SQLite, dành cho quản lý lead từ Facebook, Threads và chăm sóc khách hàng qua Zalo.

## Chức năng đã triển khai

- Giao diện tiếng Việt: tổng quan, khám phá lead, khách hàng 360, cơ hội bán hàng, lịch chăm sóc, trợ lý Zalo, chăm sóc OA, blacklist và sao lưu.
- Nhập bài viết/bình luận JSON; lọc tuổi bài, chống trùng qua nhiều lần nhập, blacklist cứng/mềm, chấm điểm có giải thích, trích xuất SĐT với nguồn dữ liệu.
- Tạo liên hệ thủ công hoặc từ bài/bình luận; chuyển thành khách hàng, nhu cầu, cơ hội, ghi chú, nhãn, dòng thời gian và hợp nhất hồ sơ.
- Lịch chăm sóc, cảnh báo đến hạn và đề xuất follow-up sau báo giá 48 giờ.
- Tìm kiếm FTS5 tự đồng bộ bài viết, hồ sơ, SĐT, URL, ghi chú và nhãn.
- Sao lưu SQLite online, khôi phục có bản sao an toàn trước khi ghi, xuất CSV.
- Zalo cá nhân: liên kết hội thoại, ghi nhận tin nhắn, soạn nháp và sao chép để gửi thủ công.
- Zalo OA: đợt chăm sóc có bản xem trước, consent, hạn mức, giờ yên lặng Việt Nam và duyệt từng tin. Không giả báo gửi thành công.
- Desktop tự khởi động/dừng engine sidecar, token ngẫu nhiên mỗi phiên, dữ liệu lưu tại thư mục ứng dụng của người dùng.

## Chạy phát triển

Yêu cầu Python >= 3.12 và Node >= 22.12.

```bash
python -m pip install -r apps/engine/requirements.txt
npm ci --prefix apps/desktop
python scripts/dev.py
```

Trong terminal khác:

```bash
cd apps/desktop
npm run dev
```

Mở `http://127.0.0.1:5173`, dùng địa chỉ engine và token được script phát triển in ra. CRM mặc định của script này nằm tại `data/`, bị loại khỏi Git. Engine production không in token ra log.

## Kiểm chứng

```bash
python -m pytest apps/engine/tests -q
cd apps/desktop
npm run build
npx playwright install chromium
npm run test:e2e
```

Test backend và trình duyệt dùng dữ liệu tạm độc lập, không sửa CRM thật. CI không bỏ qua lỗi typecheck. Test benchmark chỉ kiểm tra thuật toán; không đại diện cho chứng nhận chất lượng production hay quyền sử dụng API.

## Nhập dữ liệu

Chọn **Khám phá lead → Nhập JSON**. Có thể bấm **Điền ví dụ** để xem định dạng; dữ liệu ví dụ chỉ được ghi khi bạn bấm nhập. Định dạng:

```json
{
  "platform": "FACEBOOK",
  "max_age_hours": 168,
  "posts": [{
    "platform": "FACEBOOK",
    "external_id": "your-post-id",
    "url": "https://www.facebook.com/posts/your-post-id",
    "author_name": "Tên liên hệ",
    "author_id": "optional-author-id",
    "content": "Nội dung bạn có quyền sử dụng",
    "posted_at": "2026-10-05T08:00:00+07:00",
    "comments": []
  }]
}
```

SĐT trích xuất chưa được xác minh chủ sở hữu; trùng tên hoặc SĐT chưa xác minh không đủ điều kiện tự hợp nhất. Bài đã lưu hoặc liên kết CRM được bảo vệ khỏi retention.

## Kết nối thật và giới hạn

- **Facebook:** chỉ đọc Page feed được cấp quyền. Cấu hình `SCANSOCIAL_FACEBOOK_PAGE_IDS='["PAGE_ID"]'` và token Page trong Cài đặt hoặc `SCANSOCIAL_FACEBOOK_ACCESS_TOKEN`. Không cung cấp tìm kiếm tùy ý toàn Facebook/Groups.
- **Threads:** official keyword search; cần token và quyền API phù hợp. Đặt token trong Cài đặt hoặc `SCANSOCIAL_THREADS_ACCESS_TOKEN`.
- **Zalo OA:** cần token chính thức `SCANSOCIAL_ZALO_ACCESS_TOKEN`, UID OA đúng, sự đồng ý và tương tác gần đây. Chăm sóc sử dụng tin tư vấn; không phải công cụ phát quảng cáo hàng loạt.
- **Zalo cá nhân:** thao tác gửi và nhập lịch sử là thủ công. Không truy cập tự động tài khoản cá nhân.
- **AI:** chấm điểm/nhu cầu dùng heuristic offline. `SCANSOCIAL_DEFAULT_AI_PROVIDER=ollama` bật soạn phản hồi qua Ollama local, có fallback khi dịch vụ không sẵn sàng.
- Quyền/token và gửi thật trên các nền tảng phải được kiểm chứng với tài khoản được cấp quyền; test dự án không gửi tin cho khách thật.

Secrets lưu trong OS keyring. Khi không có keyring, dùng biến môi trường; không tự lưu khóa mã hóa cạnh dữ liệu. Engine chỉ bind `127.0.0.1`, REST và WebSocket đều xác thực session token, CORS giới hạn origin local.

## Desktop và bộ cài

Cần Rust stable, WebView2 và MSVC Build Tools trên Windows; xem hướng dẫn Tauri chính thức: https://v2.tauri.app/start/prerequisites/.

```bash
python -m pip install pyinstaller
python scripts/build-sidecar.py
cd apps/desktop
npm run tauri dev
# or
npm run tauri build
```

Workflow **Desktop Packages** build Windows/Ubuntu và lưu bộ cài dưới Actions artifacts mỗi lần push. Workflow release chỉ chạy khi push tag `v*`. Xem `docs/release/` và `docs/testing/TEST_PLAN.md`.

MIT License.

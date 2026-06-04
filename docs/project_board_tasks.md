# Danh Sách Thẻ Task Theo Mẫu Form Công Việc
### Dự án: Team AI / AI Gen Tin Tức - Slide

Tài liệu này chứa chi tiết 12 thẻ task được thiết kế để copy-paste chính xác vào từng trường của form tạo công việc.

---

## 🟢 NHÓM 1: TRẠNG THÁI "HOÀN THÀNH"
*Các công việc đã thực hiện thành công, kiểm thử và đồng bộ mã nguồn.*

### Task 1: Tích hợp Middleware Semaphore giới hạn tải đồng thời
* **Tiêu đề:** `[Backend] Tích hợp Middleware Semaphore giới hạn tải đồng thời`
* **Mô tả:** 
Triển khai bộ điều phối tài nguyên bằng Semaphore của Asyncio để giới hạn mức độ xử lý song song các tác vụ nặng, ngăn ngừa tình trạng VPS bị quá tải CPU/RAM hoặc lỗi Out-Of-Memory (OOM):
- Giới hạn tác vụ Playwright render: tối đa 30.
- Giới hạn tác vụ LLM call: tối đa 20.
- Giới hạn tác vụ TTS audio: tối đa 20.
- Tạo background clean loop định kỳ dọn dẹp các thư mục session rác (`my-video/sessions/`) quá hạn 30 phút trên ổ đĩa.
- Tích hợp endpoint `/status` cho phép Client giám sát thời gian thực số render đang xếp hàng (queue).
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 8 hours
* **Realtime:** 8 hours
* **Start date:** 2026-06-01
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Tạo `concurrency.py` định nghĩa các đối tượng Asyncio Semaphore.
- [x] Sửa đổi `main.py` để gắn static files endpoint cho `/sessions` và khởi động tác vụ chạy nền dọn dẹp.
- [x] Gắn semaphore giới hạn vào router `build.py` và `compositions.py`.

---

### Task 2: Cô lập Lịch sử & Database theo tài khoản người dùng
* **Tiêu đề:** `[Backend] Phân tách lịch sử render và database db.json theo User Account`
* **Mô tả:**
Phân tách dữ liệu lịch sử và video output của từng người dùng để bảo mật thông tin và tránh xung đột file ghi đè chéo:
- Tự động tạo thư mục lịch sử riêng cho từng user dựa trên email: `my-video/history/users/{user_email}/`.
- Lưu trữ file cơ sở dữ liệu `db.json` riêng lẻ cho từng user.
- Triển khai API `/upload-render` và `/save-error-log` để quản lý tải lên video render phía client cùng log lỗi.
- Hỗ trợ API `DELETE` lịch sử độc lập, tự động xóa sạch file video, html và cập nhật DB riêng tư.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 12 hours
* **Realtime:** 11 hours
* **Start date:** 2026-06-01
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Refactor module router `build.py` để đọc/ghi lịch sử theo email người dùng gửi từ header `x-user-email`.
- [x] Xây dựng cơ chế dọn dẹp file vật lý khi gọi API xóa phần tử lịch sử.
- [x] Viết script kiểm thử mô phỏng đa tài khoản đăng nhập đồng thời.

---

### Task 3: Giao diện chọn chế độ dựng video Hybrid Dual-Mode
* **Tiêu đề:** `[Frontend] Tích hợp bộ chọn chế độ Render: Client vs Server`
* **Mô tả:**
Thiết kế và lập trình giao diện chuyển đổi linh hoạt chế độ render để người dùng tự quyết định nơi xử lý video:
- Tích hợp thanh trượt chọn chế độ cao cấp (glassmorphism UI) tại màn hình VideoBuilder.
- Gọi bộ kiểm tra tính năng WebCodecs của trình duyệt client (hỗ trợ H.264 profile & AAC audio codec).
- Tự động fallback về Server Render nếu trình duyệt client không đủ năng lực xử lý (ví dụ: Safari trên iOS).
- Tích hợp giao diện log tiến độ render client thời gian thực.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 6 hours
* **Realtime:** 6 hours
* **Start date:** 2026-06-02
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Tạo file kiểm tra năng lực trình duyệt `browserCapabilities.ts`.
- [x] Sửa giao diện `VideoBuilder.tsx` hiển thị thanh trượt Dual-Mode.
- [x] Kết nối tiến độ từ hook `useClientRender` lên UI log list.

---

### Task 4: Pipeline mã hóa WebCodecs Client-side & Audio Chunking
* **Tiêu đề:** `[Frontend] Xây dựng Pipeline mã hóa video Client-Side & Audio Chunking`
* **Mô tả:**
Xây dựng module render video hoàn chỉnh chạy trực tiếp ở luồng client:
- Nạp composition HTML vào hidden iframe.
- Đọc file âm thanh WAV từ backend và decode sang Float32.
- Đồng bộ và chụp frame tuần tự qua canvas rồi đưa vào WebCodecs `VideoEncoder`.
- **Sửa lỗi Audio:** Cắt nhỏ dữ liệu Float32Array của `mergedAudioBuffer` thành các chunk 1024 samples để tránh tràn driver AAC và gây crash trình duyệt (`EncodingError`).
- Sử dụng `mp4-muxer` đóng gói thành file `.mp4`.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 16 hours
* **Realtime:** 15 hours
* **Start date:** 2026-06-02
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Viết component hook `useClientRender` điều khiển WebCodecs và `mp4-muxer`.
- [x] Xử lý thuật toán chia nhỏ buffer âm thanh (Audio Chunking).
- [x] Ghép nối tự động upload video đã render lên Server thông qua API.

---

### Task 5: Thiết kế và tích hợp 15 Layout Templates mới
* **Tiêu đề:** `[Design] Thiết kế 15 Layout Templates mới (t16 - t30) & Phá vỡ khuôn mẫu 50/50`
* **Mô tả:**
Thiết kế và viết code HTML/CSS cho 15 layout mẫu slide mới để tăng tính thẩm mỹ và đa dạng hóa hiển thị tin tức:
- Phá bỏ thiết kế chia đôi 50/50 màn hình thông thường.
- Thiết kế layout bất đối xứng (T19 - 70/30), layout lưới side-by-side toàn màn hình (T17, T26).
- Thiết kế layout dòng thời gian ngang (T22), Kanban Scrum Board (T28) với 3 cột nhiệm vụ.
- Đăng ký danh mục layout hoàn chỉnh vào `catalog.json` hỗ trợ đa ngôn ngữ và từ khóa gợi ý tiếng Việt.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 16 hours
* **Realtime:** 16 hours
* **Start date:** 2026-06-02
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Viết file template HTML từ `t16.html` đến `t30.html` trong thư mục `templates`.
- [x] Cập nhật metadata trong `catalog.json` và cấu hình phân loại template.
- [x] Nâng cấp router `/templates/gallery` để hỗ trợ hiển thị toàn bộ 30 templates trên giao diện gallery.

---

### Task 6: Mở rộng 15 Theme màu nghệ thuật phong cách mới
* **Tiêu đề:** `[Design] Mở rộng thêm 15 Theme màu nghệ thuật cho Slide`
* **Mô tả:**
Bổ sung các phối màu và font chữ nghệ thuật để đáp ứng đa dạng nhiều chủ đề tin tức khác nhau:
- Các theme mới gồm: Sunset Glow, Iceberg Tech, Retro Arcade, Cyberpunk Glitch, Bento Minimal, Forest Eco, Royal Velvet, v.v.
- Khai báo kiểu dữ liệu TypeScript union `ThemeId` trong `scene.ts`.
- Cập nhật hiển thị màu swatch trên giao diện lựa chọn của Client để người dùng chọn nhanh.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 6 hours
* **Realtime:** 6 hours
* **Start date:** 2026-06-03
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Thêm cấu hình style CSS variables cho 15 theme mới trong backend router `compositions.py`.
- [x] Định nghĩa danh sách swatch màu và theme ID trong frontend `types/scene.ts`.

---

### Task 7: Sửa lỗi Treo màn hình "Đang chờ GSAP timeline..." khi tải song song
* **Tiêu đề:** `[Bugfix] Khắc phục lỗi Treo màn hình "Đang chờ GSAP timeline..."`
* **Mô tả:**
Sửa lỗi bất đồng bộ nghiêm trọng khiến trình duyệt bị kẹt cứng không thể bắt đầu tiến trình render client:
- Trì hoãn việc append iframe vào DOM cho đến khi đã cấu hình xong `src` và các sự kiện `onload`/`onerror` nhằm bỏ qua tài liệu mặc định `about:blank`.
- Truy cập động `contentWindow` của iframe ở mỗi vòng lặp tránh giữ tham chiếu cũ đã bị giải phóng khi chuyển trang.
- Bao bọc đối tượng GSAP Timeline trong plain object `{ timeline }` để tránh cơ chế tự động chạy `.then()` (thenable) gây treo vô hạn của Javascript engine.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 8 hours
* **Realtime:** 8 hours
* **Start date:** 2026-06-03
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Sửa lại luồng load hứa hẹn (loadPromises) trong `ClientRenderer.tsx`.
- [x] Đóng gói GSAP timeline trả về trong plain wrapper `{ timeline }`.
- [x] Tối ưu hóa số lượng workers chạy song song từ 6 xuống 2 để giảm nghẽn main thread.

---

### Task 8: Tối ưu hóa tốc độ chụp frame Client-Side
* **Tiêu đề:** `[Perf] Tăng tốc độ chụp Canvas Frame bằng Base64 Inlining & Direct ImageBitmap`
* **Mô tả:**
Tối ưu hóa sâu kiến trúc render client để đẩy tốc độ chụp từ ~1 frame/1.5s lên ~20 frames/s:
- Triển khai hàm helper `inlineHtmlAssets` sử dụng `DOMParser` để fetch và convert toàn bộ hình ảnh (trong thẻ `<img>` và background-image CSS) thành chuỗi Base64 Data URL trước khi render.
- Loại bỏ canvas trung gian `workerCanvas` cùng hàm `drawImage`, gọi trực tiếp `createImageBitmap(capturedCanvas)` để gửi buffer hình ảnh trực tiếp sang VideoEncoder.
- Tắt cacheBust của `html-to-image` giúp tối ưu hóa luồng đọc bộ nhớ đệm của trình duyệt.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 8 hours
* **Realtime:** 8 hours
* **Start date:** 2026-06-03
* **End date:** 2026-06-04
* **Deadline:** 2026-06-04
* **Trạng thái:** Hoàn thành
* **SubTasks:**
- [x] Tích hợp helper `inlineHtmlAssets` và `blobToDataURL` vào `ClientRenderer.tsx`.
- [x] Chạy kiểm thử đo lường hiệu năng thực tế FPS trên console log.

---

## 🟡 NHÓM 2: TRẠNG THÁI "ĐANG TEST"
*Các công việc đang chạy thử nghiệm kiểm soát chất lượng.*

### Task 9: Kiểm thử chất lượng và tốc độ Render Client-side
* **Tiêu đề:** `[QA] Kiểm thử hiệu năng và FPS chế độ Client Render trên các cấu hình máy`
* **Mô tả:**
Thực hiện chạy thử nghiệm quy trình tạo video thực tế ở môi trường local:
- Đo lường và ghi nhận tốc độ xử lý FPS trung bình (mục tiêu từ 15-30 FPS).
- Xác minh xem tệp video tải về có hiển thị đầy đủ hình ảnh, hiệu ứng chuyển động GSAP và âm thanh đồng bộ khớp hình hay không.
- Test trên các trình duyệt phổ biến: Chrome, Edge, Firefox, Brave để đảm bảo tính tương thích của WebCodecs.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 4 hours
* **Realtime:** 2 hours
* **Start date:** 2026-06-03
* **End date:** 
* **Deadline:** 2026-06-04
* **Trạng thái:** Đang test
* **SubTasks:**
- [ ] Chạy thử render 5 video có độ dài khác nhau.
- [ ] Kiểm tra dung lượng và codec của file MP4 đầu ra.

---

### Task 10: Xác minh phân quyền Lịch sử người dùng và Xóa Video
* **Tiêu đề:** `[QA] Xác minh lưu trữ phân tách thư mục lịch sử và xóa Video`
* **Mô tả:**
Kiểm tra tính độc lập dữ liệu giữa các tài khoản và thao tác dọn dẹp tệp tin:
- Đăng nhập tài khoản Test A và Test B để tạo lịch sử video.
- Xác nhận danh sách video lịch sử không bị hiển thị chéo sang tài khoản đối phương.
- Thực hiện xóa video của tài khoản Test A, kiểm tra xem các tệp tin trong thư mục vật lý `my-video/history/users/TestA/...` có bị xóa hoàn toàn hay không, và đảm bảo dữ liệu Test B không bị ảnh hưởng.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 4 hours
* **Realtime:** 2 hours
* **Start date:** 2026-06-03
* **End date:** 
* **Deadline:** 2026-06-04
* **Trạng thái:** Đang test
* **SubTasks:**
- [ ] Chạy mô phỏng tạo và xóa video đồng thời của 2 tài khoản qua script `test_user_history.py`.
- [ ] Xác minh thư mục vật lý tương ứng trên máy chủ local sau khi xóa.

---

## 🔵 NHÓM 3: TRẠNG THÁI "ĐANG THỰC HIỆN"
*Các công việc tài liệu và chuẩn bị bàn giao.*

### Task 11: Hoàn thiện tài liệu Kỹ thuật Tối ưu hóa
* **Tiêu đề:** `[Dev] Hoàn thiện tài liệu tối ưu hóa Client-side và hướng dẫn vận hành`
* **Mô tả:**
Biên soạn và hoàn thiện tài liệu hướng dẫn kỹ thuật phục vụ lưu trữ dự án:
- Viết chi tiết kiến trúc Hybrid Render mới trong `docs/11-client-side-rendering-optimization.md`.
- Ghi lại các tham số cấu hình Semaphore của Backend cùng cách điều chỉnh để phục vụ nâng cấp VPS sau này.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 4 hours
* **Realtime:** 3 hours
* **Start date:** 2026-06-04
* **End date:** 
* **Deadline:** 2026-06-04
* **Trạng thái:** Đang thực hiện
* **SubTasks:**
- [x] Viết tài liệu `11-client-side-rendering-optimization.md`.
- [ ] Đánh giá lại tài liệu và lưu trữ trong nhánh code `home`.

---

## 🔴 NHÓM 4: TRẠNG THÁI "CHỜ XỬ LÝ"
*Kế hoạch chuẩn bị triển khai lên Production.*

### Task 12: Đóng gói mã nguồn và chuẩn bị deploy lên VPS Production
* **Tiêu đề:** `[Ops] Đóng gói mã nguồn ver_2.6 và chuẩn bị deploy lên máy chủ VPS`
* **Mô tả:**
Lập kế hoạch chuẩn bị đưa các cải tiến mới lên môi trường thực tế (VPS Production):
- Đóng gói toàn bộ code ổn định mới nhất của nhánh `home`.
- Thiết lập quy trình chuyển đổi, di chuyển database cũ sang cấu trúc database cô lập theo user mới của ver_2.6 mà không làm mất dữ liệu lịch sử cũ của người dùng.
- Theo dõi tải tài nguyên VPS (CPU, RAM, Disk) sau khi đưa tính năng Client Render vào hoạt động để đánh giá mức độ giảm tải thực tế của Server.
* **Gán cho:** Lâm Đức Cương
* **Vai trò:** AI Engineer
* **Estimate:** 8 hours
* **Realtime:** 
* **Start date:** 
* **End date:** 
* **Deadline:** 2026-06-05
* **Trạng thái:** Chờ xử lý
* **SubTasks:**
- [ ] Tạo file nén source code build.
- [ ] Viết kịch bản backup database lịch sử hiện tại trên VPS.
- [ ] Cấu hình biến môi trường semaphore trên máy chủ VPS.

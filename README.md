# SRT Mobile — iPhone web app

## Chạy thử trên máy tính có Docker
1. Tạo API key tại https://platform.openai.com/api-keys (API tính phí riêng).
2. Tại thư mục dự án, chạy:
   ```bash
   docker build -t srt-mobile .
   docker run --rm -p 8080:8080 -e OPENAI_API_KEY="YOUR_API_KEY" srt-mobile
   ```
3. Mở http://localhost:8080 trên máy tính.

## Triển khai cho iPhone
1. Tạo một **Web Service** trên Render (https://render.com), kết nối GitHub repo chứa các file này.
2. Chọn **Docker** runtime, thêm environment variable `OPENAI_API_KEY` trong dashboard Render (không đưa key vào mã hoặc GitHub).
3. Triển khai và mở URL HTTPS do Render cấp trên Safari iPhone.
4. Safari > Chia sẻ > Thêm vào Màn hình chính.

Render free tier có thể không phù hợp với video dài, giới hạn upload hoặc timeout; chọn dịch vụ/gói có đủ RAM, disk, thời gian xử lý và dung lượng request. Nên thêm xác thực, rate limit, quota và chính sách lưu/xóa trước khi cho người khác dùng.

## Lưu ý
- Cần kết nối mạng; nhận diện sử dụng `whisper-1` với mốc thời gian theo đoạn, dịch sử dụng `gpt-4o-mini`.
- Chấp nhận MP4/MOV/M4V/MP3/M4A/WAV/WEBM/MPEG/MPGA. Giới hạn upload mặc định 100 MB; audio sau nén tối đa 24 MB.
- Mốc thời gian theo đoạn không chính xác tới từng từ; cần kiểm tra và sửa thủ công khi cần.
- Video không có lời nói sẽ không tạo được SRT từ hình ảnh/chữ trên màn hình (không có OCR).
- Không lưu video lâu dài: file tạm được xóa sau khi xử lý. Dịch vụ AI vẫn xử lý nội dung được gửi tới API theo điều khoản của nhà cung cấp.

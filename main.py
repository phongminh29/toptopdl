import os
import logging
import sys
import threading
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Updater, MessageHandler, Filters
import yt_dlp

# --- 1. SERVER DUY TRÌ SỰ SỐNG CHO RENDER (HEALTH CHECK) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running')

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server started on port {port}", flush=True)
    httpd.serve_forever()

# --- 2. CẤU HÌNH LOGGING ---
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, stream=sys.stdout)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- 3. HÀM TẢI VIDEO ĐA NỀN TẢNG ---
def download_video(url):
    # Đặt tên file dựa trên định danh luồng để tránh trùng lặp
    output_filename = f"video_{threading.get_ident()}.mp4"
    
    ydl_opts = {
        # Lấy định dạng mp4 tốt nhất, tự động gộp hình và tiếng bằng ffmpeg
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        'nocheckcertificate': True,
        'ignoreerrors': False,
        # Nếu anh có file cookies.txt cho Douyin, hãy bỏ dấu # ở dòng dưới:
         'cookiefile': 'cookies.txt', 
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_filename

# --- 4. HÀM XỬ LÝ TIN NHẮN TỪ TELEGRAM ---
def handle_message(update, context):
    raw_text = update.message.text
    
    # TỰ ĐỘNG TRÍCH XUẤT LINK TỪ VĂN BẢN (Xử lý lỗi dán kèm nội dung rác)
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    
    if url_match:
        url = url_match.group(1)
        # Loại bỏ các ký tự thừa ở cuối link nếu có
        url = url.split('?')[0] if 'douyin.com' in url else url 
        
        print(f"--- NHẬN YÊU CẦU: {url} ---", flush=True)
        status_msg = update.message.reply_text("⏳ Đang xử lý video (TikTok/Douyin/Reels)...")
        
        file_path = None
        try:
            # Tải video
            file_path = download_video(url)
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print(f"--- GỬI VIDEO: {file_path} ---", flush=True)
                with open(file_path, 'rb') as video:
                    update.message.reply_video(video=video, caption="✅ Video của anh đây!")
                status_msg.delete()
            else:
                status_msg.edit_text("❌ Lỗi: Không thể lấy được video. Link có thể bị riêng tư hoặc là dạng ảnh Slide.")
                
        except Exception as e:
            print(f"LỖI DOWNLOAD: {str(e)}", flush=True)
            status_msg.edit_text(f"❌ Bot gặp lỗi: {str(e)}")
            
        finally:
            # Xóa file sau khi gửi để giải phóng bộ nhớ
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
    else:
        # Nếu không tìm thấy link trong tin nhắn
        if "http" in raw_text:
             update.message.reply_text("Anh gửi link chuẩn giúp em nhé!")

# --- 5. CHƯƠNG TRÌNH CHÍNH ---
if __name__ == '__main__':
    # Chạy Web Server giả ở luồng phụ để Render không tắt Bot
    threading.Thread(target=run_health_server, daemon=True).start()
    
    print("🚀 BOT ĐANG KHỞI CHẠY (BẢN UPDATE ĐA NỀN TẢNG)...", flush=True)
    
    if not TOKEN:
        print("❌ LỖI: THIẾU TELEGRAM_TOKEN TRONG SETTINGS!", flush=True)
        sys.exit(1)

    # Khởi tạo Updater và Dispatcher
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Lắng nghe mọi tin nhắn văn bản
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Bắt đầu nhận tin từ Telegram
    updater.start_polling()
    print("✅ BOT ĐÃ ONLINE 24/7!", flush=True)
    updater.idle()
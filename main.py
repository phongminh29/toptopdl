import os
import logging
import sys
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Updater, MessageHandler, Filters
import yt_dlp

# --- SERVER DUY TRÌ SỰ SỐNG CHO RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Online')

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    httpd.serve_forever()

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- HÀM TẢI VIDEO ĐA NỀN TẢNG ---
def download_video(url):
    # Đặt tên file duy nhất để tránh xung đột khi nhiều người tải cùng lúc
    output_filename = f"video_{threading.get_ident()}.mp4"
    
    ydl_opts = {
        # Ưu tiên mp4, gộp video và audio tốt nhất
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        # Lách cơ chế chặn của Douyin/Facebook
        'nocheckcertificate': True,
        'extractor_args': {'tiktok': {'webpath_allow_no_video': True}},
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_filename

def handle_message(update, context):
    url = update.message.text
    # Danh sách các nền tảng hỗ trợ
    valid_platforms = ["tiktok.com", "douyin.com", "facebook.com", "fb.watch", "instagram.com"]
    
    if any(p in url for p in valid_platforms):
        print(f"--- ĐANG XỬ LÝ LINK: {url} ---", flush=True)
        status_msg = update.message.reply_text("⏳ Đang tải và xử lý video cho anh...")
        
        file_path = None
        try:
            file_path = download_video(url)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as video:
                    update.message.reply_video(video=video, caption="✅ Video của anh đây!")
                status_msg.delete()
            else:
                status_msg.edit_text("❌ Lỗi: Không thể tạo file video.")
                
        except Exception as e:
            print(f"Lỗi: {e}", flush=True)
            status_msg.edit_text(f"❌ Bot gặp lỗi khi tải: {str(e)}")
        finally:
            # Xóa file sau khi gửi để nhẹ server
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
    else:
        if "http" in url:
            update.message.reply_text("Em chỉ hỗ trợ: TikTok, Douyin, Facebook Reels và Instagram thôi ạ!")

if __name__ == '__main__':
    # Chạy server web phụ
    threading.Thread(target=run_health_server, daemon=True).start()
    
    print("🚀 BOT ĐANG KHỞI CHẠY (MULTILINGUAL BẢN CHUẨN)...", flush=True)
    
    if not TOKEN:
        print("❌ THIẾU TELEGRAM_TOKEN!", flush=True)
        sys.exit(1)

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    print("✅ HỆ THỐNG ĐÃ ONLINE!", flush=True)
    updater.idle()
import os
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Updater, MessageHandler, Filters
import yt_dlp

# --- WEB SERVER GIẢ ĐỂ DUY TRÌ RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running')

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- LOGIC TẢI VIDEO ĐA NỀN TẢNG ---
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, stream=sys.stdout)
TOKEN = os.getenv("TELEGRAM_TOKEN")

def download_video(url):
    video_path = 'video_download.mp4'
    ydl_opts = {
        # 'best' giúp lấy chất lượng tốt nhất có sẵn
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': video_path,
        'quiet': True,
        'no_warnings': True,
        # Thêm cấu hình để lách tường lửa Douyin/Facebook
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return video_path

def handle_message(update, context):
    url = update.message.text
    # Kiểm tra xem link có thuộc các nền tảng mình muốn không
    platforms = ["tiktok.com", "douyin.com", "facebook.com", "fb.watch"]
    
    if any(p in url for p in platforms):
        print(f"--- NHẬN LINK TỪ {url} ---", flush=True)
        msg = update.message.reply_text("⏳ Đang lấy video cho anh (TikTok/Douyin/Reels)...")
        try:
            path = download_video(url)
            if os.path.exists(path):
                update.message.reply_video(video=open(path, 'rb'), caption="✅ Gửi anh video!")
                os.remove(path)
                msg.delete()
            else:
                msg.edit_text("❌ Lỗi: Không tìm thấy file video.")
        except Exception as e:
            print(f"Lỗi: {e}", flush=True)
            msg.edit_text(f"❌ Lỗi xử lý: {str(e)}")
    else:
        # Phản hồi nhẹ nếu link không hợp lệ
        if "http" in url:
            update.message.reply_text("Hỗ trợ TikTok, Douyin và Facebook Reels thôi anh nhé!")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    
    print("🚀 BOT ĐANG KHỞI CHẠY BẢN UPDATE...", flush=True)
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    print("✅ BOT ĐÃ ONLINE (TikTok/Douyin/Reels)!", flush=True)
    updater.idle()
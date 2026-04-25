import os
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Updater, MessageHandler, Filters
import yt_dlp

# --- PHẦN 1: TẠO WEB GIẢ ĐỂ RENDER KHÔNG TẮT BOT ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Alive!')

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"--- Health check server started on port {port} ---", flush=True)
    server.serve_forever()

# --- PHẦN 2: LOGIC TẢI VIDEO TIKTOK ---
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, stream=sys.stdout)
TOKEN = os.getenv("TELEGRAM_TOKEN")

def download_tiktok(url):
    video_path = 'video.mp4'
    ydl_opts = {'format': 'best', 'outtmpl': video_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return video_path

def handle_message(update, context):
    url = update.message.text
    if "tiktok.com" in url:
        msg = update.message.reply_text("⏳ Chờ em tí, đang xử lý...")
        try:
            path = download_tiktok(url)
            update.message.reply_video(video=open(path, 'rb'), caption="✅ Gửi anh!")
            if os.path.exists(path): os.remove(path)
            msg.delete()
        except Exception as e:
            update.message.reply_text(f"❌ Lỗi: {e}")

if __name__ == '__main__':
    # Chạy server web ở luồng phụ
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Chạy Bot ở luồng chính
    print("🚀 BOT ĐANG KHỞI CHẠY TRÊN RENDER...", flush=True)
    if not TOKEN:
        print("❌ THIẾU TOKEN TRONG ENVIRONMENT VARIABLES!", flush=True)
    else:
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        updater.start_polling()
        print("✅ BOT ĐÃ ONLINE 24/7!", flush=True)
        updater.idle()
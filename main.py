import os, logging, sys, threading, re, requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import InputMediaPhoto
from telegram.ext import Updater, MessageHandler, Filters
import yt_dlp

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'Bot is Online')

def run_health_server():
    httpd = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    httpd.serve_forever()

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, stream=sys.stdout)
TOKEN = os.getenv("TELEGRAM_TOKEN")

def get_media_via_api(url):
    """Sử dụng API tikwm để lấy video/ảnh cho cả TikTok và Douyin"""
    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        resp = requests.get(api_url, timeout=20).json()
        if resp.get('code') == 0:
            return resp.get('data', {})
    except Exception as e:
        print(f"Lỗi API: {e}")
    return None

def handle_message(update, context):
    raw_text = update.message.text
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    if not url_match: return
    
    url = url_match.group(1).split('?')[0]
    print(f"--- ĐANG XỬ LÝ: {url} ---", flush=True)
    status_msg = update.message.reply_text("⏳ Đang bóc tách dữ liệu (TikTok/Douyin/Reels)...")

    try:
        # 1. ƯU TIÊN XỬ LÝ TIKTOK VÀ DOUYIN QUA API (VƯỢT LỖI COOKIE)
        if "tiktok.com" in url or "douyin.com" in url:
            data = get_media_via_api(url)
            if data:
                # Nếu là Slide ảnh (TikTok/Douyin đều dùng chung cấu trúc này)
                images = data.get('images', [])
                if images:
                    status_msg.edit_text(f"📸 Tìm thấy {len(images)} ảnh. Đang gửi...")
                    media_group = [InputMediaPhoto(img) for img in images[:10]]
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete()
                    return
                
                # Nếu là Video (Lấy link video không logo từ API)
                video_url = data.get('play')
                if video_url:
                    status_msg.edit_text("🎥 Đang gửi video cho anh...")
                    # Tikwm đôi khi dùng link CDN, mình gửi trực tiếp qua URL cho nhanh
                    update.message.reply_video(video=video_url, caption="✅ Gửi anh video (No Logo)!")
                    status_msg.delete()
                    return

        # 2. NẾU LÀ FACEBOOK REELS HOẶC API THẤT BẠI, DÙNG YT-DLP TẢI TRỰC TIẾP
        status_msg.edit_text("🎥 Đang tải video (FB Reels/Instagram)...")
        file_path = f"vid_{threading.get_ident()}.mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': file_path,
            'merge_output_format': 'mp4',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as v:
                update.message.reply_video(video=v, caption="✅ Gửi anh!")
            os.remove(file_path)
            status_msg.delete()
        else:
            status_msg.edit_text("❌ Lỗi: Không thể lấy dữ liệu từ link này.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Lỗi: {str(e)[:100]}")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 SIÊU BOT ĐÃ ONLINE - CHẤP HẾT COOKIE!", flush=True)
    updater.idle()
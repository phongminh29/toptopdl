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

def get_tiktok_photo_api(url):
    """Sử dụng API hỗ trợ bóc tách ảnh TikTok"""
    try:
        # Sử dụng API của tikwm hoặc các bên tương tự để lấy dữ liệu ảnh
        api_url = f"https://www.tikwm.com/api/?url={url}"
        resp = requests.get(api_url, timeout=15).json()
        
        if resp.get('code') == 0:
            data = resp.get('data', {})
            # Nếu là slide ảnh (images)
            images = data.get('images', [])
            if images:
                return images
    except Exception as e:
        print(f"Lỗi API: {e}")
    return None

def handle_message(update, context):
    raw_text = update.message.text
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    if not url_match: return
    
    url = url_match.group(1).split('?')[0]
    print(f"--- ĐANG XỬ LÝ: {url} ---", flush=True)
    status_msg = update.message.reply_text("⏳ Đang giải mã dữ liệu TikTok...")

    try:
        # ƯU TIÊN KIỂM TRA SLIDE ẢNH QUA API TRƯỚC
        if "tiktok.com" in url:
            images = get_tiktok_photo_api(url)
            if images:
                status_msg.edit_text(f"📸 Tìm thấy {len(images)} ảnh. Đang gửi cho anh...")
                # Telegram giới hạn 10 ảnh mỗi lần gửi
                media_group = [InputMediaPhoto(img) for img in images[:10]]
                update.message.reply_media_group(media=media_group)
                status_msg.delete()
                return

        # NẾU KHÔNG PHẢI ẢNH HOẶC API THẤT BẠI, DÙNG YT-DLP TẢI VIDEO
        status_msg.edit_text("🎥 Định dạng Video. Đang tải không logo...")
        file_path = f"vid_{threading.get_ident()}.mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': file_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'nocheckcertificate': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as v:
                update.message.reply_video(video=v, caption="✅ Gửi anh!")
            os.remove(file_path)
            status_msg.delete()
        else:
            status_msg.edit_text("❌ Lỗi: Không lấy được video này.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Lỗi: {str(e)[:100]}")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ONLINE - CHUYÊN TRỊ SLIDE ẢNH V4!", flush=True)
    updater.idle()
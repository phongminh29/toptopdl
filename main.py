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
    """Thử nhiều API khác nhau để lấy link video/ảnh cho TikTok và Douyin"""
    # Thử API 1: tikwm
    try:
        resp = requests.get(f"https://www.tikwm.com/api/?url={url}", timeout=15).json()
        if resp.get('code') == 0:
            return resp.get('data')
    except: pass
    
    # Thử API 2: ddl (Dự phòng cho Douyin)
    try:
        resp = requests.get(f"https://api.douyin.wtf/api/download?url={url}", timeout=15).json()
        if resp.get('status') == 'success':
            return resp.get('data')
    except: pass
    
    return None

def handle_message(update, context):
    raw_text = update.message.text
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    if not url_match: return
    
    url = url_match.group(1)
    status_msg = update.message.reply_text("⏳ Đang giải mã Douyin/TikTok...")

    try:
        # BƯỚC 1: GIẢI MÃ LINK RÚT GỌN (Quan trọng cho Douyin)
        headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'}
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        final_url = response.url
        print(f"--- LINK SAU GIẢI MÃ: {final_url} ---", flush=True)

        # BƯỚC 2: XỬ LÝ QUA API ĐỂ TRÁNH LỖI COOKIE
        if "douyin.com" in final_url or "tiktok.com" in final_url:
            data = get_media_via_api(final_url)
            if data:
                # Nếu là Slide ảnh
                images = data.get('images') or data.get('image_list')
                if images:
                    status_msg.edit_text(f"📸 Phát hiện Slide ảnh ({len(images)} tấm)...")
                    media_group = [InputMediaPhoto(img) for img in images[:10]]
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete(); return
                
                # Nếu là Video
                video_url = data.get('play') or data.get('video_url')
                if video_url:
                    status_msg.edit_text("🎥 Đang gửi video không logo...")
                    update.message.reply_video(video=video_url, caption="✅ Gửi anh!")
                    status_msg.delete(); return

        # BƯỚC 3: DÙNG YT-DLP CHO FACEBOOK REELS HOẶC KHI API LỖI
        status_msg.edit_text("🎥 Đang dùng bộ tải dự phòng (yt-dlp)...")
        file_path = f"vid_{threading.get_ident()}.mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': file_path, 'merge_output_format': 'mp4', 'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([final_url])
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as v:
                update.message.reply_video(video=v, caption="✅ Xong rồi anh!")
            os.remove(file_path); status_msg.delete()
        else:
            status_msg.edit_text("❌ Douyin chặn gắt quá, em không bẻ khóa được link này.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text("❌ Lỗi hệ thống. Anh thử lại sau nhé!")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ONLINE - CHUYÊN TRỊ DOUYIN 2026!", flush=True)
    updater.idle()
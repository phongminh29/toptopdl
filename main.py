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
    """Thử các cổng API mạnh nhất để bẻ khóa Douyin/TikTok"""
    # Danh sách các API Endpoint
    endpoints = [
        f"https://www.tikwm.com/api/?url={url}",
        f"https://api.douyin.wtf/api/download?url={url}",
        f"https://api.tmate.cc/v1/download?url={url}"
    ]
    
    for api_url in endpoints:
        try:
            print(f"--- ĐANG THỬ API: {api_url[:30]}... ---", flush=True)
            r = requests.get(api_url, timeout=12).json()
            # Xử lý kết quả trả về tùy theo từng API
            data = r.get('data') or r.get('result')
            if data: return data
        except:
            continue
    return None

def handle_message(update, context):
    raw_text = update.message.text
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    if not url_match: return
    
    url = url_match.group(1)
    status_msg = update.message.reply_text("⏳ Đang bẻ khóa link Douyin (Không dùng Cookie)...")

    try:
        # BƯỚC 1: GIẢI MÃ LINK (Lấy URL cuối cùng sau khi redirect)
        headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}
        with requests.get(url, headers=headers, timeout=10, stream=True, allow_redirects=True) as r:
            final_url = r.url
        
        print(f"--- ĐANG XỬ LÝ: {final_url} ---", flush=True)

        # BƯỚC 2: XỬ LÝ TIKTOK & DOUYIN (CHỈ DÙNG API)
        if "douyin.com" in final_url or "tiktok.com" in final_url:
            data = get_media_via_api(final_url)
            if data:
                # Xử lý Slide ảnh
                images = data.get('images') or data.get('image_list')
                if images:
                    status_msg.edit_text("📸 Phát hiện Slide ảnh. Đang gửi album...")
                    media_group = [InputMediaPhoto(img) for img in images[:10]]
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete(); return
                
                # Xử lý Video (Ưu tiên link Play không logo)
                video_url = data.get('play') or data.get('video_url') or data.get('nwm_video_url') or data.get('url')
                if video_url:
                    update.message.reply_video(video=video_url, caption="✅ Gửi anh video!")
                    status_msg.delete(); return
            
            # Nếu chạy đến đây tức là API cũng bó tay
            status_msg.edit_text("❌ Douyin chặn IP server quá gắt. Anh thử lại link khác hoặc chờ vài phút nhé!")
            return

        # BƯỚC 3: DÙNG YT-DLP CHO FACEBOOK REELS/INSTAGRAM
        status_msg.edit_text("🎥 Đang tải Video Reels/Instagram...")
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

    except Exception as e:
        print(f"LỖI: {str(e)}", flush=True)
        status_msg.edit_text("❌ Không tải được link này. Có thể link bị riêng tư hoặc nền tảng chặn.")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ONLINE - CHỐT HẠ DOUYIN!", flush=True)
    updater.idle()
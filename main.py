import os, logging, sys, threading, re, requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import InputMediaPhoto
from telegram.ext import Updater, MessageHandler, Filters
import yt_dlp

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'Bot is Running')

def run_health_server():
    httpd = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    httpd.serve_forever()

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, stream=sys.stdout)
TOKEN = os.getenv("TELEGRAM_TOKEN")

def handle_message(update, context):
    raw_text = update.message.text
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    
    if not url_match: return
    url = url_match.group(1)
    status_msg = update.message.reply_text("⏳ Đang kiểm tra link (Video/Ảnh)...")

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'impersonate': 'chrome', # Giả lập chrome để vượt rào Douyin
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # TRƯỜNG HỢP 1: TIKTOK SLIDE ẢNH
            if 'entries' in info or info.get('formats') is None or len(info.get('formats')) == 0:
                images = []
                # Một số link TikTok Slide trả về danh sách entries
                entries = info.get('entries', [info])
                for entry in entries:
                    if 'requested_formats' in entry: continue
                    # Lấy link ảnh chất lượng cao nhất
                    img_url = entry.get('url') or entry.get('thumbnails', [{}])[-1].get('url')
                    if img_url: images.append(img_url)
                
                if images:
                    status_msg.edit_text(f"📸 Phát hiện Slide ảnh ({len(images)} ảnh). Đang gửi...")
                    media_group = [InputMediaPhoto(img) for img in images[:10]] # Telegram giới hạn 10 ảnh/album
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete()
                    return

            # TRƯỜNG HỢP 2: VIDEO (TIKTOK/DOUYIN/REELS)
            status_msg.edit_text("🎥 Đang tải video không logo...")
            file_path = f"vid_{threading.get_ident()}.mp4"
            
            video_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': file_path,
                'merge_output_format': 'mp4',
                'impersonate': 'chrome',
                'nocheckcertificate': True,
            }
            with yt_dlp.YoutubeDL(video_opts) as ydl_vid:
                ydl_vid.download([url])
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as v:
                    update.message.reply_video(video=v, caption="✅ Gửi anh video!")
                os.remove(file_path)
                status_msg.delete()

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Không tải được. Có thể link bị riêng tư hoặc Douyin chặn IP.\nLỗi: {str(e)[:50]}...")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ONLINE! ĐÃ HỖ TRỢ SLIDE ẢNH.", flush=True)
    updater.idle()
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
    status_msg = update.message.reply_text("⏳ Đang kiểm tra link...")

    try:
        # Cấu hình yt-dlp bản chuẩn không dùng impersonate nếu server thiếu lib
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # KIỂM TRA NẾU LÀ SLIDE ẢNH (TIKTOK)
            # Thường TikTok Slide sẽ có thông tin thumbnails rất nhiều và không có formats video
            formats = info.get('formats', [])
            if not formats or info.get('duration') is None:
                images = []
                # Lấy danh sách ảnh từ thumbnails hoặc post_thumbnails
                temp_images = info.get('thumbnails', [])
                for img in temp_images:
                    # Lấy những ảnh có độ phân giải cao (thường không chứa 'm' hoặc 'p' ở cuối url của TikTok)
                    if 'url' in img:
                        images.append(img['url'])
                
                # Lọc trùng và lấy ảnh xịn
                unique_images = list(dict.fromkeys(images))[-10:] # Lấy 10 ảnh cuối (thường là ảnh gốc)

                if len(unique_images) > 1:
                    status_msg.edit_text(f"📸 Đang gửi {len(unique_images)} ảnh từ Slide...")
                    media_group = [InputMediaPhoto(img) for img in unique_images]
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete()
                    return

            # TRƯỜNG HỢP LÀ VIDEO
            status_msg.edit_text("🎥 Đang tải video không logo...")
            file_path = f"vid_{threading.get_ident()}.mp4"
            
            video_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': file_path,
                'merge_output_format': 'mp4',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(video_opts) as ydl_vid:
                ydl_vid.download([url])
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as v:
                    update.message.reply_video(video=v, caption="✅ Gửi anh video!")
                os.remove(file_path)
                status_msg.delete()
            else:
                status_msg.edit_text("❌ Lỗi: Không lấy được file video.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Thất bại. Link có thể bị chặn hoặc sai định dạng.\nChi tiết: {str(e)[:100]}")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ĐÃ ONLINE!", flush=True)
    updater.idle()
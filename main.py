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

def handle_message(update, context):
    raw_text = update.message.text
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    if not url_match: return
    
    url = url_match.group(1)
    # Làm sạch link TikTok photo
    if "tiktok.com" in url and "/photo/" in url:
        url = url.split('?')[0]

    status_msg = update.message.reply_text("⏳ Đang kiểm tra định dạng (Video/Slide ảnh)...")

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception:
                info = {}

            # KIỂM TRA NẾU LÀ SLIDE ẢNH TIKTOK
            if "/photo/" in url or info.get('duration') == 0 or not info.get('formats'):
                status_msg.edit_text("📸 Đang bóc tách Slide ảnh TikTok cho anh...")
                
                # Cách lấy ảnh thủ công nếu yt-dlp thất bại
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10).text
                # Tìm tất cả link ảnh trong mã nguồn TikTok
                images = re.findall(r'https://p16-sign-va\.tiktokcdn\.com/[^"& ]+', response)
                
                if not images:
                    # Thử lấy từ info thumbnails nếu có
                    images = [t['url'] for t in info.get('thumbnails', []) if 'url' in t]

                if images:
                    # Lọc trùng và lấy ảnh nét (thường ảnh TikTok Photo có đuôi ~c5_1080x1080)
                    unique_images = list(dict.fromkeys(images))
                    final_images = [img for img in unique_images if "obj/tos-maliva-p-0037" in img or "p16-sign" in img][:10]
                    
                    if final_images:
                        media_group = [InputMediaPhoto(img) for img in final_images]
                        update.message.reply_media_group(media=media_group)
                        status_msg.delete()
                        return
                    
            # TRƯỜNG HỢP TẢI VIDEO
            status_msg.edit_text("🎥 Định dạng Video. Đang tải không logo...")
            file_path = f"vid_{threading.get_ident()}.mp4"
            video_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': file_path,
                'merge_output_format': 'mp4',
            }
            with yt_dlp.YoutubeDL(video_opts) as ydl_vid:
                ydl_vid.download([url])
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as v:
                    update.message.reply_video(video=v, caption="✅ Gửi anh video!")
                os.remove(file_path)
                status_msg.delete()
            else:
                status_msg.edit_text("❌ Lỗi: Không tải được video này.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Bot bó tay với link này rồi anh! Thử link khác xem sao.\nLỗi: {str(e)[:50]}")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ONLINE! ĐÃ CẬP NHẬT TRÌNH BÓC TÁCH ẢNH.", flush=True)
    updater.idle()
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
    
    url = url_match.group(1).split('?')[0] # Làm sạch link
    print(f"--- ĐANG XỬ LÝ: {url} ---", flush=True)
    status_msg = update.message.reply_text("⏳ Đang kiểm tra định dạng...")

    try:
        # KIỂM TRA NHANH NẾU LÀ TIKTOK PHOTO
        if "/photo/" in url or "vt.tiktok.com" in url or "v.douyin.com" in url:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
            }
            # Thử lấy mã nguồn trang để bóc link ảnh thủ công
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            page_content = resp.text
            final_url = resp.url

            if "/photo/" in final_url:
                status_msg.edit_text("📸 Phát hiện Slide ảnh. Đang bóc tách dữ liệu...")
                # Tìm link ảnh gốc trong script của TikTok (thường nằm trong các thẻ image-src hoặc JSON)
                images = re.findall(r'https://p16-sign-[^"\\& ]+', page_content)
                if not images:
                    images = re.findall(r'https://p[^"\\& ]+~tplv-photomode-video[^"\\& ]+', page_content)
                
                unique_images = []
                for img in images:
                    img_clean = img.replace('\\u002F', '/')
                    if img_clean not in unique_images:
                        unique_images.append(img_clean)

                if unique_images:
                    # Lấy 10 ảnh đầu tiên chất lượng cao nhất
                    final_list = unique_images[:10]
                    media_group = [InputMediaPhoto(img) for img in final_list]
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete()
                    return

        # NẾU KHÔNG PHẢI ẢNH HOẶC BÓC TÁCH THỦ CÔNG THẤT BẠI, CHUYỂN SANG TẢI VIDEO
        status_msg.edit_text("🎥 Đang tải video không logo...")
        file_path = f"vid_{threading.get_ident()}.mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': file_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as v:
                update.message.reply_video(video=v, caption="✅ Gửi anh video!")
            os.remove(file_path)
            status_msg.delete()
        else:
            status_msg.edit_text("❌ Không lấy được file. Link có thể bị riêng tư hoặc không hỗ trợ.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Lỗi: {str(e)[:100]}")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ONLINE! ĐÃ FIX LỖI TIKTOK PHOTO.", flush=True)
    updater.idle()
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
    print(f"--- ĐANG KIỂM TRA: {url} ---", flush=True)
    status_msg = update.message.reply_text("⏳ Đang phân tích dữ liệu...")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # BƯỚC 1: GIẢI MÃ LINK RÚT GỌN (vt.tiktok.com -> tiktok.com/photo/...)
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        final_url = resp.url
        print(f"--- LINK SAU GIẢI MÃ: {final_url} ---", flush=True)

        # BƯỚC 2: KIỂM TRA NẾU LÀ SLIDE ẢNH (CHẠY RIÊNG KHÔNG DÙNG YT-DLP)
        if "/photo/" in final_url or "note" in final_url:
            status_msg.edit_text("📸 Phát hiện Slide ảnh. Đang bóc tách từng tấm...")
            
            # Quét link ảnh từ mã nguồn trang web
            page_content = resp.text
            # Tìm các link ảnh chất lượng cao trong script của TikTok
            image_links = re.findall(r'https://p16-sign-[^"\\& ]+', page_content)
            
            if not image_links:
                image_links = re.findall(r'https://p19-sign-[^"\\& ]+', page_content)

            if image_links:
                # Làm sạch và lọc trùng
                unique_images = []
                for img in image_links:
                    clean_img = img.replace('\\u002F', '/')
                    if clean_img not in unique_images:
                        unique_images.append(clean_img)
                
                # Lọc lấy những ảnh có kích thước lớn (thường chứa '720x720' hoặc không có đuôi thumbnail)
                final_images = [img for img in unique_images if "image" in img or "obj" in img][:10]
                
                if final_images:
                    media_group = [InputMediaPhoto(img) for img in final_images]
                    update.message.reply_media_group(media=media_group)
                    status_msg.delete()
                    return

        # BƯỚC 3: NẾU LÀ VIDEO, DÙNG YT-DLP TẢI NHƯ BÌNH THƯỜNG
        status_msg.edit_text("🎥 Định dạng Video. Đang tải không logo...")
        file_path = f"vid_{threading.get_ident()}.mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': file_path,
            'merge_output_format': 'mp4',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([final_url])
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as v:
                update.message.reply_video(video=v, caption="✅ Gửi anh video!")
            os.remove(file_path)
            status_msg.delete()
        else:
            status_msg.edit_text("❌ Lỗi: Không lấy được file video.")

    except Exception as e:
        print(f"Lỗi: {e}")
        status_msg.edit_text(f"❌ Lỗi: Link này hiện tại TikTok chặn bóc tách.\nThử link khác xem sao anh!")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("🚀 BOT ĐÃ ONLINE - CHUYÊN TRỊ SLIDE ẢNH!", flush=True)
    updater.idle()
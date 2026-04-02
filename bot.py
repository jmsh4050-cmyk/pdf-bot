import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 

bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل ملف المحاضرة (PDF) وسأقوم بترجمته لك بتصميم احترافي (إنجليزي + عربي) مع الصور 🩺✨")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        bot.reply_to(message, f"🚫 يرجى الاشتراك بالقناة أولاً لتفعيل البوت: {CHANNEL_USERNAME}")
        return

    msg = bot.reply_to(message, "⏳ جاري تصميم الملف بالترجمة المزدوجة والصور... انتظر قليلاً")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Translated_{message.document.file_name}"
        
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 40
            
            # --- أولاً: معالجة الصور (مثل صفحة 5 في ملفك) ---
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 100: continue # تجاهل الأيقونات الصغيرة جداً

                    img_name = f"img_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    # وضع الصورة بمنتصف الصفحة
                    img_rect = fitz.Rect(100, y_offset, 500, y_offset + 220)
                    new_page.insert_image(img_rect, filename=img_name, keep_proportion=True)
                    y_offset += 240
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # --- ثانياً: الترجمة المزدوجة (مثل صفحات 1-4 في ملفك) ---
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 5:
                        try:
                            # ترجمة السطر
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)

                            if y_offset > 760:
                                new_page = out_doc.new_page()
                                y_offset = 40

                            # كتابة الإنجليزي (أسود)
                            new_page.insert_text((50, y_offset), line, fontsize=12, color=(0,0,0))
                            y_offset += 18
                            # كتابة العربي (أزرق غامق للوضوح)
                            new_page.insert_text((50, y_offset), fixed_ar, fontsize=12.5, fontname="f0", fontfile=font_path, color=(0, 0.2, 0.5))
                            y_offset += 35
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()

        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم التصميم بنجاح! ترجمة مزدوجة مع صور توضيحية.")
        
        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

bot.polling()
    

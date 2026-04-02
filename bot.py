import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات (سحب التوكن من Railway) ---
# سيبحث البوت عن متغير باسم BOT_TOKEN في إعدادات Railway
API_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    """إصلاح الخط العربي للـ PDF"""
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, f"أهلاً {user_name}! 🩺\nتم تحديث البوت لتصميم الملازم الاحترافية (نصوص وصور موسطة).")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF فقط.")
        return

    msg = bot.reply_to(message, "⏳ جاري تصميم الملزمة (تنسيق موسط مثل الهرمونات)...")

    try:
        user_id = message.from_user.id
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Professional_{message.document.file_name}"
        
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" # يجب أن يكون الملف مرفوعاً في GitHub

        page_width = 595 # عرض صفحة A4 القياسي
        
        for page in doc:
            new_page = out_doc.new_page(width=page_width, height=842)
            y_offset = 60
            
            # --- 1. معالجة وتوسيط الصور (مثل صفحة 5 في ملفك) ---
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 100: continue 

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    # توسيط الصور
                    img_w = 380 
                    img_h = 240 
                    img_x = (page_width - img_w) / 2 
                    
                    if y_offset > 500:
                        new_page = out_doc.new_page(width=page_width, height=842)
                        y_offset = 60
                    
                    img_rect = fitz.Rect(img_x, y_offset, img_x + img_w, y_offset + img_h)
                    new_page.insert_image(img_rect, filename=img_name, keep_proportion=True)
                    y_offset += img_h + 40
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # --- 2. معالجة وتوسيط النصوص (نفس أسلوب الهرمونات) ---
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            # ترجمة السطر
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)

                            if y_offset > 780:
                                new_page = out_doc.new_page(width=page_width, height=842)
                                y_offset = 60

                            # كتابة الإنجليزي (موسط)
                            eng_rect = fitz.Rect(50, y_offset, 545, y_offset + 25)
                            new_page.insert_textbox(eng_rect, line, fontsize=11.5, align=1, color=(0,0,0))
                            y_offset += 22
                            
                            # كتابة العربي (موسط بلون أزرق طبي)
                            ar_rect = fitz.Rect(50, y_offset, 545, y_offset + 25)
                            new_page.insert_textbox(ar_rect, fixed_ar, fontsize=12, fontname="f0", fontfile=font_path, align=1, color=(0, 0.3, 0.6))
                            y_offset += 45 # مسافة مريحة بين الفقرات
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()

        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم التصميم بنجاح لدفعة تمريض 2025")
        
        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"خطأ: تأكد من ضبط التوكن في Railway ووجود الخط Amiri.ttf")

bot.polling()

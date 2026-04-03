import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "تم تحديث التنسيق: ملء عرض الورقة + مسافات واسعة بين الأسطر ✅\nأرسل الملزمة الآن.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"FullWidth_Mlazma_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" 

        for page in doc:
            # إنشاء صفحة بيضاء جديدة بنفس الأبعاد
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            y_offset = 50  # نقطة البداية من الأعلى
            page_width = page.rect.width
            margin = 50    # الهامش الجانبي

            # 1. نقل الصور (بشكل ممركز في الأعلى)
            for img_info in page.get_image_info():
                try:
                    img_rect = fitz.Rect(margin, y_offset, page_width - margin, y_offset + 200)
                    new_page.insert_image(img_rect, stream=doc.extract_image(img_info["xref"])["image"], keep_proportion=True)
                    y_offset += 220
                    break # نأخذ صورة واحدة لتنظيم الصفحة
                except: pass

            # 2. استخراج النصوص وإعادة توزيعها على عرض الورقة
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                txt = block[4].replace('\n', ' ').strip()
                if len(txt) < 3: continue
                
                try:
                    # الترجمة
                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                    fixed_ar = fix_arabic(trans)

                    # تحديد الحجم (16 للعناوين، 14 للعادي)
                    is_title = len(txt) < 40 
                    current_size = 16 if is_title else 14

                    # التحقق من المساحة المتبقية في الصفحة
                    if y_offset > page.rect.height - 80:
                        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                        y_offset = 50

                    # أ. كتابة النص الإنجليزي (يمتد من الهامش للهامش)
                    # نستخدم textbox لضمان التفاف النص إذا كان طويلاً
                    rect_en = fitz.Rect(margin, y_offset, page_width - margin, y_offset + 100)
                    actual_height_en = new_page.insert_textbox(rect_en, txt, fontsize=current_size, color=(0, 0, 0), align=fitz.TEXT_ALIGN_LEFT)
                    
                    y_offset += (abs(actual_height_en) if actual_height_en != 0 else current_size) + 5

                    # ب. كتابة النص العربي (تحته وبمحاذاة اليمين)
                    rect_ar = fitz.Rect(margin, y_offset, page_width - margin, y_offset + 100)
                    actual_height_ar = new_page.insert_textbox(rect_ar, fixed_ar, fontsize=current_size - 1, 
                                                               fontname="f0", fontfile=font_path, 
                                                               color=(0.8, 0, 0), align=fitz.TEXT_ALIGN_RIGHT)
                    
                    # ج. إضافة فراغ واسع (Gap) بين الفقرات المترجمة
                    y_offset += (abs(actual_height_ar) if actual_height_ar != 0 else current_size) + 35 

                except: continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم إعادة تنسيق الملزمة بعرض كامل.")
            
    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()

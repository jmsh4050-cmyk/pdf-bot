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
    # معالجة النصوص العربية لتظهر صحيحة في الـ PDF
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! أرسل ملف الـ PDF وسأقوم بترجمته فقرة بفقرة (إنجليزي وتحته عربي) ✅")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"Translated_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    bot.reply_to(message, "⏳ جاري المعالجة... أترجم الآن فقرة بفقرة.")

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" # تأكد من وجود ملف الخط بجانب الكود

        for page in doc:
            # إنشاء صفحة جديدة بنفس أبعاد الأصل
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            y_offset = 50 # نقطة البداية من أعلى الصفحة
            margin = 50   # الهامش الجانبي
            width = page.rect.width - (2 * margin)

            # استخراج النصوص ككتل (Blocks) للحفاظ على سياق الفقرة
            blocks = page.get_text("blocks")
            
            for block in blocks:
                text = block[4].replace('\n', ' ').strip()
                
                if len(text) > 2:
                    try:
                        # ترجمة الفقرة كاملة
                        translation = GoogleTranslator(source='en', target='ar').translate(text)
                        fixed_ar = fix_arabic(translation)

                        # التحقق من المساحة المتبقية في الصفحة قبل الكتابة
                        if y_offset > page.rect.height - 100:
                            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                            y_offset = 50

                        # 1. كتابة الفقرة الإنجليزية (يسار)
                        # نستخدم textbox لضمان التفاف النص إذا كان طويلاً
                        rect_en = fitz.Rect(margin, y_offset, margin + width, y_offset + 300)
                        height_en = new_page.insert_textbox(rect_en, text, fontsize=12, color=(0, 0, 0), align=0)
                        
                        y_offset += abs(height_en) + 5 # مسافة بسيطة بين الأصل والترجمة

                        # 2. كتابة الترجمة العربية (يمين) تحتها مباشرة
                        rect_ar = fitz.Rect(margin, y_offset, margin + width, y_offset + 300)
                        height_ar = new_page.insert_textbox(rect_ar, fixed_ar, fontsize=12, 
                                                            fontname="f0", fontfile=font_path,
                                                            color=(0.8, 0, 0), align=1) # اللون الأحمر للمحاذاة لليمين
                        
                        # إضافة مسافة كبيرة (سطر فارغ) قبل الفقرة التالية
                        y_offset += abs(height_ar) + 25 

                    except Exception as e:
                        print(f"Error in block: {e}")
                        continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ اكتملت الترجمة (فقرة وتحتها ترجمتها).")
            
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")
    
    # تنظيف الملفات المؤقتة
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()

import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

# مقاس ورق A4 العالمي بالنقاط (Points)
A4_WIDTH = 595
A4_HEIGHT = 842

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "تم ضبط البوت: مقاس الورقة A4 والترجمة سطر بسطر ✅\nأرسل الملزمة الآن.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"A4_Translated_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    bot.reply_to(message, "⏳ جاري تحويل الملزمة إلى مقاس A4 وترجمتها سطر بسطر...")

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" 

        for page in doc:
            # إنشاء صفحة جديدة بمقاس A4 حصراً
            new_page = new_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
            y_offset = 50 
            margin = 50
            max_width = A4_WIDTH - (2 * margin)

            # استخراج النصوص سطر بسطر (Lines)
            words = page.get_text("words") # نحصل على الكلمات مع إحداثياتها
            
            # تجميع الكلمات في أسطر بناءً على ارتفاعها (y)
            lines = {}
            for w in words:
                y_coord = round(w[1], 1) # إحداثي الارتفاع
                if y_coord not in lines:
                    lines[y_coord] = []
                lines[y_coord].append(w)

            # ترتيب الأسطر من الأعلى للأسفل
            for y in sorted(lines.keys()):
                line_words = sorted(lines[y], key=lambda x: x[0]) # ترتيب الكلمات من اليسار لليمين
                line_text = " ".join([w[4] for w in line_words]).strip()

                if len(line_text) > 2:
                    try:
                        # ترجمة السطر
                        translation = GoogleTranslator(source='en', target='ar').translate(line_text)
                        fixed_ar = fix_arabic(translation)

                        # التحقق من نهاية الصفحة
                        if y_offset > A4_HEIGHT - 80:
                            new_page = new_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
                            y_offset = 50

                        # 1. كتابة السطر الإنجليزي (أسود)
                        new_page.insert_text((margin, y_offset), line_text, fontsize=12, color=(0, 0, 0))
                        y_offset += 18 # مسافة بسيطة للترجمة

                        # 2. كتابة السطر العربي (أحمر - محاذاة يمين)
                        # نستخدم textbox لضمان بقاء العربي ضمن حدود الـ A4
                        rect_ar = fitz.Rect(margin, y_offset - 10, A4_WIDTH - margin, y_offset + 20)
                        new_page.insert_textbox(rect_ar, fixed_ar, fontsize=11, 
                                               fontname="f0", fontfile=font_path,
                                               color=(0.8, 0, 0), align=1)
                        
                        y_offset += 30 # مسافة قبل السطر القادم

                    except: continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم الإنجاز بمقاس A4 وتنسيق سطر بسطر.")
            
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()

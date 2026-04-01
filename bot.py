import os
import telebot
import fitz  # PyMuPDF
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from googletrans import Translator

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
bot = telebot.TeleBot(API_TOKEN)
translator = Translator()

class StyledPDF(FPDF):
    def header(self):
        # إضافة شعار أو عنوان علوي للملزمة
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Medical Lecture Translation - 2025', 0, 1, 'C')
        self.ln(5)

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً وسام! أرسل ملف الـ PDF وسأقوم بترجمته وتنسيقه لك بشكل احترافي.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف بصيغة PDF فقط.")
        return

    file_info = bot.get_file(message.document.file_id)
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"translated_{message.chat.id}.pdf"
    
    with open(input_path, 'wb') as f:
        f.write(bot.download_file(file_info.file_path))
    
    bot.reply_to(message, "⏳ جاري استخراج النص وترجمته... انتظر قليلاً.")

    try:
        # 1. استخراج النص من الملف الأصلي
        doc = fitz.open(input_path)
        pdf = StyledPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)

        for page in doc:
            text = page.get_text()
            if text.strip():
                # 2. الترجمة (تحافظ على المصطلحات)
                # تقسيم النص لفقرات للحفاظ على الهيكل
                paragraphs = text.split('\n')
                for p in paragraphs:
                    if p.strip():
                        translation = translator.translate(p, dest='ar').text
                        
                        # كتابة النص الأصلي (إنجليزي)
                        pdf.set_text_color(0, 0, 255) # لون أزرق للأصلي
                        pdf.multi_cell(0, 8, txt=p, align='L')
                        
                        # كتابة الترجمة (عربي)
                        pdf.set_text_color(0, 0, 0) # لون أسود للترجمة
                        # ملاحظة: لظهور العربي بالـ PDF تحتاج إضافة خط .ttf يدعم العربية
                        pdf.multi_cell(0, 8, txt=fix_arabic(translation), align='R')
                        pdf.ln(2)

        pdf.output(output_path)
        doc.close()

        # 3. إرسال الملف المنسق
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✨ محاضرتك المترجمة بتنسيق مرتب")

    except Exception as e:
        bot.send_message(message.chat.id, f"حدث خطأ أثناء المعالجة: {str(e)}")
    finally:
        # تنظيف الملفات المؤقتة
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

bot.polling(none_stop=True)

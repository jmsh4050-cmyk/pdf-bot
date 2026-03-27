import telebot
import fitz  # PyMuPDF
from googletrans import Translator
from fpdf import FPDF
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات الأساسية ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
bot = telebot.TeleBot(API_TOKEN)
translator = Translator()

def fix_arabic(text):
    # تصحيح اتجاه العربي للكتابة داخل الـ PDF
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "أرسل ملف PDF فقط.")
        return

    msg = bot.reply_to(message, "⏳ جاري البدء بالترجمة المزدوجة...")

    try:
        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{message.from_user.id}.pdf"
        output_pdf = f"Result_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        # إعداد ملف الـ PDF الجديد
        pdf_out = FPDF()
        try:
            # نحاول نستخدم الخط العربي اللي رفعته أنت
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.set_font('Amiri', size=11)
        except:
            # إذا ما لقى الخط، يستخدم Arial (احتياط)
            pdf_out.set_font("Arial", size=11)

        pdf_out.add_page()
        doc = fitz.open(input_pdf)

        for page in doc:
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    if len(line.strip()) > 3:
                        try:
                            # ترجمة السطر
                            translated = translator.translate(line, dest='ar').text
                            fixed_ar = fix_arabic(translated)
                            
                            # كتابة النص الأصلي (إنجليزي)
                            pdf_out.set_text_color(0, 0, 0) # أسود
                            pdf_out.multi_cell(0, 8, line, align='L')
                            
                            # كتابة الترجمة (عربي)
                            pdf_out.set_text_color(200, 0, 0) # أحمر
                            pdf_out.multi_cell(0, 8, fixed_ar, align='R')
                            pdf_out.ln(2) # مسافة بين الأسطر
                        except: continue

        pdf_out.output(output_pdf)
        
        # إرسال الملف النهائي
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ اكتملت الترجمة الأساسية.")

        # تنظيف الملفات المؤقتة
        doc.close()
        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")

print("البوت بدأ العمل...")
bot.polling()

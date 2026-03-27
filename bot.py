import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from fpdf import FPDF
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً وسام! أرسل الـ PDF وسأترجمه لك (ترجمة مزدوجة مستقرة).")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    msg = bot.reply_to(message, "⏳ جاري المعالجة (استخدمنا نظاماً أكثر استقراراً)...")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{message.chat.id}.pdf"
        output_pdf = f"Result_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        pdf_out = FPDF()
        try:
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.set_font('Amiri', size=11)
        except:
            pdf_out.set_font("Arial", size=11)

        pdf_out.add_page()
        doc = fitz.open(input_pdf)

        for page in doc:
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if len(clean_line) > 3:
                        try:
                            # استخدام المترجم المستقر الجديد
                            translated = GoogleTranslator(source='en', target='ar').translate(clean_line)
                            fixed_ar = fix_arabic(translated)
                            
                            if pdf_out.get_y() > 260: pdf_out.add_page()
                            
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 8, clean_line, align='L')
                            
                            pdf_out.set_text_color(200, 0, 0)
                            pdf_out.multi_cell(0, 8, fixed_ar, align='R')
                            pdf_out.ln(2)
                        except: continue

        pdf_out.output(output_pdf)
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ اكتملت الترجمة بنجاح.")

        doc.close()
        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")

bot.polling()

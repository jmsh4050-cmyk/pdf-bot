import telebot
import fitz  # PyMuPDF
from googletrans import Translator
from fpdf import FPDF
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 

bot = telebot.TeleBot(API_TOKEN)
translator = Translator()

def fix_arabic(text):
    # ربط الحروف العربية وتعديل الاتجاه
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        bot.reply_to(message, f"🚫 اشترك أولاً في قناة المطور:\n{CHANNEL_USERNAME}")
        return

    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    msg = bot.reply_to(message, "⏳ جاري ترجمة وتنسيق المحاضرة...")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Translated_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        pdf_out = FPDF()
        # استخدام ملف الخط Amiri.ttf الموجود عندك بالـ GitHub
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
                    if len(line.strip()) > 3:
                        try:
                            # الترجمة للعربية
                            translated = translator.translate(line, dest='ar').text
                            fixed_ar = fix_arabic(translated)
                            if pdf_out.get_y() > 260: pdf_out.add_page()
                            # كتابة النص الأصلي والمترجم
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 8, line, align='L')
                            pdf_out.set_text_color(220, 20, 60)
                            pdf_out.multi_cell(0, 8, fixed_ar, align='R')
                            pdf_out.ln(2)
                        except: continue

        pdf_out.output(output_pdf)
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم الترجمة لدفعة 2025")

        doc.close()
        os.remove(input_pdf)
        os.remove(output_pdf)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")

bot.polling()

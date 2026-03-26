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
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id

    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اشترك في القناة أولاً ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        markup.add(btn)
        bot.reply_to(message, f"🚫 لاستخدام البوت، يجب عليك الاشتراك في القناة:\n{CHANNEL_USERNAME}", reply_markup=markup)
        return

    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    msg = bot.reply_to(message, "⏳ جاري التنسيق والترجمة (انتظر قليلاً)...")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf_name = f"in_{user_id}.pdf"
        output_pdf_name = f"Formatted_{message.document.file_name}"

        with open(input_pdf_name, 'wb') as f:
            f.write(downloaded_file)

        pdf_out = FPDF()
        
        # --- تعديل جوهري لمنع الـ Crash ---
        try:
            # نحاول تحميل الخط Amiri من المستودع
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.set_font('Amiri', size=10)
        except:
            # إذا فشل، نستخدم خط النظام الافتراضي بدلاً من مسارات وهمية
            pdf_out.set_font("Arial", size=10)

        pdf_out.set_margins(10, 10, 10)
        pdf_out.add_page()

        doc = fitz.open(input_pdf_name)

        for page in doc:
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if len(clean_line) > 3:
                        try:
                            translated = translator.translate(clean_line, dest='ar').text
                            fixed_ar = fix_arabic(translated)
                            if pdf_out.get_y() > 260: pdf_out.add_page()
                            
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 6, clean_line, align='L')
                            
                            pdf_out.set_text_color(220, 20, 60)
                            pdf_out.multi_cell(0, 6, fixed_ar, align='R')
                            pdf_out.ln(1)
                        except: continue

            # استخراج الصور مع الحفاظ على فلترك الخاص
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 100 or base_image["height"] < 100: continue

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, 'wb') as f:
                        f.write(base_image["image"])

                    if pdf_out.get_y() > 220: pdf_out.add_page()
                    pdf_out.image(img_name, w=100)
                    os.remove(img_name)
                except: pass

        pdf_out.output(output_pdf_name)
        with open(output_pdf_name, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم التنسيق بنجاح لدفعة 2025 \nقناتنا: {CHANNEL_USERNAME}")

        doc.close()
        os.remove(input_pdf_name)
        os.remove(output_pdf_name)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")

bot.polling()
                            

import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from fpdf import FPDF
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
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF للترجمة بالأحجام المطلوبة لدفعة التمريض.\nقناتنا: {CHANNEL_USERNAME}")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اشترك في القناة أولاً ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        markup.add(btn)
        bot.reply_to(message, f"🚫 عذراً، اشترك في القناة لاستخدام البوت:\n{CHANNEL_USERNAME}", reply_markup=markup)
        return

    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    msg = bot.reply_to(message, "⏳ جاري استخراج الصور الصافية وترجمة النصوص بالأحجام الجديدة...")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Translated_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        pdf_out = FPDF()
        try:
            # تحميل الخطوط
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.add_font('AmiriB', '', 'Amiri-Bold.ttf', uni=True) 
        except: pass

        pdf_out.add_page()
        doc = fitz.open(input_pdf)

        for page in doc:
            # --- الصور (مع تقليل الفراغات حولها) ---
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 150 or base_image["height"] < 150: continue

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f:
                        f.write(base_image["image"])
                    
                    if pdf_out.get_y() > 200: pdf_out.add_page()
                    pdf_out.image(img_name, x=45, w=100) 
                    pdf_out.ln(2) # فراغ بسيط بعد الصورة
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # --- النصوص ---
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            # كشف العناوين (إذا كان السطر أحرف كبيرة وقصير)
                            is_header = line.isupper() and len(line) < 60
                            
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            
                            if pdf_out.get_y() > 270: pdf_out.add_page()

                            # تنظيف النص الإنجليزي منعاً للكراش
                            clean_eng = line.encode('cp1252', 'ignore').decode('cp1252')

                            # 1. إنجليزي: عنوان (15 Bold) أو نص عادي (14)
                            pdf_out.set_font('Arial', 'B' if is_header else '', 15 if is_header else 14)
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 5.5, clean_eng, align='L') # تقليل المسافة العمودية لضغط الفراغ

                            # 2. عربي: عنوان (15 Bold) أو نص عادي (14.5)
                            try:
                                f_style = 'AmiriB' if is_header else 'Amiri'
                                pdf_out.set_font(f_style, size=15 if is_header else 14.5)
                            except:
                                pdf_out.set_font('Arial', size=14.5)

                            pdf_out.set_text_color(220, 20, 60)
                            pdf_out.multi_cell(0, 5.5, fixed_ar, align='R')
                            
                            pdf_out.ln(1) # فراغ صغير جداً بين الفقرات
                        except: continue

        pdf_out.output(output_pdf)
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم الترجمة بنجاح لدفعة أبطال التمريض🔥\nالأحجام: إنجليزي 14 | عربي 14.5 | عنوان 15")

        doc.close()
        if os.path.exists(input_pdf): os.remove(input_pdf)
        if os.path.exists(output_pdf): os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")

bot.polling()

import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from fpdf import FPDF
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
# استبدل التوكن الخاص بك هنا
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 

bot = telebot.TeleBot(API_TOKEN)

# قاموس لحفظ بيانات الملف مؤقتاً لكل مستخدم
user_data = {}

def fix_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF للترجمة.\nالقناة المشتركة: {CHANNEL_USERNAME}")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اشترك في القناة أولاً ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        markup.add(btn)
        bot.reply_to(message, f"🚫 عذراً، يجب الاشتراك أولاً لاستخدام البوت:\n{CHANNEL_USERNAME}", reply_markup=markup)
        return

    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف بصيغة PDF فقط.")
        return

    # حفظ معلومات الملف وسؤال المستخدم عن التنسيق
    user_data[user_id] = {
        'file_id': message.document.file_id,
        'file_name': message.document.file_name
    }

    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("شكل 1: نص تحت نص (كلاسيك)", callback_data="style1")
    btn2 = telebot.types.InlineKeyboardButton("شكل 2: ترجمة فوق السطر (احترافي)", callback_data="style2")
    markup.add(btn1, btn2)

    bot.reply_to(message, "اختار شكل تنسيق الترجمة المفضل لديك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['style1', 'style2'])
def callback_query(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة أخرى.")
        return

    style = call.data
    file_id = user_data[user_id]['file_id']
    file_name = user_data[user_id]['file_name']

    bot.edit_message_text("⏳ جاري معالجة الملف واستخراج النصوص والصور...", call.message.chat.id, call.message.message_id)
    
    process_pdf(call.message, file_id, file_name, style)

def process_pdf(message, file_id, file_name, style):
    user_id = message.chat.id
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Translated_{file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        pdf_out = FPDF()
        try:
            # تأكد من رفع ملف الخط Amiri.ttf بجانب الكود
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
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            
                            if pdf_out.get_y() > 250: pdf_out.add_page()

                            if style == 'style1':
                                # التنسيق القديم
                                pdf_out.set_text_color(0, 0, 0)
                                pdf_out.multi_cell(0, 8, line, align='L')
                                pdf_out.set_text_color(220, 20, 60)
                                pdf_out.multi_cell(0, 8, fixed_ar, align='R')
                            else:
                                # التنسيق الجديد: ترجمة فوق السطر بدون تداخل
                                pdf_out.set_font_size(9)
                                pdf_out.set_text_color(120, 120, 120) # رمادي للنص الأصلي
                                pdf_out.cell(0, 6, line, ln=1, align='L')
                                pdf_out.set_font_size(12)
                                pdf_out.set_text_color(0, 0, 0) # أسود للترجمة
                                pdf_out.multi_cell(0, 7, fixed_ar, align='L')

                            pdf_out.ln(3)
                        except: continue

            # معالجة الصور
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
                    
                    if pdf_out.get_y() > 190: pdf_out.add_page()
                    pdf_out.image(img_name, w=110)
                    pdf_out.ln(5)
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

        pdf_out.output(output_pdf)
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز لدفعة أبطال التمريض🔥\nالقناة: {CHANNEL_USERNAME}")

        doc.close()
        os.remove(input_pdf)
        os.remove(output_pdf)
        if user_id in user_data: del user_data[user_id]

    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

bot.polling()

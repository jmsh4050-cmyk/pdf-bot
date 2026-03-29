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

# قاموس لحفظ بيانات الملف مؤقتاً
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

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF واختار شكل الترجمة اللي يناسبك.\nقناتنا: {CHANNEL_USERNAME}")

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

    # حفظ المعلومات وسؤال المستخدم
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("الشكل 1 (ملف جديد + صور)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("الشكل 2 (حقن فوك الأصلية + تصغير)", callback_data="style_inject")
    markup.add(btn1)
    markup.add(btn2)
    
    bot.reply_to(message, "اختار شكل الترجمة المفضل:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    style = call.data
    
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return

    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    
    if style == "style_fpdf":
        run_fpdf_style(call.message, file_info)
    else:
        run_inject_style(call.message, file_info)

# --- الطريقة الأولى: إنشاء ملف جديد (كودك الأصلي) ---
def run_fpdf_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        pdf_out = FPDF()
        try:
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.set_font('Amiri', size=11)
        except: pdf_out.set_font("Arial", size=11)

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
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 8, line, align='L')
                            pdf_out.set_text_color(220, 20, 60)
                            pdf_out.multi_cell(0, 8, fixed_ar, align='R')
                            pdf_out.ln(2)
                        except: continue
            # الصور
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 150: continue
                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    if pdf_out.get_y() > 190: pdf_out.add_page()
                    pdf_out.image(img_name, w=110)
                    pdf_out.ln(5)
                    os.remove(img_name)
                except: pass

        pdf_out.output(output_pdf)
        send_and_clean(message, output_pdf, input_pdf)
        doc.close()
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# --- الطريقة الثانية: الحقن فوق الأصلية (الكود الجديد) ---
def run_inject_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style2_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        for page in doc:
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    rect = span["bbox"]
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    eng_sz = span["size"] * 0.75
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.60
                                    page.insert_text(fitz.Point(rect[0], rect[3]), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0, 0.4, 0.8))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

def send_and_clean(message, out, inp):
    with open(out, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز لدفعة أبطال التمريض🔥")
    if os.path.exists(out): os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

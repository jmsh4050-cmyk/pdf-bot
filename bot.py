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
BOT_LINK = 'https://t.me/WSM_bot' 

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

# --- الترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    bot.reply_to(message, f"أهلاً {user_name}! أرسل ملف PDF واختار شكل الترجمة المفضل لدفعة التمريض.\nقناتنا: {CHANNEL_USERNAME}")

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

    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ شكل كلاسيك (🙂‍↔️)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (خط ناعم)", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت (منسق)", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق المطلوب حسب طلبك😊:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return

    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_fpdf_style(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- تم استبدال الشكل 1 بالكود الأول المطور ---
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
            pdf_out.add_font('AmiriB', '', 'Amiri-Bold.ttf', uni=True) 
        except: pass

        pdf_out.add_page()
        doc = fitz.open(input_pdf)
        all_processed_images = []

        for page in doc:
            # معالجة الصور الصافية مع منع التكرار
            image_list = page.get_images(full=True)
            for img in image_list:
                try:
                    xref = img[0]
                    if xref in all_processed_images: continue 
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 150 or base_image["height"] < 150: continue

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    if pdf_out.get_y() > 200: pdf_out.add_page()
                    pdf_out.image(img_name, x=45, w=100) 
                    pdf_out.ln(2)
                    all_processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # معالجة النصوص (إنجليزي 14، عربي 14.5، عنوان 15)
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            is_header = line.isupper() and len(line) < 60
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            if pdf_out.get_y() > 270: pdf_out.add_page()

                            # حل مشكلة الكراش والرموز
                            clean_eng = line.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
                            clean_eng = clean_eng.encode('cp1252', 'ignore').decode('cp1252')

                            # إنجليزي
                            pdf_out.set_font('Arial', 'B' if is_header else '', 15 if is_header else 14)
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 5.5, clean_eng, align='L')

                            # عربي
                            try:
                                f_style = 'AmiriB' if is_header else 'Amiri'
                                pdf_out.set_font(f_style, size=15 if is_header else 14.5)
                            except:
                                pdf_out.set_font('Arial', size=14.5)

                            pdf_out.set_text_color(220, 20, 60)
                            pdf_out.multi_cell(0, 5.5, fixed_ar, align='R')
                            pdf_out.ln(0.5) 
                        except: continue
        
        pdf_out.output(output_pdf)
        send_and_clean(message, output_pdf, input_pdf)
        doc.close()
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل 1: {e}")

# --- الأشكال الأخرى (من الكود الثاني) ---
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
                                    eng_sz = span["size"] * 0.70
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.50 
                                    page.insert_text(fitz.Point(rect[0], rect[3]), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0, 0.4, 0.8))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل 2: {e}")

def run_highlight_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Highlight_{file_info['file_name']}"
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
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.45 
                                    high_rect = [rect[0], rect[3] - 2, rect[2], rect[3] + ar_sz - 1]
                                    page.draw_rect(high_rect, color=(0.92, 0.96, 1), fill=(0.92, 0.96, 1))
                                    page.insert_text(fitz.Point(rect[0], high_rect[3]-0.5), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1, 0.3, 0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل 3: {e}")

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            caption_text = f"✅ تم الإنجاز (تستطيع تغير شكل الترجمة)😊🔥\n\n🔗 [اضغط هنا لدخول البوت]({BOT_LINK})"
            bot.send_document(message.chat.id, f, caption=caption_text, parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()
        

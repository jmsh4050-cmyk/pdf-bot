import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! تم تحديث البوت بالتوكن الجديد ✅\nأرسل ملف الـ PDF وسأقوم بترجمته بتنسيقك الخاص.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    user_id = message.from_user.id
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ تصميم ملزمة (إنجليزي وتحته عربي) 🖼️", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (ترجمة حمراء) 💉", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت (رفيع) 🖍️", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق المطلوب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "أرسل الملف مرة أخرى.")
        return
    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة... انتظر ثواني", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_fpdf_style_fixed(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- الشكل 1: تصميم ملزمة (نص تحت نص + صور) ---
def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 50
            
            # استخراج الصور
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 100: continue
                    img_rect = fitz.Rect(100, y_offset, 495, y_offset + 180)
                    new_page.insert_image(img_rect, stream=base_image["image"])
                    y_offset += 200
                    break 
                except: pass

            # نصوص الملزمة
            text = page.get_text("text")
            if text.strip():
                for line in text.split('\n'):
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            trans = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(trans)
                            if y_offset > 780: new_page = out_doc.new_page(); y_offset = 50
                            
                            # تنسيق الملزمة: إنجليزي ثم عربي تحته مباشرة
                            is_title = len(line) < 25
                            color_ar = (0.8, 0, 0) if is_title else (0.7, 0, 0)
                            color_en = (0.8, 0, 0) if is_title else (0, 0, 0)

                            new_page.insert_text((50, y_offset), line, fontsize=15, color=color_en)
                            y_offset += 20
                            new_page.insert_text((50, y_offset), fixed_ar, fontsize=15, fontname="f0", fontfile=font_path, color=color_ar)
                            y_offset += 30
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل 1: {e}")

# --- الشكل 2: الحقن (لون الترجمة أحمر فقط) ---
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
                                    eng_sz = span["size"] * 0.85
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.65 
                                    page.insert_text(fitz.Point(rect[0], rect[3] + ar_sz - 2), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.8, 0, 0))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل 2: {e}")

# --- الشكل 3: هايلايت رفيع ---
def run_highlight_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style3_{file_info['file_name']}"
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
                                    ar_sz = span["size"] * 0.55 
                                    high_rect = fitz.Rect(rect[0], rect[3] - 1.5, rect[2], rect[3] + ar_sz - 1) 
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
            bot.send_document(message.chat.id, f, caption="✅ تم الإنجاز!")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

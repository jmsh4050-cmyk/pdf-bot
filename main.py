import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات (سحب التوكن من Railway Variables) ---
# تأكد من إضافة BOT_TOKEN في إعدادات ريلوي
API_TOKEN = os.environ.get('BOT_TOKEN')
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    bot.reply_to(message, f"أهلاً {user_name}! 🩺\nتم تحديث البوت ليدعم التنسيق الموسط (نفس ملزمة الهرمونات).\nأرسل ملف الـ PDF الآن.")

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
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ تنسيق موسط (مثل الهرمونات)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق المفضل لديك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return
    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري تصميم الملزمة بتنسيق احترافي... انتظر ثواني", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_center_style(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- الشكل 1 المطور (توسيط كامل مثل ملزمة الهرمونات) ---
def run_center_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Center_Style_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 
        page_width = 595 

        for page in doc:
            new_page = out_doc.new_page(width=page_width, height=842)
            y_offset = 60
            
            # معالجة وتوسيط الصور
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    img_w, img_h = 360, 240
                    img_x = (page_width - img_w) / 2
                    img_rect = fitz.Rect(img_x, y_offset, img_x + img_w, y_offset + img_h)
                    new_page.insert_image(img_rect, pixmap=pix)
                    y_offset += img_h + 40
                except: pass

            # معالجة وتوسيط النصوص (نفس أسلوب الهرمون معك)
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            if y_offset > 780:
                                new_page = out_doc.new_page(width=page_width, height=842)
                                y_offset = 60

                            # إنجليزي موسط
                            eng_rect = fitz.Rect(50, y_offset, 545, y_offset + 25)
                            new_page.insert_textbox(eng_rect, line, fontsize=12, align=1)
                            y_offset += 22
                            # عربي موسط بلون أزرق طبي
                            ar_rect = fitz.Rect(50, y_offset, 545, y_offset + 25)
                            new_page.insert_textbox(ar_rect, fixed_ar, fontsize=12.5, fontname="f0", fontfile=font_path, align=1, color=(0, 0.3, 0.6))
                            y_offset += 45
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"حدث خطأ: {e}")

# --- الأشكال الأخرى (الحقن والهايلايت) ---
def run_inject_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Inject_{file_info['file_name']}"
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
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    page.insert_text(fitz.Point(rect[0], rect[1] + (span["size"]*0.7)), txt, fontsize=span["size"]*0.7, color=(0,0,0))
                                    page.insert_text(fitz.Point(rect[0], rect[3]), fixed, fontsize=span["size"]*0.5, fontname="f0", fontfile=font_path, color=(0, 0.4, 0.8))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

def run_highlight_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"High_{file_info['file_name']}"
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
                                    page.draw_rect([rect[0], rect[3], rect[2], rect[3]+ar_sz], color=(0.95, 0.95, 1), fill=(0.95, 0.95, 1))
                                    page.insert_text(fitz.Point(rect[0], rect[3]+ar_sz-1), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1, 0.3, 0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم تصميم الملزمة بنظام التوسيط الاحترافي.", parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

if __name__ == "__main__":
    bot.polling()

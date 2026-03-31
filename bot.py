import telebot
import fitz
from deep_translator import GoogleTranslator
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import os

API_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = telebot.TeleBot(API_TOKEN)
user_data = {}

CHANNEL_USERNAME = '@YourChannel'
BOT_LINK = 'https://t.me/YourBotLink'

# --- وظائف مساعدة ---
def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def contains_arabic(text):
    return any("\u0600" <= c <= "\u06FF" for c in text)

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            caption_text = f"✅تم الإنجاز\n🔗 [دخول البوت]({BOT_LINK})"
            bot.send_document(message.chat.id, f, caption=caption_text, parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

# --- الترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, f"أهلاً {user_name}! أرسل ملف PDF الآن.")

# --- استقبال الملفات ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اشترك أولاً ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        markup.add(btn)
        bot.reply_to(message, "🚫 اشترك في القناة لاستخدام البوت", reply_markup=markup)
        return

    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}

    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ الشكل الكلاسيكي", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    bot.reply_to(message, "اختر نوع التنسيق:", reply_markup=markup)

# --- اختيار النمط ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة أخرى.")
        return
    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة...", call.message.chat.id, call.message.message_id)

    if call.data == "style_fpdf":
        run_fpdf_style(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- الشكل الكلاسيكي ---
def run_fpdf_style(message, file_info):
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
        all_images = []

        new_page = out_doc.new_page()
        y_offset = 50

        for page in doc:
            # ترتيب الصور حسب الظهور وتقليل الصفحات
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in all_images: continue
                try:
                    pix = fitz.Pixmap(doc, xref)
                    new_page.insert_image(fitz.Rect(50, y_offset, 540, y_offset+280), pixmap=pix)
                    y_offset += 290
                    if y_offset > 750:
                        new_page = out_doc.new_page()
                        y_offset = 50
                    all_images.append(xref)
                except: continue

            # معالجة النصوص
            text = page.get_text("text")
            if text.strip():
                for line in text.split('\n'):
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            if y_offset > 750:
                                new_page = out_doc.new_page()
                                y_offset = 50
                            new_page.insert_text((50, y_offset), line, fontsize=14, color=(0,0,0))
                            y_offset += 18
                            new_page.insert_text((50, y_offset), fixed_ar, fontsize=14.5, fontname="f0", fontfile=font_path, color=(0.8,0,0))
                            y_offset += 25
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

# --- الشكل الثاني (كما هو) ---
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
                                    page.draw_rect(rect, color=(1,1,1), fill=(1,1,1))
                                    eng_sz = span["size"]*0.7
                                    page.insert_text(fitz.Point(rect[0], rect[1]+eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"]*0.5
                                    page.insert_text(fitz.Point(rect[0], rect[3]), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0,0.4,0.8))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e:
        bot.reply_to(message, f"خطأ في شكل الحقن: {e}")

# --- الشكل الثالث (تكبير الخط) ---
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
                                    en_sz, ar_sz = 8, 10
                                    high_rect = [rect[0], rect[3]-2, rect[2], rect[3]+ar_sz-1]
                                    page.draw_rect(high_rect, color=(0.92,0.96,1), fill=(0.92,0.96,1))
                                    page.insert_text(fitz.Point(rect[0], rect[1]), txt, fontsize=en_sz, color=(0,0,0))
                                    page.insert_text(fitz.Point(rect[0], high_rect[3]-0.5), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1,0.3,0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e:
        bot.reply_to(message, f"خطأ في شكل الهايلايت: {e}")

# --- تشغيل البوت ---
bot.polling()

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
user_data = {}

def fix_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

# --- استقبال أمر البداية ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF واختار شكل الترجمة المفضل لدفعة التمريض.\nقناتنا: {CHANNEL_USERNAME}")

# --- استقبال الملفات ---
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
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ شكل كلاسيك (ملف جديد)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (تصغير وصافي)", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت (بدون تداخل)", callback_data="style_high")
    btn4 = telebot.types.InlineKeyboardButton("4️⃣ شكل احترافي (أعمدة + تظليل عناوين)", callback_data="style_pro")
    markup.add(btn1, btn2)
    markup.add(btn3)
    markup.add(btn4)
    
    bot.reply_to(message, "اختار نوع التنسيق المطلوب:", reply_markup=markup)

# --- معالجة اختيار المستخدم ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    style = call.data
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return

    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة بدقة عالية... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    
    if style == "style_fpdf": run_fpdf_style(call.message, file_info)
    elif style == "style_inject": run_inject_style(call.message, file_info)
    elif style == "style_high": run_highlight_style(call.message, file_info)
    else: run_professional_style(call.message, file_info)

# --- الدوال الخاصة بالأشكال 1 و 2 و 3 (كما كانت سابقاً) ---
# [يمكنك نسخ الدوال run_fpdf_style, run_inject_style, run_highlight_style من الكود السابق ولصقها هنا]
# ... [الدوال القديمة] ...

# --- [الشكل 4: الشكل الاحترافي (أعمدة + تظليل عناوين) - الجديد] ---
def run_professional_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Professional_{file_info['file_name']}"
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
                                    rect = span["bbox"] # [x0, y0, x1, y1]
                                    page_width = page.rect.width
                                    page_height = page.rect.height
                                    column_width = page_width / 2.2 # تقسيم الصفحة لعمودين

                                    # ترجمة العربي
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed_ar = fix_arabic(trans)
                                    
                                    # تحديد إذا كانت الجملة عنواناً رئيسياً (Nursing, Care, Diagnosis, Risk)
                                    is_main_header = any(keyword in txt for keyword in ["Nursing", "Care", "Diagnosis", "Risk", "Wound", "Related"])
                                    # تحديد النقاط الفرعية (1. , 2. , ...)
                                    is_sub_header = txt[0].isdigit() and txt[1] == '.' if len(txt) > 1 else False

                                    # --- 1. مسح النص الأصلي تماماً ---
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    
                                    # --- 2. رسم خلفية رمادية للعناوين الرئيسية (هايلايت) ---
                                    if is_main_header:
                                        page.draw_rect(rect, color=(0.94, 0.94, 0.94), fill=(0.94, 0.94, 0.94))
                                    
                                    # --- 3. تحديد تنسيقات الخطوط (الحجم واللون) ---
                                    eng_font_size = span["size"]
                                    ar_font_size = span["size"] * 0.85 # العربي أصغر قليلاً

                                    if is_main_header:
                                        eng_color = (0, 0, 0) # أسود للعنوان الرئيسي
                                        ar_color = (0.6, 0.1, 0.1) # أحمر غامق للعربي المقابل
                                    elif is_sub_header:
                                        eng_color = (0, 0, 0.5) # أزرق غامق للنقاط
                                        ar_color = (0, 0, 0.5)
                                    else:
                                        eng_color = (0, 0, 0) # أسود للنص العادي
                                        ar_color = (0.2, 0.2, 0.2) # رمادي غامق للعربي العادي

                                    # --- 4. حقن النص الإنكليزي (العمود الأيسر) ---
                                    # نستخدم Multi-cell لتوزيع النص داخل العمود
                                    page.insert_textbox(
                                        fitz.Rect(rect[0], rect[1], column_width, rect[3]),
                                        txt,
                                        fontsize=eng_font_size,
                                        color=eng_color,
                                        align=fitz.TEXT_ALIGN_LEFT
                                    )
                                    
                                    # --- 5. حقن النص العربي (العمود الأيمن) ---
                                    page.insert_textbox(
                                        fitz.Rect(page_width - column_width, rect[1], column_width - rect[0], rect[3]),
                                        fixed_ar,
                                        fontsize=ar_font_size,
                                        fontname="f0", 
                                        fontfile=font_path,
                                        color=ar_color,
                                        align=fitz.TEXT_ALIGN_RIGHT
                                    )
                                    
                                except: continue
        
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: 
        bot.reply_to(message, f"خطأ في الشكل الاحترافي: {str(e)}")

# --- دالة الإرسال والتنظيف (كما كانت سابقاً) ---
def send_and_clean(message, out, inp):
    with open(out, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز بدقة عالية لدفعة أبطال التمريض🔥\nقناتنا: {CHANNEL_USERNAME}")
    if os.path.exists(out): os.remove(out)
    if os.path.exists(inp): os.remove(inp)

# --- تشغيل البوت ---
bot.polling()

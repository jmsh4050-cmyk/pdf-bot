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
    btn4 = telebot.types.InlineKeyboardButton("4️⃣ شكل احترافي (أعمدة + تظليل عناوين - مصحح)", callback_data="style_pro")
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
    bot.edit_message_text("⏳ جاري المعالجة بدقة عالية لدفعة التمريض... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    
    if style == "style_fpdf": run_fpdf_style(call.message, file_info)
    elif style == "style_inject": run_inject_style(call.message, file_info)
    elif style == "style_high": run_highlight_style(call.message, file_info)
    else: run_professional_style(call.message, file_info)

# --- الدوال القديمة (run_fpdf_style, run_inject_style, run_highlight_style) تُنسخ هنا دون تعديل ---
# ... [الدوال القديمة] ...

# --- [الشكل 4 الاحترافي (المصحح)] ---
def run_professional_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style4_Clean_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        
        for page in doc:
            dict_text = page.get_text("dict")
            # --- 1. مسح النص الأصلي بالكامل أولاً لضمان النظافة ---
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                # مسح فقط نصوص الإنكليزي
                if not contains_arabic(block[4]) and len(block[4].strip()) > 2:
                    page.draw_rect(block[:4], color=(1, 1, 1), fill=(1, 1, 1))

            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    rect = span["bbox"] # إحداثيات النص الأصلي
                                    page_width = page.rect.width
                                    
                                    # --- 2. تحديد أنظف للأعمدة ---
                                    column_width = page_width / 2.5 # جعل الأعمدة أصغر شوية
                                    gap = 20 # فراغ أمان بين العمودين

                                    # --- 3. ترجمة العربي ---
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed_ar = fix_arabic(trans)
                                    
                                    # تحديد تنسيقات العناوين
                                    is_main_header = any(keyword in txt for keyword in ["Nursing", "Care", "Diagnosis", "Risk", "Wound", "Related"])
                                    is_sub_header = txt[0].isdigit() and txt[1] == '.' if len(txt) > 1 else False

                                    # --- 4. تخطيط مساحة الكتابة النظيفة (التصحيح الرئيسي) ---
                                    # نستخدم Multi-cell لتوزيع النص، ولكن نترك مساحة أكبر شوية
                                    eng_sz = span["size"] * 0.90
                                    ar_sz = span["size"] * 0.75 # العربي أصغر قليلاً

                                    if is_main_header:
                                        # تظليل رمادي للعناوين الرئيسية
                                        header_rect = fitz.Rect(rect[0], rect[1]-1, page_width, rect[3]+1)
                                        page.draw_rect(header_rect, color=(0.95, 0.95, 0.95), fill=(0.95, 0.95, 0.95))
                                        eng_color = (0, 0, 0) # أسود للإنكليزي
                                        ar_color = (0.6, 0.1, 0.1) # أحمر غامق للعربي
                                    elif is_sub_header:
                                        eng_color = (0, 0, 0.5) # أزرق غامق للنقاط
                                        ar_color = (0, 0, 0.5)
                                    else:
                                        eng_color = (0, 0, 0) # أسود للنص العادي
                                        ar_color = (0.2, 0.2, 0.2) # رمادي غامق للعربي

                                    # --- 5. حقن النص الإنكليزي (العمود الأيسر) ---
                                    eng_frame = fitz.Rect(rect[0], rect[1], column_width, rect[3])
                                    page.insert_textbox(
                                        eng_frame,
                                        txt,
                                        fontsize=eng_sz,
                                        color=eng_color,
                                        align=fitz.TEXT_ALIGN_LEFT
                                    )
                                    
                                    # --- 6. حقن النص العربي (العمود الأيمن) مع ترك gap ---
                                    ar_frame = fitz.Rect(column_width + gap, rect[1], page_width - gap, rect[3])
                                    page.insert_textbox(
                                        ar_frame,
                                        fixed_ar,
                                        fontsize=ar_sz,
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
        bot.reply_to(message, f"خطأ في الشكل الاحترافي المصحح: {str(e)}\nتأكد من وجود ملف Amiri.ttf")

# --- دالة الإرسال والتنظيف القديمة تُنسخ هنا دون تعديل ---
# ... [دالة send_and_clean القديمة] ...

# --- تشغيل البوت ---
bot.polling()
                                   

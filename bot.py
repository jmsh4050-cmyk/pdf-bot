import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# --- الدوال المساعدة ---
def fix_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def send_and_clean(message, out, inp):
    with open(out, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"✅ تم الترتيب بالتسلسل لدفعة أبطال التمريض🔥")
    if os.path.exists(out): os.remove(out)
    if os.path.exists(inp): os.remove(inp)

# --- [الشكل الرابع: الترتيب الاحترافي المتسلسل] ---
def run_professional_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Pro_Ordered_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        
        for page in doc:
            # 1. مسح الصفحة بالكامل لضمان عدم وجود تداخل (Clean Slate)
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    page.draw_rect(b["bbox"], color=(1, 1, 1), fill=(1, 1, 1))

            # 2. إعادة توزيع النص (إنكليزي يسار - عربي يمين) مع تمييز العناوين
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    rect = span["bbox"]
                                    mid = page.rect.width / 2
                                    
                                    # الترجمة الاحترافية
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed_ar = fix_arabic(trans)
                                    
                                    # كشف العناوين (Headers) والنقاط (1. 2. 3.)
                                    is_main = any(k in txt.upper() for k in ["NURSING", "DIAGNOSIS", "MANAGEMENT", "RISK"])
                                    is_numbered = txt[0].isdigit() and ('.' in txt[:3] or ')' in txt[:3])

                                    # إعدادات الشكل (الألوان والأحجام)
                                    if is_main:
                                        # تظليل العنوان الرئيسي مثل الصورة
                                        bg_rect = fitz.Rect(10, rect[1]-2, page.rect.width-10, rect[3]+2)
                                        page.draw_rect(bg_rect, color=(0.93, 0.93, 0.93), fill=(0.93, 0.93, 0.93))
                                        e_color, a_color = (0, 0, 0), (0.7, 0, 0) # أحمر غامق للعربي
                                        f_size = span["size"]
                                    elif is_numbered:
                                        e_color, a_color = (0, 0, 0.6), (0, 0, 0.6) # أزرق للنقاط
                                        f_size = span["size"] * 0.9
                                    else:
                                        e_color, a_color = (0.1, 0.1, 0.1), (0.2, 0.2, 0.2)
                                        f_size = span["size"] * 0.85

                                    # حقن النص بترتيب متوازي (نظام الأعمدة)
                                    # العمود الأيسر: إنكليزي
                                    page.insert_textbox(fitz.Rect(15, rect[1], mid-10, rect[3]+10), 
                                                        txt, fontsize=f_size, color=e_color, align=0)
                                    
                                    # العمود الأيمن: عربي (مقابل تماماً للسطر الإنكليزي)
                                    page.insert_textbox(fitz.Rect(mid+10, rect[1], page.rect.width-15, rect[3]+10), 
                                                        fixed_ar, fontsize=f_size*0.9, fontname="f0", 
                                                        fontfile=font_path, color=a_color, align=2)
                                except: continue
        
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: 
        bot.reply_to(message, f"حدث خطأ في الترتيب: {str(e)}")

# --- Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أهلاً وسام! أرسل ملف الـ PDF لترجمته بالشكل الاحترافي الجديد.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, f"اشترك أولاً بـ {CHANNEL_USERNAME}")
        return
    user_data[message.from_user.id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("الشكل 4: الترتيب المتسلسل ✅", callback_data="run_pro"))
    bot.reply_to(message, "تم استلام الملف، اضغط للبدء بالترجمة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "run_pro")
def callback_handler(call):
    bot.edit_message_text("⏳ جاري إعادة بناء الصفحة وترجمتها بالتسلسل...", call.message.chat.id, call.message.message_id)
    run_professional_style(call.message, user_data[call.from_user.id])

bot.polling()

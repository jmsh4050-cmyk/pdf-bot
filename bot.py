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
        bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز لدفعة أبطال التمريض🔥")
    if os.path.exists(out): os.remove(out)
    if os.path.exists(inp): os.remove(inp)

# --- الشكل 4: التصميم الاحترافي الصافي ---
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
            # --- الخطوة 1: مسح كل النصوص الموجودة في الصفحة لضمان عدم التداخل ---
            text_instances = page.get_text("dict")["blocks"]
            for block in text_instances:
                if "lines" in block:
                    page.draw_rect(block["bbox"], color=(1, 1, 1), fill=(1, 1, 1))

            # --- الخطوة 2: إعادة بناء النص المترجم في أعمدة ---
            for block in text_instances:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    rect = span["bbox"]
                                    mid_x = page.rect.width / 2
                                    
                                    # الترجمة
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed_ar = fix_arabic(trans)
                                    
                                    # تمييز العناوين (تظليل خفيف)
                                    is_header = any(k in txt.lower() for k in ["nursing", "diagnosis", "risk", "physiology", "system"])
                                    if is_header:
                                        header_bg = fitz.Rect(0, rect[1]-2, page.rect.width, rect[3]+2)
                                        page.draw_rect(header_bg, color=(0.96, 0.96, 0.96), fill=(0.96, 0.96, 0.96))

                                    # حقن النص - عمود يسار (إنكليزي) وعمود يمين (عربي)
                                    # الإنكليزي
                                    page.insert_textbox(
                                        fitz.Rect(20, rect[1], mid_x - 10, rect[3] + 5),
                                        txt, fontsize=span["size"] * 0.85, color=(0, 0, 0), align=0
                                    )
                                    # العربي
                                    page.insert_textbox(
                                        fitz.Rect(mid_x + 10, rect[1], page.rect.width - 20, rect[3] + 5),
                                        fixed_ar, fontsize=span["size"] * 0.75, 
                                        fontname="f0", fontfile=font_path, color=(0, 0, 0), align=2
                                    )
                                except: continue
        
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: 
        bot.reply_to(message, f"خطأ في الشكل 4: {e}")

# --- باقي أجزاء البوت (Handlers) ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أهلاً وسام! أرسل ملف PDF للترجمة.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك بالقناة أولاً.")
        return
    user_data[message.from_user.id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("الشكل الرابع (الاحترافي)", callback_data="s_4"))
    bot.reply_to(message, "اختار التنسيق:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "s_4")
def callback_query(call):
    bot.edit_message_text("⏳ جاري تنظيف الصفحة وترجمتها...", call.message.chat.id, call.message.message_id)
    run_professional_style(call.message, user_data[call.from_user.id])

bot.polling()

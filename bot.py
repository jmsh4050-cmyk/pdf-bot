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
        bot.send_document(message.chat.id, f, caption=f"✅ تم الترتيب المتسلسل بنجاح لدفعة التمريض🔥")
    if os.path.exists(out): os.remove(out)
    if os.path.exists(inp): os.remove(inp)

# --- الشكل الرابع المطور: نظام الترتيب العمودي المنسق ---
def run_professional_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Ordered_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        
        for page in doc:
            # الحصول على كل النصوص في الصفحة مرتبة من الأعلى للأسفل
            text_blocks = page.get_text("blocks")
            text_blocks.sort(key=lambda b: b[1]) # ترتيب حسب الارتفاع (Y)
            
            # مسح الصفحة بالكامل لضمان النظافة
            page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            current_y = 40 # نقطة البداية من أعلى الصفحة
            margin = 30
            line_height = 25

            for block in text_blocks:
                txt = block[4].strip()
                if len(txt) > 2 and not contains_arabic(txt):
                    try:
                        # الترجمة
                        trans = GoogleTranslator(source='en', target='ar').translate(txt)
                        fixed_ar = fix_arabic(trans)
                        
                        # كشف العناوين (Nursing Interventions, Wound Care, etc)
                        is_header = any(k in txt.upper() for k in ["NURSING", "RISK", "DIABETIC", "CARE", "DIAGNOSIS"])
                        is_numbered = txt[0].isdigit() and ('.' in txt[:3])

                        # 1. طباعة النص الإنكليزي
                        f_size = 12 if is_header else 10
                        color = (0, 0, 0) if not is_numbered else (0, 0, 0.5) # أزرق للنقاط
                        
                        if is_header:
                            # رسم خلفية للعنوان
                            header_rect = fitz.Rect(margin-5, current_y-2, page.rect.width-margin+5, current_y + line_height)
                            page.draw_rect(header_rect, color=(0.95, 0.95, 0.95), fill=(0.95, 0.95, 0.95))

                        page.insert_text(fitz.Point(margin, current_y + 12), txt, fontsize=f_size, color=color)
                        current_y += line_height

                        # 2. طباعة النص العربي (تحته مباشرة)
                        ar_color = (0.6, 0.1, 0.1) if is_header else (0.2, 0.2, 0.2)
                        page.insert_text(fitz.Point(page.rect.width - margin, current_y + 12), 
                                         fixed_ar, fontsize=f_size, fontname="f0", fontfile=font_path, 
                                         color=ar_color, align=2)
                        
                        current_y += line_height + 10 # مسافة بين الفقرات
                        
                        # التأكد من عدم الخروج من الصفحة
                        if current_y > page.rect.height - 50:
                            break 
                    except: continue
        
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: 
        bot.reply_to(message, f"خطأ في التنسيق المتسلسل: {e}")

# --- Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أرسل الملف واختار الشكل الرابع الجديد.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك بالقناة أولاً.")
        return
    user_data[message.from_user.id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("الشكل 4 (الترتيب المتسلسل الجديد)", callback_data="s_4"))
    bot.reply_to(message, "اختار التنسيق:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "s_4")
def callback_query(call):
    bot.edit_message_text("⏳ جاري إعادة ترتيب الصفحة والترجمة...", call.message.chat.id, call.message.message_id)
    run_professional_style(call.message, user_data[call.from_user.id])

bot.polling()

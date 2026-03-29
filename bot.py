import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    bot.reply_to(message, f"أهلاً {user_name}! تم تصغير الصور وتجاهل اللوغو في الشكل الأول ✅")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        # ... (كود الاشتراك)
        return
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("1️⃣ الشكل الكلاسيكي (صور أصغر + صفحات أقل)", callback_data="style_fpdf"))
    markup.add(telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن", callback_data="style_inject"), 
               telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت", callback_data="style_high"))
    bot.reply_to(message, "اختار التنسيق:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    file_info = user_data.get(user_id)
    if not file_info: return
    bot.edit_message_text("⏳ جاري المعالجة (تنسيق الصور والصفحات)...", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_fpdf_style_fixed(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_Compact_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf"
        all_processed_images = []

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 50
            
            # معالجة الصور (تصغير الحجم وتجاهل اللوغو)
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in all_processed_images: continue
                try:
                    pix = fitz.Pixmap(doc, xref)
                    # تجاهل اللوغو (أي صورة أبعادها صغيرة جداً أقل من 100 بكسل)
                    if pix.width < 100 or pix.height < 100:
                        continue

                    # تصغير حجم الصورة للمتوسط (عرض 350 بكسل وارتفاع 180) لتقليل عدد الصفحات
                    img_rect = fitz.Rect(120, y_offset, 470, y_offset + 180)
                    new_page.insert_image(img_rect, pixmap=pix)
                    y_offset += 200 # مسافة معقولة لتقليل الفراغات
                    all_processed_images.append(xref)
                except: pass

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
                                new_page = out_doc.new_page()
                                y_offset = 50

                            new_page.insert_text((50, y_offset), line, fontsize=14, color=(0,0,0))
                            y_offset += 20
                            new_page.insert_text((50, y_offset), fixed_ar, fontsize=14.5, fontname="f0", fontfile=font_path, color=(0.8, 0, 0))
                            y_offset += 32
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# دوال run_inject_style و run_highlight_style و send_and_clean تبقى كما هي في كودك الأساسي
def run_inject_style(message, file_info):
    # ... (نفس كود الحقن الخاص بك بدون تغيير)
    pass

def run_highlight_style(message, file_info):
    # ... (نفس كود الهايلايت الخاص بك بدون تغيير)
    pass

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز لدفعة التمريض🔥\n🔗 [دخول البوت]({BOT_LINK})", parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

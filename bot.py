import telebot
import fitz  # المكتبة الأساسية والمستقرة
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً وسام! تم تحديث البوت ليكون مضاداً للكراش وموفراً للصفحات لدفعة التمريض ✅")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        # كود الاشتراك...
        return
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("1️⃣ شكل كلاسيك (مضغوط 🛡️)", callback_data="style_fpdf"))
    markup.add(telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن", callback_data="style_inject"))
    markup.add(telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت", callback_data="style_high"))
    bot.reply_to(message, "اختار التنسيق المطور:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    file_info = user_data.get(user_id)
    if not file_info: return
    bot.edit_message_text("⏳ جاري المعالجة بدون كراش...", call.message.chat.id, call.message.message_id)
    
    # كل الأشكال الآن تعمل بـ fitz لضمان الاستقرار
    if call.data == "style_fpdf":
        run_style_classic_fixed(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- الشكل الأول المطور (بديل FPDF الفاشل) ---
def run_style_classic_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Compact_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 
        processed_imgs = []

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 40
            
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in processed_imgs: continue
                pix = fitz.Pixmap(doc, xref)
                if pix.width < 100 or pix.height < 100: continue # تجاهل اللوجو
                
                # تصغير الصورة لتوفير صفحات
                rect = fitz.Rect(120, y_offset, 470, y_offset + 170)
                new_page.insert_image(rect, pixmap=pix)
                y_offset += 185
                processed_imgs.append(xref)

            text = page.get_text("text")
            for line in text.split('\n'):
                line = line.strip()
                if len(line) > 3:
                    if y_offset > 790:
                        new_page = out_doc.new_page()
                        y_offset = 40
                    
                    trans = GoogleTranslator(source='en', target='ar').translate(line)
                    new_page.insert_text((50, y_offset), line, fontsize=12, color=(0,0,0))
                    y_offset += 18
                    new_page.insert_text((50, y_offset), fix_arabic(trans), fontsize=12.5, fontname="f0", fontfile=font_path, color=(0.8, 0, 0))
                    y_offset += 28

        out_doc.save(output_pdf)
        out_doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# ... (باقي الدوال run_inject و run_highlight تبقى كما هي لأنها مستقرة)
def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز لدفعة التمريض🔥")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

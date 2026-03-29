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
BOT_LINK = 'https://t.me/WSM_bot' # رابط البوت المباشر

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
    user_name = message.from_user.first_name
    bot.reply_to(message, f"أهلاً {user_name}! أرسل ملف PDF واختار شكل الترجمة المفضل لدفعة التمريض.\nقناتنا: {CHANNEL_USERNAME}")

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
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ شكل كلاسيك (دعم الصور + موفر)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (خط ناعم)", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت (منسق)", callback_data="style_high")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق المطلوب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return

    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة ودعم الصور... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_fpdf_style(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- الشكل 1 المعدل (دعم الصور + حل الصفحات الفارغة) ---
def run_fpdf_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Translated_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        pdf_out = FPDF()
        try:
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.add_font('AmiriB', '', 'Amiri-Bold.ttf', uni=True)
        except: pass

        doc = fitz.open(input_pdf)
        for page_index in range(len(doc)):
            pdf_out.add_page()
            page = doc[page_index]
            
            # استخراج الصور من الصفحة الأصلية ووضعها في المترجمة
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    img_name = f"temp_img_{user_id}_{page_index}_{img_index}.png"
                    with open(img_name, "wb") as f: f.write(image_bytes)
                    
                    # وضع الصورة بشكل تلقائي في وسط الصفحة
                    pdf_out.image(img_name, x=50, w=110)
                    os.remove(img_name)
                except: pass

            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            clean_line = line.encode('latin-1', 'ignore').decode('latin-1')
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            
                            if pdf_out.get_y() > 250: pdf_out.add_page()
                            
                            is_header = line.isupper() and len(line) < 50
                            
                            # نصوص إنكليزية 14
                            pdf_out.set_font('Arial', 'B' if is_header else '', 15.5 if is_header else 14)
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 8, clean_line, align='L')
                            
                            # نصوص عربية 15
                            try: pdf_out.set_font('AmiriB' if is_header else 'Amiri', size=15)
                            except: pdf_out.set_font('Arial', size=15)
                            pdf_out.set_text_color(200, 0, 0) if is_header else pdf_out.set_text_color(60, 60, 60)
                            pdf_out.multi_cell(0, 8, fixed_ar, align='R')
                            pdf_out.ln(2)
                        except: continue
            
            # إضافة التوقيع كرابط في أسفل كل صفحة بدون إجبار صفحة جديدة
            pdf_out.set_y(-15)
            pdf_out.set_font('Arial', 'U', 9)
            pdf_out.set_text_color(0, 0, 255)
            pdf_out.cell(0, 10, "Click here to open the bot | اضغط هنا لفتح البوت", link=BOT_LINK, align='C')

        pdf_out.output(output_pdf)
        send_and_clean(message, output_pdf, input_pdf)
        doc.close()
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# --- الأشكال الأخرى تبقى كما هي مع تحديث التوقيع ---
def run_inject_style(message, file_info):
    # نفس الكود السابق مع استبدال النص بـ "اضغط هنا" ورابط BOT_LINK
    pass # (يتم تطبيقه بنفس الطريقة)

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم الإنجاز لدفعة التمريض.\n🔗 [اضغط هنا لفتح البوت]({BOT_LINK})", parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

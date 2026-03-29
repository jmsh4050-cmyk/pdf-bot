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
    bot.reply_to(message, f"أهلاً {user_name}! أرسل ملف PDF للترجمة المكثفة لدفعة التمريض.\nقناتنا: {CHANNEL_USERNAME}")

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
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ الشكل الكلاسيكي (بدون فراغات + سميك)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ الشكل الثاني (بدون تغيير)", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ الشكل الثالث (بدون تغيير)", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق المطلوب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return

    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة المكثفة... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_fpdf_style(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- الشكل 1 المعدل والآمن من الكراش ---
def run_fpdf_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        pdf_out = FPDF()
        try:
            pdf_out.add_font('Amiri', '', 'Amiri.ttf', uni=True)
            pdf_out.add_font('AmiriB', '', 'Amiri-Bold.ttf', uni=True) 
        except: pass

        doc = fitz.open(input_pdf)
        for page in doc:
            pdf_out.add_page()
            
            # استخراج الصور الصافية
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 150 or base_image["height"] < 150: continue

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    if pdf_out.get_y() > 200: pdf_out.add_page()
                    pdf_out.image(img_name, x=45, w=100) 
                    pdf_out.ln(2) 
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 2:
                        try:
                            # كشف العناوين (Bold)
                            is_header = line.isupper() and len(line) < 65
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            
                            if pdf_out.get_y() > 278: pdf_out.add_page()
                            
                            # تنظيف النص الإنجليزي لتجنب كراش الترميز
                            clean_eng = line.encode('cp1252', 'ignore').decode('cp1252')
                            
                            # تنسيق إنجليزي (مسافة 5.0 لضغط الفراغ)
                            pdf_out.set_font('Arial', 'B' if is_header else '', 15.5 if is_header else 14)
                            pdf_out.set_text_color(0, 0, 0)
                            pdf_out.multi_cell(0, 5.0, clean_eng, align='L')
                            
                            # تنسيق عربي (مسافة 5.0 لضغط الفراغ)
                            try:
                                f_style = 'AmiriB' if is_header else 'Amiri'
                                pdf_out.set_font(f_style, size=15.5 if is_header else 15)
                            except:
                                pdf_out.set_font('Arial', size=15)
                                
                            pdf_out.set_text_color(220, 20, 60) if is_header else pdf_out.set_text_color(50, 50, 50)
                            pdf_out.multi_cell(0, 5.0, fixed_ar, align='R')
                            
                            pdf_out.ln(0.3) # فراغ شبه منعدم
                        except: continue
        
        pdf_out.output(output_pdf)
        send_and_clean(message, output_pdf, input_pdf)
        doc.close()
    except Exception as e: bot.reply_to(message, f"خطأ في المعالجة: {e}")

def run_inject_style(message, file_info):
    # كود الشكل الثاني الخاص بك يوضع هنا
    pass

def run_highlight_style(message, file_info):
    # كود الشكل الثالث الخاص بك يوضع هنا
    pass

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            caption_text = f"✅ تم الإنجاز لدفعة أبطال التمريض🔥\n\n🔗 [اضغط هنا لدخول البوت]({BOT_LINK})"
            bot.send_document(message.chat.id, f, caption=caption_text, parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

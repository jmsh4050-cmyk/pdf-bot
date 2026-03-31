import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai  # مكتبة جمناي الجديدة

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 
BOT_LINK = 'https://t.me/WSM_bot' 
  
# --- إعداد ذكاء Gemini المحمي ---
# هنا سحبنا المفتاح من "الخزنة" في Railway وليس كتابةً
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # نستخدم هذا الاسم لضمان استقرار الخدمة في العراق
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("⚠️ فشل في العثور على المفتاح السري!")


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

# --- الترحيب ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    bot.reply_to(message, f"أهلاً {user_name}! تم تفعيل ذكاء Gemini للاختبارات + الترجمة الاحترافية ✅\nأرسل ملف الـ PDF الآن.")

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
    # إضافة زر الاختبار الجديد
    btn_quiz = telebot.types.InlineKeyboardButton("📝 صنع اختبار ذكي (Gemini)", callback_data="style_quiz")
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ الشكل الكلاسيكي (🌝)", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت", callback_data="style_high")
    
    markup.add(btn_quiz) # وضعت زر الاختبار في البداية ليكون واضحاً
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار ما تريد فعله بالمحاضرة 😊:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return
    file_info = user_data[user_id]
    
    if call.data == "style_quiz":
        bot.edit_message_text("⏳ جاري تحليل المحاضرة وصنع الأسئلة بواسطة Gemini...", call.message.chat.id, call.message.message_id)
        run_gemini_quiz(call.message, file_info)
    else:
        bot.edit_message_text("⏳ جاري المعالجة الاحترافية... انتظر ثواني", call.message.chat.id, call.message.message_id)
        if call.data == "style_fpdf":
            run_fpdf_style_fixed(call.message, file_info)
        elif call.data == "style_inject":
            run_inject_style(call.message, file_info)
        else:
            run_highlight_style(call.message, file_info)

# --- دالة الاختبارات الذكية (Gemini) الجديدة ---
def run_gemini_quiz(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        temp_pdf = f"quiz_in_{user_id}.pdf"
        with open(temp_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(temp_pdf)
        text_content = ""
        # نأخذ أول 4 صفحات فقط لضمان سرعة الاستجابة ودقتها
        for page in doc[:4]:
            text_content += page.get_text()
        doc.close()
        os.remove(temp_pdf)

        # طلب توليد الأسئلة من جمناي
        prompt = f"Create 3 medical MCQs for nursing students from this text. Format: Question|A,B,C,D|CorrectIndex(0-3). Text: {text_content[:3000]}"
        response = model.generate_content(prompt)
        
        # إرسال الأسئلة كتصويت (Poll)
        lines = response.text.strip().split('\n')
        for line in lines:
            if '|' in line:
                try:
                    parts = line.split('|')
                    q_text = parts[0]
                    options = parts[1].split(',')
                    correct_idx = int(parts[2])
                    bot.send_poll(user_id, q_text, options, correct_option_id=correct_idx, type='quiz', is_anonymous=False)
                except: continue
                
    except Exception as e:
        bot.send_message(user_id, f"❌ حدث خطأ في صنع الاختبار: {e}")

# --- الأكواد الأصلية للترجمة (بدون أي تغيير) ---
def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_Fixed_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf"
        all_processed_images = []

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 50
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in all_processed_images: continue
                try:
                    pix = fitz.Pixmap(doc, xref)
                    img_rect = fitz.Rect(50, y_offset, 540, y_offset + 280)
                    new_page.insert_image(img_rect, pixmap=pix)
                    y_offset += 300
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
                            y_offset += 35
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"حدث خطأ غير متوقع: {e}")

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
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    eng_sz = span["size"] * 0.70
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.50 
                                    page.insert_text(fitz.Point(rect[0], rect[3]), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0, 0.4, 0.8))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الحقن: {e}")

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
                                    ar_sz = span["size"] * 0.45 
                                    high_rect = [rect[0], rect[3] - 2, rect[2], rect[3] + ar_sz - 1]
                                    page.draw_rect(high_rect, color=(0.92, 0.96, 1), fill=(0.92, 0.96, 1))
                                    page.insert_text(fitz.Point(rect[0], high_rect[3]-0.5), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1, 0.3, 0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الهايلايت: {e}")

def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            caption_text = f"✅تم الإنجاز(تستطيع تغير شكل الترجمة)🔥\n🔗 [دخول البوت]({BOT_LINK})"
            bot.send_document(message.chat.id, f, caption=caption_text, parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()
                

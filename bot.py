import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
# التوكن الخاص ببوتك
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
    if not text: return False
    # التحقق من نطاق الحروف العربية في Unicode
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    welcome_text = (
        f"أهلاً {user_name}! تم تحديث التنسيقات وإضافة الصور بنجاح ✅\n\n"
        "أرسل لي ملف PDF، وسأقوم بترجمته إلى العربية والحفاظ على التنسيق قدر الإمكان.\n"
        "(تأكد من اختيار التنسيق المناسب لك بعد إرسال الملف)."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # 1. التحقق من الاشتراك في القناة
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اشترك في القناة أولاً ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        markup.add(btn)
        bot.reply_to(message, f"🚫 عذراً، يجب الاشتراك في القناة لاستخدام البوت:\n{CHANNEL_USERNAME}", reply_markup=markup)
        return

    # 2. التحقق من أن الملف هو PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "⚠️ عذراً، هذا البوت يدعم ملفات PDF فقط.")
        return

    # حفظ معلومات الملف في الذاكرة
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    
    # إنشاء قائمة الأزرار لاختيار التنسيق
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ الكلاسيكي (مع الصور) 🖼️", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (تحت الخط) 💉", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت 🖍️", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق حسب ماتحب😊:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أرسل الملف مرة ثانية.")
        return
    file_info = user_data[user_id]
    
    # إرسال رسالة حالة للمستخدم وتحديثها
    bot.edit_message_text("⏳ جاري المعالجة الاحترافية... انتظر ثواني", call.message.chat.id, call.message.message_id)
    
    # تشغيل التنسيق المطلوب بناءً على اختيار المستخدم
    if call.data == "style_fpdf":
        run_fpdf_style_fixed(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- دالة الإرسال وتنظيف الملفات المؤقتة ---
def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            caption_text = f"✅ تم الإنجاز.. جرب التنسيقات الأخرى 🔥\n🔗 [دخول البوت]({BOT_LINK})"
            bot.send_document(message.chat.id, f, caption=caption_text, parse_mode="Markdown")
        # حذف الملف الناتج بعد الإرسال
        os.remove(out)
    # حذف الملف الأصلي الذي تم تحميله
    if os.path.exists(inp):
        os.remove(inp)

# ==============================================================================
# --- التعديلات المطلوبة في التنسيقات الثلاثة ---
# ==============================================================================

# --- الشكل 1: المُعدَّل (أحجام خطوط جديدة، عناوين ثخينة) ---
def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_WithImages_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 
        
        # --- التعديل: تعريف ملف الخط الثخين ---
        # يجب أن يكون هذا الملف مرفوعاً على المشروع بجانب 'Amiri.ttf'
        font_bold_path = "Amiri-Bold.ttf" 

        translator = GoogleTranslator(source='auto', target='ar')

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 50
            
            # 1. استخراج الصور ووضعها أولاً
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    # تجاهل الأيقونات واللوجوهات الصغيرة (أقل من 120 بكسل)
                    if base_image["width"] < 120 or base_image["height"] < 120: continue

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    if y_offset > 500: # إذا امتلات صفحة بالصور، نفتح صفحة جديدة
                        new_page = out_doc.new_page()
                        y_offset = 50
                    
                    img_rect = fitz.Rect(70, y_offset, 500, y_offset + 250)
                    new_page.insert_image(img_rect, filename=img_name, keep_proportion=True)
                    y_offset += 270
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # 2. استخراج النصوص، ترجمتها، ووضعها بأحجام الخطوط الجديدة
            # نستخدم "dict" بدلاً من "text" للحصول على معلومات الخط الأصلي وحجمه
            text_blocks = page.get_text("dict")["blocks"]
            if text_blocks:
                for block in text_blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            clean_line = ""
                            # تجميع النص من السبانز (spans) للحصول على السطر الكامل
                            for span in line["spans"]:
                                clean_line += span["text"]
                            
                            clean_line = clean_line.strip()
                            if len(clean_line) > 3:
                                try:
                                    translated = translator.translate(clean_line)
                                    fixed_ar = fix_arabic(translated)
                                    
                                    # التحقق من المساحة العمودية المتبقية
                                    if y_offset > 750: 
                                        new_page = out_doc.new_page()
                                        y_offset = 50

                                    # --- التعديل: تحديد أحجام الخطوط ونوعها (Bold) ---
                                    # سنعتبر السطور القصيرة جداً (أقل من 20 حرف) عناوين رئيسية
                                    is_main_title = len(clean_line) < 20
                                    # سنعتبر السطور المتوسطة (أقل من 40 حرف) عناوين فرعية
                                    is_sub_title = len(clean_line) < 40

                                    if is_main_title:
                                        # عنوان رئيسي: حجم 16، ثخين (استخدام font_bold_path)
                                        new_page.insert_text((50, y_offset), clean_line, fontsize=16, color=(0,0,0), fontfile=font_bold_path)
                                        y_offset += 20 # مسافة أوسع للعناوين
                                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=16, fontname="f0", fontfile=font_bold_path, color=(0.7, 0, 0))
                                        y_offset += 30 # مسافة بعد العنوان المترجم
                                    elif is_sub_title:
                                        # عنوان فرعي: حجم 15
                                        new_page.insert_text((50, y_offset), clean_line, fontsize=15, color=(0,0,0))
                                        y_offset += 18
                                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=15, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                                        y_offset += 28 # مسافة بعد العنوان الفرعي المترجم
                                    else:
                                        # نص عادي: حجم الخط الإنجليزي 14 والعربي 14
                                        new_page.insert_text((50, y_offset), clean_line, fontsize=14, color=(0,0,0))
                                        y_offset += 16 # مسافة للفقرات العادية
                                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=14, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                                        y_offset += 25 # مسافة بعد الفقرة المترجمة

                                except Exception as e: 
                                    print(f"Error in line processing: {e}")
                                    continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"حدث خطأ في الشكل الكلاسيكي: {e}")

# --- الشكل 2: المُعدَّل (الترجمة حمراء، تحت النص، على طوله) ---
def run_inject_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style2_Inject_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)
        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        translator = GoogleTranslator(source='auto', target='ar')

        for page in doc:
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    # الحصول على موقع النص الأصلي (bbox)
                                    rect = span["bbox"]
                                    
                                    # 1. مسح المنطقة الأصلية
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    
                                    # 2. ترجمة النص إلى العربية
                                    trans = translator.translate(txt)
                                    fixed_arabic = fix_arabic(trans)
                                    
                                    # --- التعديل: تحديد حجم الخط ولون الترجمة ---
                                    # النص الإنجليزي في الأعلى قليلاً
                                    eng_size = span["size"] * 0.85
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_size), txt, fontsize=eng_size, color=(0,0,0))
                                    
                                    # النص العربي بالأسفل (إزاحة لأسفل لتكون "تحت")، بحجم أصغر قليلاً
                                    # color=(0.8, 0, 0) هو تدرج من اللون الأحمر
                                    ar_size = span["size"] * 0.65 
                                    arabic_start_point = fitz.Point(rect[0], rect[3] + ar_size - 1)
                                    page.insert_text(arabic_start_point, 
                                                      fixed_arabic, 
                                                      fontsize=ar_size, 
                                                      fontname="f0", 
                                                      fontfile=font_path, 
                                                      color=(0.8, 0, 0)) # اللون الأحمر
                                except Exception as t_err:
                                    # إذا فشلت ترجمة كتلة محددة، نكتب النص الأصلي كما هو
                                    print(f"Error translating span: {t_err}")
                                    continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الحقن: {e}")

# --- الشكل 3: المُعدَّل (رفع خط الهايلايت، الترجمة حمراء) ---
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
        translator = GoogleTranslator(source='auto', target='ar')

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
                                    
                                    # 1. ترجمة النص إلى العربية
                                    trans = translator.translate(txt)
                                    fixed_arabic = fix_arabic(trans)
                                    
                                    # --- التعديل: حجم الخط وموقع الهايلايت واللون الأحمر ---
                                    
                                    # حساب موقع الترجمة العربية أسفل النص الأصلي
                                    ar_size = span["size"] * 0.65 
                                    # النقطة التي سنبدأ عندها الكتابة العربية
                                    arabic_start_point = fitz.Point(rect[0], rect[3] + ar_size - 1)
                                    
                                    # رسم الهايلايت (تم تعديل الموقع لتقليل الإزاحة وتجنب تغطية النص)
                                    # color=(0.92, 0.96, 1) هو تدرج من اللون الأزرق السماوي (الأصلي)
                                    # سنترك لون الهايلايت الأصلي (لأنه لم يطلب تغييره)، ونغير لون الخط فقط
                                    # y0, y1 تم رفعهما لتقليل التداخل
                                    high_rect = fitz.Rect(rect[0], rect[3] - 1, rect[2], rect[3] + ar_sz - 0.5) 
                                    page.draw_rect(high_rect, color=(0.92, 0.96, 1), fill=(0.92, 0.96, 1))
                                    
                                    # كتابة النص العربي المترجم باللون الأحمر
                                    # color=(0.8, 0, 0) هو تدرج من اللون الأحمر
                                    page.insert_text(arabic_start_point, 
                                                      fixed_arabic, 
                                                      fontsize=ar_size, 
                                                      fontname="f0", 
                                                      fontfile=font_path, 
                                                      color=(0.8, 0, 0)) # اللون الأحمر
                                except Exception as t_err:
                                    print(f"Error translating span: {t_err}")
                                    continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الهايلايت: {e}")

# --- تشغيل البوت ---
bot.polling()
                                    

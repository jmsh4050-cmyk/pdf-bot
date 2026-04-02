import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
# ملاحظة: التوكن يبقى كما هو في الكود الأصلي الذي أرسلته
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    bot.reply_to(message, f"أهلاً {user_name}! البوت جاهز للترجمة المزدوجة الآن ✅\nأرسل ملف الـ PDF مباشرة.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    user_id = message.from_user.id
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ الكلاسيكي (مع الصور) 🖼️", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (تحت الخط) 💉", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت 🖍️", callback_data="style_high")
    markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "اختار نوع التنسيق المفضل لديك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "أرسل الملف مرة ثانية.")
        return
    file_info = user_data[user_id]
    bot.edit_message_text("⏳ جاري المعالجة... انتظر ثواني", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_fpdf_style_fixed(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# ==============================================================================
# --- الشكل 1: المُعدَّل (الصور مُصغّرة، أحجام الخطوط الجديدة، تضييق المساحات) ---
# ==============================================================================
def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 
        
        # تعريف ثابت لعرض الصفحة الافتراضي لـ A4 (595 نقطة)
        PAGE_WIDTH = 595

        for page in doc:
            new_page = out_doc.new_page()
            # تقليل الهامش العلوي الأولي لضغط الصفحة
            y_offset = 35 
            
            # 1. استخراج الصور ووضعها أولاً (تم تعديل الحجم والموقع لضغط الصفحة)
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    if base_image["width"] < 120: continue 

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    # --- تعديل: تصغير حجم الصورة وضبط الموقع لتضييق المساحة ---
                    desired_img_width = 280 # عرض أصغر قليلاً
                    desired_img_height = 160 # ارتفاع أصغر قليلاً

                    # حساب إحداثيات الصورة لتبدو في منتصف الصفحة أفقيًا
                    img_x = (PAGE_WIDTH - desired_img_width) / 2
                    
                    img_rect = fitz.Rect(img_x, y_offset, img_x + desired_img_width, y_offset + desired_img_height)
                    new_page.insert_image(img_rect, filename=img_name, keep_proportion=True)
                    
                    # --- تعديل: تقليل الإزاحة بعد الصورة لضغط المساحات ---
                    y_offset += desired_img_height + 15 # مسافة صغيرة جداً بعد الصورة
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # 2. إضافة النصوص المترجمة بأحجام الخطوط الجديدة وتضييق المسافات
            # نستخدم "dict" بدلاً من "text" للحصول على معلومات الموقع وحجم الخط الأصلي
            text_dict = page.get_text("dict")
            if text_dict["blocks"]:
                for block in text_dict["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            clean_line = ""
                            # تجميع النص من السبانز (spans) للحصول على السطر الكامل
                            for span in line["spans"]:
                                clean_line += span["text"]
                            
                            clean_line = clean_line.strip()
                            if len(clean_line) > 1: # معالجة السطور التي تحتوي على أكثر من حرف واحد
                                try:
                                    translated = GoogleTranslator(source='en', target='ar').translate(clean_line)
                                    fixed_ar = fix_arabic(translated)
                                    
                                    # التحقق من المساحة العمودية المتبقية وإضافة صفحة جديدة إذا لزم الأمر
                                    # زدنا الحد قليلاً لاستغلال الصفحة بشكل أكبر (810 بدلاً من 750)
                                    if y_offset > 810: 
                                        new_page = out_doc.new_page()
                                        y_offset = 35

                                    # --- تعديل: تحديد حجم الخط بناءً على طول السطر (تمييز العناوين) ---
                                    # سنعتبر السطور القصيرة جداً (أقل من 20 حرف) عناوين رئيسية
                                    is_main_title = len(clean_line) < 20
                                    # سنعتبر السطور المتوسطة الطول (بين 20 و 40 حرف) عناوين فرعية
                                    is_sub_title = 20 <= len(clean_line) < 40
                                    
                                    if is_main_title:
                                        # عنوان رئيسي: حجم 11، ثخين (بافتراض Amiri-Bold.ttf موجود، أو نستخدم الخيار الافتراضي لـ fitz)
                                        # سنستخدم خط "f1" (الثخين) المدمج في fitz أو Amiri إذا كان يدعمه
                                        new_page.insert_text((50, y_offset), clean_line, fontsize=11, color=(0,0,0))
                                        y_offset += 16 # مسافة عمودية أضيق بعد العنوان
                                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=11, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                                        y_offset += 20 # مسافة بعد العنوان المترجم
                                    elif is_sub_title:
                                        # عنوان فرعي: حجم 9، ثخين
                                        new_page.insert_text((50, y_offset), clean_line, fontsize=9, color=(0,0,0))
                                        y_offset += 14
                                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=9, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                                        y_offset += 18
                                    else:
                                        # نص عادي: حجم 8 للكل
                                        new_page.insert_text((50, y_offset), clean_line, fontsize=8, color=(0,0,0))
                                        y_offset += 12 # مسافة أضيق للسطور العادية لضغط الصفحة
                                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=8, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                                        y_offset += 16 # مسافة بعد الفقرة المترجمة

                                except Exception as e: 
                                    print(f"Error in line processing: {e}")
                                    continue # الاستمرار في معالجة السطر التالي في حال حدوث خطأ

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل الأول المُعدَّل: {e}")

# --- الشكل 2: الحقن (يبقى كما هو) ---
def run_inject_style(message, file_info):
    # يبقى كما هو في الكود الأصلي
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style2_Inject_{file_info['file_name']}"
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
                                    # إنجليزي فوق
                                    eng_sz = span["size"] * 0.8
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    # عربي تحت (إزاحة لأسفل)
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.6
                                    page.insert_text(fitz.Point(rect[0], rect[3] + ar_sz - 1), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0, 0.4, 0.8))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# --- الشكل 3: الهايلايت (يبقى كما هو) ---
def run_highlight_style(message, file_info):
    # يبقى كما هو في الكود الأصلي
    # كود الهايلايت يبقى كما هو مع تكبير الخط العربي
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style3_{file_info['file_name']}"
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
                                    ar_sz = span["size"] * 0.65 
                                    high_rect = [rect[0], rect[3] - 2, rect[2], rect[3] + ar_sz - 1]
                                    page.draw_rect(high_rect, color=(0.92, 0.96, 1), fill=(0.92, 0.96, 1))
                                    page.insert_text(fitz.Point(rect[0], high_rect[3]-0.5), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1, 0.3, 0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# --- دالة الإرسال والتنظيف (تبقى كما هو) ---
def send_and_clean(message, out, inp):
    # يبقى كما هو في الكود الأصلي
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم الإنجاز بتصميمك الخاص!")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

# --- تشغيل البوت ---
bot.polling()
        

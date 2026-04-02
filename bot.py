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
    # إعادة تشكيل الخط العربي
    reshaped_text = arabic_reshaper.reshape(text)
    # تصحيح الاتجاه ليكون من اليمين لليسار
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
# --- الشكل 1: المُصَحَّح (الصور مُصغّرة، النصوص بالمنتصف باستخدام textbox، تنسيق الخطوط الجديد) ---
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
        
        # تعريف ثوابت للصفحة
        PAGE_WIDTH = 595
        PAGE_HEIGHT = 842 # الارتفاع الافتراضي لـ A4

        # تعريف متغيرات محددة لـ Textbox لتنفيذ المحاذاة للمنتصف
        textbox_x_offset = 50 # الهامش الجانبي للـ textbox
        textbox_width = PAGE_WIDTH - (2 * textbox_x_offset) # عرض صندوق النص

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 40 
            
            # 1. استخراج الصور ووضعها (تم تصغيرها وضغطها لتقليل الصفحات)
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    # تجاهل الأيقونات الصغيرة جداً
                    if base_image["width"] < 100: continue 

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    # --- تعديل: تصغير حجم الصورة ---
                    desired_img_width = 250
                    desired_img_height = 150 

                    # حساب مركز الصفحة وضع الصورة فيه
                    img_x = (PAGE_WIDTH - desired_img_width) / 2
                    
                    img_rect = fitz.Rect(img_x, y_offset, img_x + desired_img_width, y_offset + desired_img_height)
                    new_page.insert_image(img_rect, filename=img_name, keep_proportion=True)
                    
                    # --- تعديل: تقليل الإزاحة بعد الصورة لضغط الصفحة ---
                    y_offset += desired_img_height + 15 
                    processed_images.append(xref)
                    os.remove(img_name)
                except: pass

            # 2. إضافة النصوص المترجمة (بالمنتصف والتنسيق الجديد باستخدام insert_textbox)
            # تم استخدام "dict" بدلاً من "text" للوصول لحجم الخط الأصلي
            text_blocks = page.get_text("dict")["blocks"]
            if text_blocks:
                for block in text_blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            clean_line = ""
                            # تجميع النص من السبانز (spans)
                            for span in line["spans"]:
                                clean_line += span["text"]
                            
                            clean_line = clean_line.strip()
                            if len(clean_line) > 1:
                                try:
                                    # ترجمة السطر
                                    translated = GoogleTranslator(source='en', target='ar').translate(clean_line)
                                    fixed_ar = fix_arabic(translated)
                                    
                                    # التحقق من المساحة العمودية وإضافة صفحة جديدة إذا لزم الأمر
                                    # زدنا الحد قليلاً لأن insert_textbox تتطلب مساحة داخلية
                                    if y_offset > 800: 
                                        new_page = out_doc.new_page()
                                        y_offset = 40

                                    # --- تعديل: تمييز الخطوط بناءً على حجم الخط الأصلي ---
                                    # الحصول على حجم الخط الأصلي لأول سبان في السطر
                                    original_font_size = line["spans"][0]["size"]
                                    
                                    if original_font_size > 22: # عناوين رئيسية جداً
                                        eng_size = 13
                                        ar_size = 13
                                        # يمكن زيادة مسافة الارتفاع للعناوين
                                        text_height = 20
                                        space_after = 28
                                    elif original_font_size > 14: # عناوين فرعية
                                        eng_size = 12
                                        ar_size = 12
                                        text_height = 18
                                        space_after = 24
                                    else: # نص عادي
                                        eng_size = 10
                                        ar_size = 10
                                        text_height = 14
                                        space_after = 20
                                    
                                    # --- استخدام insert_textbox لتنفيذ المحاذاة للمنتصف ---
                                    
                                    # 1. تحديد مستطيل النص الإنجليزي
                                    eng_rect = fitz.Rect(textbox_x_offset, y_offset, textbox_x_offset + textbox_width, y_offset + text_height)
                                    # align=fitz.TEXT_ALIGN_CENTER هي القيمة الصحيحة لـ textbox المحاذي للمنتصف
                                    # نستخدم المعامل align داخل insert_textbox وليس insert_text
                                    new_page.insert_textbox(eng_rect, clean_line, fontsize=eng_size, color=(0,0,0), align=fitz.TEXT_ALIGN_CENTER)
                                    y_offset += text_height + 2 # إزاحة بسيطة قبل العربي

                                    # 2. تحديد مستطيل النص العربي
                                    ar_rect = fitz.Rect(textbox_x_offset, y_offset, textbox_x_offset + textbox_width, y_offset + text_height)
                                    new_page.insert_textbox(ar_rect, fixed_ar, fontsize=ar_size, fontname="f0", fontfile=font_path, color=(0.7, 0, 0), align=fitz.TEXT_ALIGN_CENTER)
                                    
                                    # الإزاحة العمودية بعد السطر المترجم
                                    y_offset += text_height + space_after - text_height - 2 # تعديل الإزاحة لتناسب space_after

                                except Exception as e: 
                                    print(f"Error in line processing: {e}")
                                    # --- تعديل: كتابة النص الإنجليزي باللون الرمادي في حال فشل الترجمة باستخدام textbox ---
                                    # زدنا المساحة قليلاً لرسالة الخطأ
                                    error_rect = fitz.Rect(textbox_x_offset, y_offset, textbox_x_offset + textbox_width, y_offset + 16)
                                    new_page.insert_textbox(error_rect, f"[Trans. Error]: {clean_line}", fontsize=10, color=(0.8, 0.8, 0.8), align=fitz.TEXT_ALIGN_CENTER)
                                    y_offset += 16 + 18
                                    continue
            else:
                # إذا لم يتم العثور على أي كتل نصوص (السبب الأول المحتمل - PDF عبارة عن صور)
                print(f"Warning: No text blocks found on page {page.number}.")
                # يمكنك اختيار إبلاغ المستخدم بأن الصفحة قد تحتوي على صور فقط.

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في الشكل الأول المُصَحَّح: {e}")

# ==============================================================================
# --- الأشكال الأخرى والوظائف المساعدة تبقى كما هي دون تغيير ---
# ==============================================================================

# --- الشكل 2: الحقن (الترجمة تحت الإنجليزي) ---
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

def send_and_clean(message, out, inp):
    # يبقى كما هو في الكود الأصلي
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم الإنجاز بتصميمك الخاص!")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()
                            



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
        f"أهلاً {user_name}! تم تحديث التنسيقات بناءً على طلبك بدقة ✅\n\n"
        "أرسل لي ملف PDF، وسأقوم بترجمته وتنسيقه.\n"
        "(الشكل الأول يصمم ملزمة، الثاني يلون بالأحمر، الثالث يضيق الهايلايت)."
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
    btn1 = telebot.types.InlineKeyboardButton("1️⃣ الكلاسيكي (تصميم ملزمة) 🖼️", callback_data="style_fpdf")
    btn2 = telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن (لون أحمر) 💉", callback_data="style_inject")
    btn3 = telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت (هايلايت رفيع) 🖍️", callback_data="style_high")
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
            caption_text = f"✅ تم الإنجاز بتنسيقك الخاص.. جرب البقية 🔥\n🔗 [دخول البوت]({BOT_LINK})"
            bot.send_document(message.chat.id, f, caption=caption_text, parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp):
        os.remove(inp)

# ==============================================================================
# --- التعديلات الجذرية الجديدة في التنسيقات الثلاثة ---
# ==============================================================================

# --- الشكل 1: المُعدَّل (تصميم ملزمة: صورة فوق، نص إنجليزي وتحته ترجمة، خط 15، عنوان أحمر) ---
def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_Malama_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf" 

        for page in doc:
            new_page = out_doc.new_page()
            y_offset = 50
            
            # 1. استخراج الصور ووضعها في الأعلى (تصميم ملزمة: صورة توضيحية أولاً)
            processed_images = []
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    if xref in processed_images: continue
                    base_image = doc.extract_image(xref)
                    # تجاهل الأيقونات واللوجوهات الصغيرة (أقل من 100 بكسل لضغط الصفحة)
                    if base_image["width"] < 100: continue

                    img_name = f"tmp_{user_id}_{xref}.{base_image['ext']}"
                    with open(img_name, "wb") as f: f.write(base_image["image"])
                    
                    # تصميم ملزمة: وضع الصورة في الأعلى بحجم أصغر قليلاً (A4 عرضها 595)
                    img_rect = fitz.Rect(100, y_offset, 495, y_offset + 180) # أصغر من السابق
                    new_page.insert_image(img_rect, filename=img_name, keep_proportion=True)
                    y_offset += 200 # إزاحة بعد الصورة
                    processed_images.append(xref)
                    os.remove(img_name)
                    # نكتفي بصورة واحدة في الأعلى لكل صفحة لتصميم ملزمة أنيق
                    break 
                except: pass

            # 2. استخراج النصوص وترجمتها ووضعها (إنجليزي وتحته عربي)
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            # ترجمة السطر
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            
                            # التحقق من المساحة العمودية المتبقية
                            if y_offset > 780: 
                                new_page = out_doc.new_page()
                                y_offset = 50

                            # --- التعديل: تمييز العناوين باللون الأحمر وحجم الخط 15 للكل ---
                            # سنعتبر السطور القصيرة جداً عناوين
                            is_title = len(line) < 25
                            
                            if is_title:
                                # عنوان: لون أحمر، حجم 15 (ويمكن جعله ثخيناً Bold إذا أردت)
                                new_page.insert_text((50, y_offset), line, fontsize=15, color=(0.8, 0, 0)) # أحمر
                                y_offset += 18
                                new_page.insert_text((50, y_offset), fixed_ar, fontsize=15, fontname="f0", fontfile=font_path, color=(0.8, 0, 0)) # أحمر
                                y_offset += 25 # مسافة بعد العنوان
                            else:
                                # نص عادي: لون أسود، حجم خط 15 للكل
                                new_page.insert_text((50, y_offset), line, fontsize=15, color=(0,0,0))
                                y_offset += 18
                                new_page.insert_text((50, y_offset), fixed_ar, fontsize=15, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                                y_offset += 25 # مسافة بعد الفقرة المترجمة

                        except Exception as e: 
                            print(f"Error in line processing: {e}")
                            continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"حدث خطأ في تصميم الملزمة: {e}")

# --- الشكل 2: المُعدَّل (تغيير لون الترجمة للأحمر فقط) ---
def run_inject_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style2_InjectRed_{file_info['file_name']}"
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
                                    # 1. مسح المنطقة الأصلية
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    
                                    # --- التعديل: النص الإنجليزي في الأعلى قليلاً ولون الترجمة أحمر ---
                                    eng_size = span["size"] * 0.85
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_size), txt, fontsize=eng_size, color=(0,0,0))
                                    
                                    # الترجمة العربية بالأسفل (إزاحة بسيطة للأسفل لتكون "تحت")
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    
                                    # ar_size تم الحفاظ عليها، لكن لون الخط أصبح أحمر
                                    ar_size = span["size"] * 0.65 
                                    arabic_start_point = fitz.Point(rect[0], rect[3] + ar_size - 2)
                                    page.insert_text(arabic_start_point, 
                                                      fixed, 
                                                      fontsize=ar_size, 
                                                      fontname="f0", 
                                                      fontfile=font_path, 
                                                      color=(0.8, 0, 0)) # اللون الأحمر (تعديل اللون فقط)
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الحقن الأحمر: {e}")

# --- الشكل 3: المُعدَّل (تصغير مستطيل الهايلايت والترجمة) ---
def run_highlight_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"HighlightSmall_{file_info['file_name']}"
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
                                    
                                    # --- التعديل: تصغير حجم الخط العربي وتضييق الهايلايت العمودي ---
                                    # ar_size أصغر من السابق ليتناسب مع الهايلايت الرفيع
                                    ar_size = span["size"] * 0.55 # أصغر 
                                    
                                    # حساب نقطة الكتابة العربية لتكون في منتصف الهايلايت الرفيع
                                    arabic_start_point = fitz.Point(rect[0], rect[3] + ar_size - 1.5)
                                    
                                    # رسم الهايلايت (تم تضييق المستطيل العمودي y0, y1)
                                    # high_rect تم تضييقه من الأعلى والأسفل
                                    high_rect = fitz.Rect(rect[0], rect[3] - 1.5, rect[2], rect[3] + ar_size - 1) 
                                    
                                    # color=(0.92, 0.96, 1) هو تدرج من اللون الأزرق السماوي (الأصلي)
                                    page.draw_rect(high_rect, color=(0.92, 0.96, 1), fill=(0.92, 0.96, 1))
                                    
                                    # كتابة النص العربي المترجم داخل الهايلايت الرفيع (باللون الأزرق الأصلي أو الأسود)
                                    page.insert_text(arabic_start_point, 
                                                      fixed, 
                                                      fontsize=ar_size, 
                                                      fontname="f0", 
                                                      fontfile=font_path, 
                                                      color=(0.1, 0.3, 0.7)) # لون أزرق أصلي
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الهايلايت الرفيع: {e}")

# --- تشغيل البوت ---
bot.polling()
                        

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

# --- الدوال الأساسية (التي كانت ناقصة أو تحتاج تعديل) ---

def fix_arabic(text):
    """تصحيح ظهور اللغة العربية في الـ PDF"""
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def contains_arabic(text):
    """التحقق إذا كان النص يحتوي على حروف عربية"""
    if not text: return False
    return any("\u0600" <= char <= "\u06FF" for char in text)

def is_subscribed(user_id):
    """التحقق من الاشتراك بالقناة"""
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def send_and_clean(message, out_path, in_path):
    """إرسال الملف المترجم وحذف النسخ المؤقتة"""
    with open(out_path, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"✅ تم الترتيب بنجاح لدفعة التمريض🔥")
    if os.path.exists(out_path): os.remove(out_path)
    if os.path.exists(in_path): os.remove(in_path)

# --- دالة الترجمة الذكية (حل مشكلة اختفاء الترجمة) ---
def get_safe_translation(text, target_lang='ar'):
    """دالة ذكية لاستخدام deep_translator مع التعامل مع الأخطاء"""
    if not text: return ""
    try:
        # إذا كان النص طويلاً جداً (أكثر من 400 حرف)، نقسمه لضمان نجاح الترجمة
        if len(text) > 400:
            parts = text.split('. ', 1)
            translated_parts = []
            for part in parts:
                trans = GoogleTranslator(source='en', target=target_lang).translate(part)
                translated_parts.append(trans)
            return '. '.join(translated_parts)
        else:
            return GoogleTranslator(source='en', target=target_lang).translate(text)
    except Exception as e:
        print(f"Error in translation: {e}")
        return f"[Translation Error] - {text}" # إظهار النص الأصلي عند الخطأ حتى لا تختفي

# --- الشكل الرابع: الترتيب المتسلسل الواضح والضخم ---
def run_professional_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Ordered_{file_info['file_name']}"
        
        with open(input_pdf, 'wb') as f: 
            f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf" # لازم يكون ملف الخط موجود بجانب الكود
        
        for page in doc:
            # ترتيب النصوص من الأعلى للأسفل
            text_blocks = page.get_text("blocks")
            text_blocks.sort(key=lambda b: b[1])
            
            # مسح الصفحة لضمان عدم التداخل
            page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            y_cursor = 50 
            margin = 40

            for block in text_blocks:
                txt = block[4].strip()
                if len(txt) > 2 and not contains_arabic(txt):
                    try:
                        # استخدام دالة الترجمة الذكية الجديدة
                        translated = get_safe_translation(txt)
                        ar_text = fix_arabic(translated)
                        
                        # تمييز العناوين والخطوات (مثل ملازم التمريض)
                        is_header = any(k in txt.upper() for k in ["NURSING", "RISK", "CARE", "DIAGNOSIS", "DIABETIC"])
                        
                        f_size = 14 if is_header else 12 # تكبير حجم الخط لضمان الوضوح
                        line_spacing = 35 if is_header else 28
                        
                        if is_header:
                            # رسم مستطيل تظليل للعنوان
                            page.draw_rect(fitz.Rect(margin-5, y_cursor-5, page.rect.width-margin+5, y_cursor+28), 
                                           color=(0.93, 0.93, 0.93), fill=(0.93, 0.93, 0.93))

                        # كتابة الإنكليزي (يسار)
                        page.insert_text(fitz.Point(margin, y_cursor + 18), txt, fontsize=f_size, color=(0,0,0))
                        y_cursor += line_spacing
                        
                        # كتابة العربي تحته مباشرة (يمين) - بألوان تمريضية هادئة
                        page.insert_text(fitz.Point(page.rect.width - margin, y_cursor), 
                                         ar_text, fontsize=f_size, fontname="f0", fontfile=font_path, 
                                         color=(0.5, 0, 0) if is_header else (0.1, 0.1, 0.1), align=2)

                        y_cursor += line_spacing + 12
                        if y_cursor > page.rect.height - 70: break 
                    except: continue

        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
        
    except Exception as e:
        bot.reply_to(message, f"خطأ برمجـي في الشكل الاحترافي: {str(e)}\nتأكد من وجود ملف خط Amiri.ttf")

# --- استقبال الأوامر والملفات ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF للبدء بالترجمة.\nقناتنا: {CHANNEL_USERNAME}")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "🚫 اشترك في القناة أولاً لتفعيل البوت.")
        return
        
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف بصيغة PDF فقط.")
        return

    user_data[message.from_user.id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("الشكل 4: الترتيب المتسلسل (النسخة الواضحة) ✅", callback_data="run_pro"))
    bot.reply_to(message, "اختار التنسيق المطلوب لدفعة التمريض:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "run_pro")
def execute_style(call):
    bot.edit_message_text("⏳ جاري المعالجة وترجمة الفقرات... انتظر قليلاً", call.message.chat.id, call.message.message_id)
    run_professional_style(call.message, user_data[call.from_user.id])

bot.polling()

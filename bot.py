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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً وسام! تم تعديل الشكل الأول ليكون بنفس تنسيق الملف الأصلي ويملاً الفراغات بدقة ✅")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id): return
    user_data[user_id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("1️⃣ التنسيق الأصلي (منسق 🛡️)", callback_data="style_fpdf"))
    markup.add(telebot.types.InlineKeyboardButton("2️⃣ شكل الحقن", callback_data="style_inject"), 
               telebot.types.InlineKeyboardButton("3️⃣ شكل الهايلايت", callback_data="style_high"))
    bot.reply_to(message, "اختار التنسيق المطلوب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def process_style(call):
    user_id = call.from_user.id
    file_info = user_data.get(user_id)
    if not file_info: return
    bot.edit_message_text("⏳ جاري الحفاظ على التنسيق الأصلي للملف...", call.message.chat.id, call.message.message_id)
    
    if call.data == "style_fpdf":
        run_original_style(call.message, file_info)
    elif call.data == "style_inject":
        run_inject_style(call.message, file_info)
    else:
        run_highlight_style(call.message, file_info)

# --- التعديل الجوهري: الشكل الأول بنفس توزيع الملف الأصلي ---
def run_original_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Original_Style_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open()
        font_path = "Amiri.ttf"

        for page in doc:
            # ننشئ صفحة جديدة بنفس مقاسات الصفحة الأصلية تماماً
            new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # 1. نقل الصور لأماكنها الأصلية وتصغير اللوغو
            for img in page.get_images(full=True):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.width < 100 or pix.height < 100: continue # تجاهل اللوغو
                    
                    # الحصول على مكان الصورة الأصلي في الصفحة
                    img_rects = page.get_image_rects(xref)
                    for r in img_rects:
                        # تصغير بسيط للصورة لترك مساحة للترجمة
                        small_rect = fitz.Rect(r.x0, r.y0, r.x1 * 0.9, r.y1 * 0.9)
                        new_page.insert_image(small_rect, pixmap=pix)
                except: pass

            # 2. نقل النصوص وترجمتها في نفس إحداثياتها الأصلية
            blocks = page.get_text("blocks")
            for b in blocks:
                if b[6] == 0: # كائن نصي
                    text = b[4].strip()
                    if len(text) > 3:
                        try:
                            # ترجمة النص
                            translated = GoogleTranslator(source='en', target='ar').translate(text)
                            fixed_ar = fix_arabic(translated)
                            
                            # إحداثيات البلوك الأصلي
                            rect = fitz.Rect(b[:4])
                            
                            # كتابة الإنجليزي في مكانه الأصلي
                            new_page.insert_text((rect.x0, rect.y0), text, fontsize=11, color=(0,0,0))
                            
                            # كتابة العربي تحت الإنجليزي مباشرة في نفس الفراغ
                            new_page.insert_text((rect.x0, rect.y0 + 12), fixed_ar, fontsize=11, fontname="f0", fontfile=font_path, color=(0.8, 0, 0))
                        except: pass

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

# (دوال الحقن والهايلايت و send_and_clean تبقى كما هي)
def send_and_clean(message, out, inp):
    if os.path.exists(out):
        with open(out, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم الحفاظ على التنسيق لدفعة التمريض🔥\n🔗 [دخول البوت]({BOT_LINK})", parse_mode="Markdown")
        os.remove(out)
    if os.path.exists(inp): os.remove(inp)

bot.polling()

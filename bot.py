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

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# --- دالة الشكل الرابع (النسخة الضخمة والواضحة) ---
def run_professional_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Final_Style_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf" # تأكد من وجود الملف بجانب الكود
        
        for page in doc:
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # ترتيب من الأعلى للأسفل
            
            # مسح الصفحة بالكامل لضمان النظافة
            page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            y_cursor = 50 
            margin = 40

            for block in blocks:
                txt = block[4].strip()
                if len(txt) > 2:
                    try:
                        # الترجمة الفورية
                        translated = GoogleTranslator(source='en', target='ar').translate(txt)
                        ar_text = fix_arabic(translated)
                        
                        # تحديد نوع السطر (عنوان أو نقطة أو نص عادي)
                        is_header = any(k in txt.upper() for k in ["NURSING", "RISK", "DIABETIC", "CARE", "DIAGNOSIS", "RELATED"])
                        is_step = txt[0].isdigit() and ('.' in txt[:3])

                        # ضبط حجم الخط (تكبير بناءً على طلبك)
                        font_size = 14 if is_header else 12
                        line_spacing = 30 if is_header else 25

                        if is_header:
                            # رسم مستطيل تظليل للعنوان (مثل الصورة اللي دزيتها)
                            page.draw_rect(fitz.Rect(margin-10, y_cursor-5, page.rect.width-margin+10, y_cursor+line_spacing), 
                                           color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))
                            txt_color = (0, 0, 0)
                            ar_color = (0.7, 0, 0) # أحمر غامق للعنوان العربي
                        elif is_step:
                            txt_color = (0, 0, 0.7) # أزرق للنقاط
                            ar_color = (0, 0, 0.7)
                        else:
                            txt_color = (0, 0, 0)
                            ar_color = (0.2, 0.2, 0.2)

                        # كتابة الإنكليزي (يسار)
                        page.insert_text(fitz.Point(margin, y_cursor + 15), txt, fontsize=font_size, color=txt_color)
                        
                        # كتابة العربي (يمين - بنفس السطر أو تحته بمسافة بسيطة لضمان الوضوح)
                        y_cursor += line_spacing
                        page.insert_text(fitz.Point(page.rect.width - margin, y_cursor), 
                                         ar_text, fontsize=font_size, fontname="f0", fontfile=font_path, 
                                         color=ar_color, align=2)

                        y_cursor += line_spacing + 5 # مسافة أمان للسطر القادم
                        
                        if y_cursor > page.rect.height - 60: break 
                    except: continue

        doc.save(output_pdf)
        doc.close()
        
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم التعديل: تكبير الخط + وضوح الترجمة.")
        
        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)}")

# --- المحركات (Handlers) ---
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "اشترك أولاً.") ; return
    user_data[message.from_user.id] = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("تشغيل الشكل 4 المطور 🚀", callback_data="run"))
    bot.reply_to(message, "تم الاستلام. اضغط للترجمة بخط كبير:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "run")
def start_pro(call):
    bot.edit_message_text("⏳ جاري المعالجة (النسخة الواضحة)...", call.message.chat.id, call.message.message_id)
    run_professional_style(call.message, user_data[call.from_user.id])

bot.polling()

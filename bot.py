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

def fix_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def contains_arabic(text):
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    msg = bot.reply_to(message, "⏳ جاري تصغير الخطوط وحقن الترجمة بدقة عالية...")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Compact_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf" 

        for page in doc:
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            original_text = span["text"].strip()
                            
                            # نترجم فقط إذا النص مو عربي وطوله مناسب
                            if len(original_text) > 2 and not contains_arabic(original_text):
                                try:
                                    rect = span["bbox"]
                                    
                                    # 1. مسح النص الأصلي بمستطيل أبيض
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    
                                    # 2. إعادة كتابة الإنكليزي (تصغير درجة: 0.75)
                                    eng_size = span["size"] * 0.75
                                    page.insert_text(
                                        fitz.Point(rect[0], rect[1] + eng_size), 
                                        original_text,
                                        fontsize=eng_size,
                                        color=(0, 0, 0)
                                    )
                                    
                                    # 3. ترجمة وحقن العربي (تصغير درجة إضافية: 0.60)
                                    translated = GoogleTranslator(source='en', target='ar').translate(original_text)
                                    fixed_ar = fix_arabic(translated)
                                    
                                    ar_size = span["size"] * 0.60
                                    # نضع العربي تحت الإنكليزي بمسافة بسيطة جداً
                                    page.insert_text(
                                        fitz.Point(rect[0], rect[3]), 
                                        fixed_ar,
                                        fontsize=ar_size,
                                        fontname="f0", 
                                        fontfile=font_path,
                                        color=(0, 0.4, 0.8) # لون أزرق دراسي
                                    )
                                except: continue

        doc.save(output_pdf)
        doc.close()

        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم التصغير والحقن بنجاح لدفعة التمريض🔥")

        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")

bot.polling()

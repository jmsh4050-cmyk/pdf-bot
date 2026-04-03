import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! أرسل الملزمة وسأقوم بإعادة تصميمها مع تكبير العناوين (16) في مواقعها الأصلية ✅")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"Fixed_Mlazma_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    bot.reply_to(message, "⏳ جاري إعادة الهيكلة.. العناوين ستكون بحجم 16 وفي مكانها الأصلي.")
    
    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" 

        for page in doc:
            # إنشاء صفحة جديدة بنفس أبعاد الصفحة الأصلية تماماً
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # 1. نقل الصور لمواقعها الأصلية
            image_list = page.get_images(full=True)
            for img_info in page.get_image_info():
                try:
                    img_rect = img_info["bbox"]
                    xref = img_info["xref"]
                    base_image = doc.extract_image(xref)
                    new_page.insert_image(img_rect, stream=base_image["image"])
                except: pass

            # 2. معالجة النصوص (إبقاء المواقع الأصلية وتكبير العناوين)
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            txt = s["text"].strip()
                            if len(txt) < 2: continue
                            
                            # إحداثيات النص الأصلي
                            origin_x, origin_y = s["origin"]
                            original_size = s["size"]
                            
                            try:
                                # ترجمة النص
                                trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                fixed_ar = fix_arabic(trans)

                                # --- تحديد العنوان (إذا كان حجم الخط الأصلي كبيراً أو النص قصيراً) ---
                                is_title = original_size > 13 or len(txt) < 30
                                
                                if is_title:
                                    # العنوان: حجم 16، لون أحمر، في موقعه الأصلي
                                    current_size = 16
                                    color = (0.8, 0, 0) # أحمر داكن
                                else:
                                    # النص العادي: حجم 14
                                    current_size = 14
                                    color = (0, 0, 0) # أسود

                                # كتابة النص الإنجليزي في موقعه
                                new_page.insert_text((origin_x, origin_y), txt, fontsize=current_size, color=color)
                                
                                # كتابة الترجمة العربية تحتها مباشرة (إزاحة بسيطة لأسفل)
                                new_page.insert_text((origin_x, origin_y + current_size + 2), 
                                                   fixed_ar, 
                                                   fontsize=current_size - 1, 
                                                   fontname="f0", 
                                                   fontfile=font_path, 
                                                   color=(0.6, 0, 0)) # ترجمة بلون مميز
                            except:
                                continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ اكتملت الملزمة المنسقة!")
            
    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()

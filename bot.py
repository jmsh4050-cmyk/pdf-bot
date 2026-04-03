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
    bot.reply_to(message, "تم زيادة المسافات بين الأسطر لراحة العين ✅\nأرسل الملزمة الآن.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"Mlazma_Spaced_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" 

        for page in doc:
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # نقل الصور لمواقعها
            for img_info in page.get_image_info():
                try:
                    new_page.insert_image(img_info["bbox"], stream=doc.extract_image(img_info["xref"])["image"])
                except: pass

            # معالجة النصوص وترجمتها
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            txt = s["text"].strip()
                            if len(txt) < 2: continue
                            
                            origin_x, origin_y = s["origin"]
                            original_size = s["size"]
                            
                            try:
                                trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                fixed_ar = fix_arabic(trans)

                                # تحديد حجم الخط (16 للعناوين و 14 للعادي)
                                if original_size > 13 or len(txt) < 30:
                                    current_size = 16
                                else:
                                    current_size = 14

                                # 1. كتابة النص الإنجليزي (أسود)
                                new_page.insert_text((origin_x, origin_y), txt, fontsize=current_size, color=(0, 0, 0))
                                
                                # 2. كتابة النص العربي (أحمر) 
                                # زدنا الإزاحة هنا لتكون المسافة أكبر (حجم الخط + 6 بكسل)
                                new_page.insert_text((origin_x, origin_y + current_size + 6), 
                                                   fixed_ar, 
                                                   fontsize=current_size - 1, 
                                                   fontname="f0", 
                                                   fontfile=font_path, 
                                                   color=(0.8, 0, 0)) 
                            except: continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم التنسيق مع تكبير المسافات.")
            
    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()

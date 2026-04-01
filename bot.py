import os
import telebot
import fitz # للملف الأصلي
from fpdf import FPDF # لصنع الملف الجديد
import arabic_reshaper
from bidi.algorithm import get_display

API_TOKEN = 7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA
bot = telebot.TeleBot(API_TOKEN)

# كلاس لتصميم شكل الصفحة الجديدة
class StyledPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Medical Translation - Batch 2025', 0, 1, 'C')
        self.ln(5)

def fix_text(text):
    return get_display(arabic_reshaper.reshape(text))

@bot.message_handler(content_types=['document'])
def translate_and_style(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    # حفظ الملف
    with open("input.pdf", "wb") as f:
        f.write(downloaded)

    bot.reply_to(message, "⏳ جاري إعادة صياغة المحاضرة بتنسيق خرافي...")

    # إنشاء ملف PDF جديد
    pdf = StyledPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # قراءة الأصلي (هنا تقدر تستخدم أي وسيلة ترجمة تحبها)
    doc = fitz.open("input.pdf")
    for page in doc:
        text = page.get_text()
        # هنا تتم معالجة النص:
        # 1. العناوين تترتب
        # 2. المصطلحات تبقى انجليزي + عربي
        pdf.multi_cell(0, 10, txt=text) # مثال بسيط على النقل
        pdf.ln(2)
    
    pdf.output("output.pdf")

    # إرسال النتيجة
    with open("output.pdf", "rb") as f:
        bot.send_document(message.chat.id, f, caption="✨ محاضرتك المترجمة بترتيبها الأصلي")

bot.polling()

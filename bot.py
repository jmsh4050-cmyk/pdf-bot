import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

genai.configure(api_key=GEMINI_KEY)

# استخدم موديل موجود ومستقر
model = genai.GenerativeModel("gemini-2.0-flash")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "اهلا 👋\nاكتب:\n/quiz رياضيات\n/quiz تاريخ\nأو أي موضوع تحبه"
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)

    if not topic:
        await update.message.reply_text("مثال:\n/quiz رياضيات")
        return

    prompt = f"""
أنشئ سؤال اختيار من متعدد عن {topic}
4 خيارات
وحدد الجواب الصحيح
أعطه بصيغة JSON فقط:
{{
"question":"",
"options":["","","",""],
"answer":""
}}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text

        # محاولة استخراج JSON فقط لتجنب أي نص زائد
        start = text.find("{")
        end = text.rfind("}") + 1
        json_text = text[start:end]

        data = json.loads(json_text)

        question = data["question"]
        options = data["options"]
        answer = data["answer"]

        correct_index = options.index(answer)

        await update.message.reply_poll(
            question=question,
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

    except Exception as e:
        await update.message.reply_text(f"❌ حصل خطأ: {e}")
        print(e)


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.run_polling()

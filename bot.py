import os
import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اكتب:\n/quiz رياضيات")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)

    if not topic:
        await update.message.reply_text("مثال:\n/quiz تاريخ")
        return

    prompt = f"""
أنشئ سؤال اختيار من متعدد عن {topic}
4 خيارات
حدد الجواب الصحيح

JSON:
{{
"question":"",
"options":["","","",""],
"answer":""
}}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text

        data = json.loads(text)

        question = data["question"]
        options = data["options"]
        answer = data["answer"]

        correct = options.index(answer)

        await update.message.reply_poll(
            question=question,
            options=options,
            type="quiz",
            correct_option_id=correct
        )

    except Exception as e:
        print(e)
        await update.message.reply_text("❌ صار خطأ")


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", quiz))

app.run_polling()

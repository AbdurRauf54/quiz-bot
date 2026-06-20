import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from questions import QUESTIONS

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Welcome to Quiz Bot!*\n\nYou will get 5 questions.\nEach correct answer = 1 point ✅\n\nType /quiz to start!",
        parse_mode="Markdown"
    )

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get("q_index", 0)
    if index >= len(QUESTIONS):
        await show_result(update, context)
        return
    q = QUESTIONS[index]
    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in q["options"]]
    markup = InlineKeyboardMarkup(keyboard)
    text = f"❓ *Question {index + 1}/{len(QUESTIONS)}*\n\n{q['question']}"
    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = context.user_data.get("q_index", 0)
    q = QUESTIONS[index]
    selected = query.data
    correct = q["answer"]
    if selected == correct:
        context.user_data["score"] = context.user_data.get("score", 0) + 1
        feedback = f"✅ *Correct!* Well done!\n\nAnswer: *{correct}*"
    else:
        feedback = f"❌ *Wrong!*\n\nYour answer: {selected}\nCorrect answer: *{correct}*"
    await query.edit_message_text(
        f"❓ *Question {index + 1}/{len(QUESTIONS)}*\n\n{q['question']}\n\n{feedback}",
        parse_mode="Markdown"
    )
    context.user_data["q_index"] = index + 1
    await send_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    score = context.user_data.get("score", 0)
    total = len(QUESTIONS)
    if score == total:
        emoji = "🏆 Perfect Score!"
    elif score >= total // 2:
        emoji = "👍 Good Job!"
    else:
        emoji = "😅 Keep Practicing!"
    text = f"🎉 *Quiz Finished!*\n\nYour Score: *{score}/{total}*\n\n{emoji}\n\nType /quiz to play again!"
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["score"] = 0
    context.user_data["q_index"] = 0
    await send_question(update, context)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CallbackQueryHandler(handle_answer))
    print("🤖 Quiz Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

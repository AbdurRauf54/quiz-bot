import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from questions import QUESTIONS

load_dotenv()
TOKEN = os.getenv("TOKEN")

# Leaderboard file
LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    return {}

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f)

def update_leaderboard(user_id, username, score):
    lb = load_leaderboard()
    uid = str(user_id)
    if uid not in lb or lb[uid]["score"] < score:
        lb[uid] = {"username": username, "score": score}
    save_leaderboard(lb)

def get_top_players(n=5):
    lb = load_leaderboard()
    sorted_lb = sorted(lb.values(), key=lambda x: x["score"], reverse=True)
    return sorted_lb[:n]

# ─── /start ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    text = (
        f"👋 *Welcome, {name}!*\n\n"
        f"🎮 *Quiz Challenge Bot*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 *{len(QUESTIONS)} Questions*\n"
        f"⏱️ *15 seconds* per question\n"
        f"🏆 Top players on leaderboard\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Ready to play? 👇"
    )
    keyboard = [
        [InlineKeyboardButton("🎯 Start Quiz", callback_data="start_quiz")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
    ]
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── Send Question ────────────────────────────────────────
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get("q_index", 0)

    if index >= len(QUESTIONS):
        await show_result(update, context)
        return

    q = QUESTIONS[index]
    context.user_data["start_time"] = asyncio.get_event_loop().time()

    # Progress bar
    progress = "🟩" * (index + 1) + "⬜" * (len(QUESTIONS) - index - 1)

    keyboard = [
        [InlineKeyboardButton(f"{opt}", callback_data=f"ans:{opt}")]
        for opt in q["options"]
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Skip", callback_data="ans:__skip__")])

    text = (
        f"{progress}\n"
        f"❓ *Question {index + 1}/{len(QUESTIONS)}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{q['question']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *15 seconds!*"
    )

    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        msg = await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        msg = await update.callback_query.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

    # Save message id for timer
    context.user_data["current_msg_id"] = msg.message_id
    context.user_data["current_chat_id"] = msg.chat_id

    # Auto skip after 15 seconds
    context.user_data["q_index"] = index
    asyncio.get_event_loop().call_later(
        15,
        lambda: asyncio.ensure_future(
            auto_skip(context, msg.chat_id, msg.message_id, index)
        )
    )

# ─── Auto Skip ────────────────────────────────────────────
async def auto_skip(context, chat_id, msg_id, index):
    if context.user_data.get("q_index") == index:
        q = QUESTIONS[index]
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=(
                    f"⏰ *Time's Up!*\n\n"
                    f"❓ {q['question']}\n\n"
                    f"✅ Correct Answer: *{q['answer']}*\n\n"
                    f"⏭️ Next question..."
                ),
                parse_mode="Markdown"
            )
        except:
            pass
        context.user_data["q_index"] = index + 1
        # Send next question
        class FakeUpdate:
            message = None
            class callback_query:
                class message:
                    pass
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⏭️ Moving to next question..."
            )
            await send_next(context, chat_id, index + 1)
        except:
            pass

# ─── Send Next (helper) ───────────────────────────────────
async def send_next(context, chat_id, index):
    if index >= len(QUESTIONS):
        score = context.user_data.get("score", 0)
        total = len(QUESTIONS)
        if score == total:
            emoji = "🏆 Perfect Score! Genius!"
        elif score >= total * 0.7:
            emoji = "🥇 Excellent!"
        elif score >= total * 0.5:
            emoji = "👍 Good Job!"
        else:
            emoji = "😅 Keep Practicing!"

        text = (
            f"🎉 *Quiz Finished!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ Correct: *{score}*\n"
            f"❌ Wrong: *{total - score}*\n"
            f"📊 Score: *{score}/{total}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{emoji}"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Play Again", callback_data="start_quiz")],
            [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    q = QUESTIONS[index]
    context.user_data["start_time"] = asyncio.get_event_loop().time()
    progress = "🟩" * (index + 1) + "⬜" * (len(QUESTIONS) - index - 1)
    keyboard = [
        [InlineKeyboardButton(f"{opt}", callback_data=f"ans:{opt}")]
        for opt in q["options"]
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Skip", callback_data="ans:__skip__")])
    text = (
        f"{progress}\n"
        f"❓ *Question {index + 1}/{len(QUESTIONS)}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{q['question']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *15 seconds!*"
    )
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    context.user_data["current_msg_id"] = msg.message_id
    context.user_data["q_index"] = index
    asyncio.get_event_loop().call_later(
        15,
        lambda: asyncio.ensure_future(
            auto_skip(context, chat_id, msg.message_id, index)
        )
    )

# ─── Handle Answer ────────────────────────────────────────
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Start Quiz
    if data == "start_quiz":
        context.user_data["score"] = 0
        context.user_data["q_index"] = 0
        await query.message.reply_text("🚀 *Quiz Starting!*", parse_mode="Markdown")
        await send_question(update, context)
        return

    # Leaderboard
    if data == "show_leaderboard":
        top = get_top_players()
        if not top:
            await query.message.reply_text("🏆 Leaderboard khali hai abhi!")
            return
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        text = "🏆 *Top Players*\n━━━━━━━━━━━━━━━━━━\n"
        for i, p in enumerate(top):
            text += f"{medals[i]} *{p['username']}* — {p['score']} pts\n"
        await query.message.reply_text(text, parse_mode="Markdown")
        return

    # Answer
    if data.startswith("ans:"):
        selected = data.replace("ans:", "")
        index = context.user_data.get("q_index", 0)

        if index >= len(QUESTIONS):
            return

        q = QUESTIONS[index]
        correct = q["answer"]

        # Calculate time bonus
        start_time = context.user_data.get("start_time", 0)
        elapsed = asyncio.get_event_loop().time() - start_time
        time_bonus = max(0, int(15 - elapsed))

        if selected == "__skip__":
            feedback = f"⏭️ *Skipped!*\n\n✅ Correct Answer: *{correct}*"
        elif selected == correct:
            points = 1 + (1 if time_bonus > 10 else 0)
            context.user_data["score"] = context.user_data.get("score", 0) + points
            feedback = (
                f"✅ *Correct!* +{points} point{'s' if points > 1 else ''}\n"
                f"⚡ Time: *{elapsed:.1f}s*\n"
                f"✅ Answer: *{correct}*"
            )
        else:
            feedback = (
                f"❌ *Wrong!*\n"
                f"Your answer: {selected}\n"
                f"✅ Correct: *{correct}*"
            )

        await query.edit_message_text(
            f"❓ *Question {index + 1}/{len(QUESTIONS)}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{q['question']}\n\n"
            f"{feedback}",
            parse_mode="Markdown"
        )

        context.user_data["q_index"] = index + 1
        await send_question(update, context)

# ─── Show Result ──────────────────────────────────────────
async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    score = context.user_data.get("score", 0)
    total = len(QUESTIONS)
    user = update.effective_user

    # Update leaderboard
    update_leaderboard(user.id, user.first_name, score)

    if score == total:
        emoji = "🏆 Perfect Score! Genius!"
    elif score >= total * 0.7:
        emoji = "🥇 Excellent!"
    elif score >= total * 0.5:
        emoji = "👍 Good Job!"
    else:
        emoji = "😅 Keep Practicing!"

    text = (
        f"🎉 *Quiz Finished!*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Correct: *{score}*\n"
        f"❌ Wrong: *{total - score}*\n"
        f"📊 Score: *{score}/{total}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{emoji}"
    )
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="start_quiz")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
    ]

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ─── /leaderboard command ─────────────────────────────────
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = get_top_players()
    if not top:
        await update.message.reply_text("🏆 Leaderboard khali hai abhi!")
        return
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "🏆 *Top Players*\n━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(top):
        text += f"{medals[i]} *{p['username']}* — {p['score']} pts\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── Main ─────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CallbackQueryHandler(handle_answer))
    print("🤖 Quiz Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

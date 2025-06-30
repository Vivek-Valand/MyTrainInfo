import requests
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# Bot states
SOURCE, DESTINATION = range(2)

# Base API
API_BASE = "https://indian-railway-api.cyclic.app"

# 1️⃣ Handler: /start
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚉 Enter source station code (e.g. BRC):")
    return SOURCE

# 2️⃣ Source input
async def source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['source'] = update.message.text.strip().upper()
    await update.message.reply_text("🛤️ Enter destination station code (e.g. NDLS):")
    return DESTINATION

# 3️⃣ Destination & processing
async def destination(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    source = ctx.user_data['source']
    dest = update.message.text.strip().upper()
    await update.message.reply_text("🔄 Fetching trains that did *not* go today...")

    today = datetime.now().strftime("%d-%m-%Y")
    try:
        # Fetch trains between stations
        res = requests.get(f"{API_BASE}/GetTrainBtwStations", params={"from": source, "to": dest})
        res.raise_for_status()
        trains = res.json().get("trains", [])
    except Exception as e:
        return await update.message.reply_text(f"❌ Error fetching trains: {e}")

    # Fetch trains running today (for each train)
    bad_trains = []
    for t in trains:
        num = t.get("train_number") or t.get("TrainNo") or t.get("TrainNo")
        name = t.get("train_name") or t.get("TrainName") or t.get("TrainName")
        if not num:
            continue

        try:
            st = requests.get(f"{API_BASE}/GetTrainOnDate",
                              params={"train": num, "date": today})
            st.raise_for_status()
            data = st.json()
            # If status != 'RUNNING' or missing -> consider bad
            if data.get("current_status", "").upper() != "RUNNING":
                bad_trains.append(f"{num} – {name}")
        except:
            bad_trains.append(f"{num} – {name} (status unknown)")

    if not bad_trains:
        msg = "✅ All trains appear to have run today!"
    else:
        msg = "❌ These trains did *not* pass today:\n" + "\n".join(bad_trains)

    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END

# 4️⃣ Cancel
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Canceled. Use /start to begin again.")
    return ConversationHandler.END

# 5️⃣ Entry point
if __name__ == "__main__":
    app = ApplicationBuilder().token("7292174685:AAFLvwL4qh_KjGbddj3pZlVL-9f41uy-Iig").build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, source)],
            DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, destination)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    print("Bot is running...")
    app.run_polling()
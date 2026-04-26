import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

# --- KONFIGURATSIYA ---
TOKEN = "8735179134:AAFbrGdmSbq-lH7na7d7AhyhBRKe-FpXm2M" # BotFather'dan olingan
CHANNEL_ID = "@instagram_kasimov" # Masalan: @inst_kasimov
ADMIN_ID = 6052580480  # O'zingizning Telegram ID-ingiz
PRIZE_PHOTO = "https://t.me/instagram_gifts/6?single" # Yutuqlar rasmi linki

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            referrer_id INTEGER,
            points INTEGER DEFAULT 0,
            is_joined INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# --- MENU TUGMALARI ---
def main_menu():
    kb = [
        [KeyboardButton(text="YUTUQLAR 🎁"), KeyboardButton(text="STATISTIKA 📊")],
        [KeyboardButton(text="HAVOLA OLISH 🔗"), KeyboardButton(text="MA'LUMOT ℹ️")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- FUNKSIYALAR ---
async def is_member(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# --- HANDLERLAR ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    args = message.text.split()
    
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)", (user_id, name))
    
    # Referal tizimi
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        # O'zini o'zi taklif qilmasligi va birinchi marta kirayotganini tekshirish
        cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
        current_ref = cursor.fetchone()
        if ref_id != user_id and current_ref[0] is None:
            cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (ref_id, user_id))
    
    conn.commit()
    conn.close()

    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kanalga a'zo bo'lish 📢", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check_sub")]
    ])
    
    await message.answer(f"Salom {name}!\nTanlovda qatnashish uchun kanalimizga a'zo bo'ling va tasdiqlashni bosing.", reply_markup=btn)

@dp.callback_query(F.data == "check_sub")
async def callback_check(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await is_member(user_id):
        conn = sqlite3.connect("contest.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referrer_id, is_joined FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if user_data and user_data[1] == 0: # Hali ball berilmagan bo'lsa
            if user_data[0]: # Uni taklif qilgan odam bo'lsa
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (user_data[0],))
            cursor.execute("UPDATE users SET is_joined = 1 WHERE user_id = ?", (user_id, ))
            conn.commit()
        
        conn.close()
        await call.message.delete()
        await call.message.answer("Tabriklaymiz! Siz ro'yxatdan o'tdingiz.", reply_markup=main_menu())
    else:
        await call.answer("Siz hali kanalga a'zo emassiz!", show_alert=True)

@dp.message(F.text == "YUTUQLAR 🎁")
async def prizes(message: types.Message):
    text = (
        "🎁 **TANLOV YUTUQLARI**\n\n"
        "🥇 1-o'rin: [SIZNING SOVG'ANGIZ]\n"
        "🥈 2-o'rin: [SIZNING SOVG'ANGIZ]\n"
        "🥉 3-o'rin: [SIZNING SOVG'ANGIZ]\n\n"
        "💡 Takliflaringiz qancha ko'p bo'lsa, yutish ehtimoli shuncha yuqori!"
    )
    try:
        await message.answer_photo(photo=PRIZE_PHOTO, caption=text, parse_mode="Markdown")
    except:
        await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "STATISTIKA 📊")
async def statistics(message: types.Message):
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, points FROM users WHERE is_joined = 1 ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (message.from_user.id,))
    user_points = cursor.fetchone()[0]
    conn.close()

    res = "🏆 **TOP 10 ISHTIROKCHILAR**\n\n"
    for i, (name, p) in enumerate(top_users, 1):
        m = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
        res += f"{m} {name} — {p} ta taklif\n"
    
    res += f"\n👤 Sizning balingiz: **{user_points}**"
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "HAVOLA OLISH 🔗")
async def my_link(message: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(f"🔗 Taklif havolangiz:\n\n`{link}`\n\nUni do'stlaringizga yuboring!", parse_mode="Markdown")

@dp.message(F.text == "MA'LUMOT ℹ️")
async def info_msg(message: types.Message):
    await message.answer("ℹ️ Tanlov qoidalari:\n1. Kanalga a'zo bo'lish shart.\n2. Faqat real odamlarni taklif qiling.\n3. Stop deyilganda tanlov yakunlanadi.")

# --- ADMIN COMMANDS ---
@dp.message(Command("results"), F.from_user.id == ADMIN_ID)
async def admin_results(message: types.Message):
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, points FROM users WHERE is_joined = 1 ORDER BY points DESC LIMIT 3")
    winners = cursor.fetchall()
    conn.close()
    
    if winners:
        text = "🏁 **TANLOV YAKUNLANDI!**\n\n"
        for i, (uid, name, p) in enumerate(winners, 1):
            text += f"{i}-o'rin: {name} (ID: {uid}) - {p} ball\n"
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("Hozircha ishtirokchilar yo'q.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        

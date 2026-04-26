import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.payload import decode_payload

# SOZLAMALAR
TOKEN = "SIZNING_BOT_TOKENINGIZ" # BotFather'dan olingan
CHANNEL_ID = "@SIZNING_KANALINGIZ" # Masalan: @inst_kasimov
ADMIN_ID = 123456789  # O'zingizning ID-ingiz

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasi
def init_db():
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            points INTEGER DEFAULT 0,
            is_joined INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    
    # Referalni aniqlash
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ? AND referrer_id IS NULL", (ref_id, user_id))
    
    conn.commit()
    conn.close()
    
    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check")]
    ])
    
    await message.answer(f"Salom! Tanlovda qatnashish uchun kanalimizga a'zo bo'ling va tasdiqlash tugmasini bosing.", reply_markup=btn)

@dp.callback_query(F.data == "check")
async def verify(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await check_sub(user_id):
        conn = sqlite3.connect("contest.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referrer_id, is_joined FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        if res and res[1] == 0: # Agar yangi a'zo bo'lsa
            if res[0]: # Uni kimdir taklif qilgan bo'lsa
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (res[0],))
            cursor.execute("UPDATE users SET is_joined = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            
        bot_info = await bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        my_points = cursor.fetchone()[0]
        conn.close()
        
        await call.message.edit_text(
            f"✅ Tasdiqlandi!\n\nSizning balingiz: {my_points}\n"
            f"Sizning referal havolangiz:\n{link}\n\n"
            f"Shu havola orqali do'stlaringizni taklif qiling!"
        )
    else:
        await call.answer("Siz hali kanalga a'zo emassiz!", show_alert=True)

@dp.message(Command("top"))
async def leaderboard(message: types.Message):
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, points FROM users WHERE is_joined = 1 ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    
    text = "🏆 **Eng ko'p odam qo'shganlar:**\n\n"
    for i, (uid, p) in enumerate(rows, 1):
        text += f"{i}. ID: `{uid}` — {p} ta odam\n"
    await message.answer(text, parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    dp.run_polling(bot)
      

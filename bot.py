import logging
import sqlite3
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- KONFIGURATSIYA ---
TOKEN = "8735179134:AAGcVDl-X2INj0ZNVzkIcIGXeRmzplq8jF0"
CHANNEL_ID = "@instagram_kasimov"
ADMIN_ID = 6052580480 

PRIZE_POST_URL = "https://t.me/instagram_gifts/6?single"
RULES_POST_URL = "https://t.me/instagram_gifts/7"
SUPPORT_USER = "@xodim_aka"

# Railway Volume uchun ma'lumotlar bazasi yo'li
DB_PATH = "/app/data/contest.db"

# Agar papka mavjud bo'lmasa, yaratish
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
# Xabarlarni vaqtincha saqlash uchun MemoryStorage qo'shildi
dp = Dispatcher(storage=MemoryStorage())

# --- HOLATLAR (STATES) ---
class FeedbackState(StatesGroup):
    waiting_for_message = State()

# --- BAZA ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            referrer_id INTEGER,
            points INTEGER DEFAULT 0,
            is_joined INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# --- IXCHAM VA CHIROYLI MENYU ---
def main_menu():
    kb = [
        [KeyboardButton(text="🎁 Yutuqlar"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🔗 Havola")],
        [KeyboardButton(text="❗ Shartlar"), KeyboardButton(text="👨🏻‍💻 Hamkorlik")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

async def is_member(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    uname = message.from_user.username or "Noma'lum"
    args = message.text.split()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    
    if not existing_user:
        try:
            await bot.send_message(ADMIN_ID, f"🆕 **Yangi foydalanuvchi:**\n👤 {name}\n🆔 `{user_id}`\n🔗 @{uname}")
        except: pass
        
        cursor.execute("INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)", (user_id, name, uname))
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != user_id:
                cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (ref_id, user_id))
    
    conn.commit()
    conn.close()

    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_sub")]
    ])
    
    await message.answer(f"Assalomu alaykum **{name}**!\nTanlovda qatnashish uchun kanalga a'zo bo'ling:", reply_markup=btn, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def callback_check(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await is_member(user_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT referrer_id, is_joined FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        if res and res[1] == 0:
            if res[0]:
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (res[0],))
                try:
                    await bot.send_message(res[0], f"🎁 **Yangi a'zo qo'shildi!** Sizga 1 ball berildi.")
                except: pass
            cursor.execute("UPDATE users SET is_joined = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        conn.close()
        
        await call.message.delete()
        await call.message.answer("🎉 **Ro'yxatdan o'tdingiz!**\nMenyudan foydalanishingiz mumkin:", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await call.answer("❌ Kanalga a'zo emassiz!", show_alert=True)

@dp.message(F.text == "🎁 Yutuqlar")
async def prizes(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👀 Ko'rish", url=PRIZE_POST_URL)]])
    await message.answer("🎁 **Yutuqlar haqida ma'lumot:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "👤 Profil")
async def show_profile(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    points = res[0] if res else 0
    conn.close()
    await message.answer(f"👤 **Profilingiz**\n\n🆔 ID: `{message.from_user.id}`\n🏆 Ballaringiz: **{points} ta**", parse_mode="Markdown")

@dp.message(F.text == "📊 Statistika")
async def statistics(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, points FROM users WHERE is_joined = 1 ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()

    res = "🏆 **TOP 10 ISHTIROKCHILAR**\n\n"
    if top_users:
        for i, (name, p) in enumerate(top_users, 1):
            medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            res += f"{medal} {name} — **{p}**\n"
    else:
        res += "Hozircha ma'lumot yo'q."
    
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "❗ Shartlar")
async def rules(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📝 O'qish", url=RULES_POST_URL)]])
    await message.answer("❗ **Tanlov qoidalari:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🔗 Havola")
async def get_link(message: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"🔗 **Taklif havolangiz:**\n\n`{link}`\n\nDo'stlaringizga yuboring!", parse_mode="Markdown")

# --- HAMKORLIK VA HABAR QOLDIRISH ---
@dp.message(F.text == "👨🏻‍💻 Hamkorlik")
async def support(message: types.Message, state: FSMContext):
    await message.answer(
        "Hamkorlik va savollar bo'lsa @xodim_aka ga yozing! yoki shu yerda yozib qoldiring!👇",
        parse_mode="Markdown"
    )
    # Bot foydalanuvchidan xabar kutish rejimiga o'tadi
    await state.set_state(FeedbackState.waiting_for_message)

@dp.message(FeedbackState.waiting_for_message)
async def forward_feedback(message: types.Message, state: FSMContext):
    # Agar foydalanuvchi menyu tugmalarini bosib yuborsa, holatni bekor qilish
    if message.text in ["🎁 Yutuqlar", "👤 Profil", "📊 Statistika", "🔗 Havola", "❗ Shartlar", "👨🏻‍💻 Hamkorlik"]:
        await state.clear()
        return

    user = message.from_user
    # Xabarni adminga yo'naltirish
    admin_msg = (
        f"📩 **Yangi xabar keldi!**\n\n"
        f"👤 Kimdan: {user.full_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"🔗 Username: @{user.username or 'yoq'}\n\n"
        f"📝 **Xabar:**\n{message.text}"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        await message.answer("Rahmat! Xabaringiz adminga yetkazildi. ✅", reply_markup=main_menu())
    except Exception as e:
        await message.answer("Xabar yuborishda xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.")
        logging.error(f"Feedback error: {e}")
    
    # Xabar yuborilgach holatni tozalash
    await state.clear()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    

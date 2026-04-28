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
TOKEN = "8251656306:AAE9fplew22iEWQPFOZbVdVzoHMFttUQaM8"
CHANNELS = ["@instagram_kasimov", "@instagram_gifts"]
ADMIN_ID = 6052580480 

PRIZE_POST_URL = "https://t.me/instagram_gifts/18?single"
RULES_POST_URL = "https://t.me/instagram_gifts/20"
SUPPORT_USER = "@xodim_aka"

# Railway Volume ulanishi
DB_PATH = "/app/data/contest.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- HOLATLAR (STATES) ---
class FeedbackState(StatesGroup):
    waiting_for_message = State()

# --- MA'LUMOTLAR BAZASI ---
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

# --- ASOSIY MENYU ---
def main_menu():
    kb = [
        [KeyboardButton(text="🎁 Yutuqlar"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🔗 Havola")],
        [KeyboardButton(text="❗ Shartlar"), KeyboardButton(text="👨🏻‍💻 Hamkorlik")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- A'ZOLIKNI TEKSHIRISH ---
async def is_member(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True

def get_sub_buttons():
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"📢 {channel}ga a'zo bo'lish", url=f"https://t.me/{channel[1:]}")])
    buttons.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    uname = message.from_user.username or "yo'q"
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

    await message.answer(
        f"Assalomu alaykum **{name}**!\n\nTanlovda qatnashish uchun quyidagi kanallarga a'zo bo'ling 👇", 
        reply_markup=get_sub_buttons(), 
        parse_mode="Markdown"
    )

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
                    await bot.send_message(res[0], f"🎁 **Tabriklaymiz!** Taklifingiz muvaffaqiyatli qo'shildi. Sizga 1 ball berildi.")
                except: pass
            cursor.execute("UPDATE users SET is_joined = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        conn.close()
        
        await call.message.delete()
        await call.message.answer("🎉 **Ro'yxatdan o'tdingiz!**\n\nMenyudan foydalanishingiz mumkin:", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await call.answer("❌ Siz hali barcha kanallarga a'zo emassiz!", show_alert=True)

@dp.message(F.text == "🎁 Yutuqlar")
async def prizes(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👀 Ko'rish", url=PRIZE_POST_URL)]])
    await message.answer("🎁 **Tanlov yutuqlari haqida ma'lumot:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "👤 Profil")
async def show_profile(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    points = res[0] if res else 0
    conn.close()
    
    text = f"👤 **Profilingiz**\n\nIsm: `{message.from_user.full_name}`\nID: `{message.from_user.id}`\n🏆 **Ballar: {points}**"
    await message.answer(text, parse_mode="Markdown")

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
            res += f"{i}. {name} — **{p}** ball\n"
    else:
        res += "Hozircha ishtirokchilar yo'q."
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "❗ Shartlar")
async def rules(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📝 O'qish", url=RULES_POST_URL)]])
    await message.answer("❗ **Tanlov qoidalari:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🔗 Havola")
async def get_link(message: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"🔗 **Sizning havolangiz:**\n\n`{link}`\n\nDo'stlaringizga yuboring va ball to'plang!", parse_mode="Markdown")

# --- HAMKORLIK BO'LIMI (YANGILANGAN) ---

@dp.message(F.text == "👨🏻‍💻 Hamkorlik")
async def support(message: types.Message, state: FSMContext):
    await state.set_state(FeedbackState.waiting_for_message)
    await message.answer(
        f"👨🏻‍💻 **Hamkorlik bo'limi**\n\nSavollaringiz yoki takliflaringiz bo'lsa, pastdan yozib qoldiring. "
        f"Xabaringiz to'g'ridan-to'g'ri adminga boradi.\n\n"
        f"Shoshilinch bo'lsa: {SUPPORT_USER}",
        parse_mode="Markdown"
    )

@dp.message(FeedbackState.waiting_for_message)
async def forward_feedback(message: types.Message, state: FSMContext):
    # Agar foydalanuvchi yozish o'rniga boshqa menyu tugmasini bossa
    if message.text in ["🎁 Yutuqlar", "👤 Profil", "📊 Statistika", "🔗 Havola", "❗ Shartlar", "👨🏻‍💻 Hamkorlik"]:
        await state.clear()
        # Bu yerda o'sha bosilgan tugmani qayta ishlashga yuboramiz
        if message.text == "🎁 Yutuqlar": await prizes(message)
        elif message.text == "👤 Profil": await show_profile(message)
        elif message.text == "📊 Statistika": await statistics(message)
        elif message.text == "🔗 Havola": await get_link(message)
        elif message.text == "❗ Shartlar": await rules(message)
        elif message.text == "👨🏻‍💻 Hamkorlik": await support(message, state)
        return

    user = message.from_user
    try:
        # Adminga yuborish
        await bot.send_message(
            ADMIN_ID,
            f"📩 **YANGI MUROJAAT!**\n\n"
            f"👤 **Kimdan:** {user.full_name}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🔗 **Username:** @{user.username or 'yoq'}\n\n"
            f"📝 **Xabar:**\n{message.text}"
        )
        await message.answer("✅ **Xabaringiz adminga yuborildi!** Tez orada javob beramiz.", reply_markup=main_menu())
    except Exception as e:
        logging.error(f"Xabar yuborishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq qayta urunib ko'ring.")
    
    await state.clear()

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
            

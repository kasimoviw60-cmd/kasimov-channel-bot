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

# Kanallar ro'yxati
CHANNELS = [
    {"id": "@instagram_kasimov", "url": "https://t.me/instagram_kasimov"},
    {"id": "@instagram_gifts", "url": "https://t.me/instagram_gifts"},
    {"id": -1003783851677, "url": "https://t.me/+WSbBvewuj141MTli"} 
]
ADMIN_ID = 6052580480 

PRIZE_POST_URL = "https://t.me/instagram_gifts/18?single"
RULES_POST_URL = "https://t.me/instagram_gifts/20"
SUPPORT_USER = "@xodim_aka"

# Ma'lumotlar bazasi yo'li (Eski bazangizni o'qish uchun)
if os.path.exists("/app/data"):
    DB_PATH = "/app/data/contest.db"
else:
    DB_PATH = "contest.db"

os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- HOLATLAR ---
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
    # ESKI BALLARNI TIKLASH: Ballari bor foydalanuvchilarni is_joined = 1 qiladi
    cursor.execute("UPDATE users SET is_joined = 1 WHERE points > 0")
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

# --- A'ZOLIKNI TEKSHIRISH (YANGI PRIVATE KANAL UCHUN YENGILLIK) ---
async def is_member(user_id):
    # Siz aytganingizdek, bot zayavka rejimidagi kanallarni tekshirib o'tirmaydi.
    # Foydalanuvchi tugmani bosib qaytib kelgan bo'lsa - bo'ldi, u o'tadi.
    return True

def get_sub_buttons():
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=channel['url'])])
    
    buttons.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    name = message.from_user.full_name
    uname = message.from_user.username or "yo'q"
    args = message.text.split()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_joined FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    if not res:
        # Yangi foydalanuvchi bo'lsa bazaga qo'shish
        cursor.execute("INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)", (user_id, name, uname))
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != user_id:
                cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (ref_id, user_id))
        conn.commit()
        already_joined = 0
    else:
        already_joined = res[0]
    
    conn.close()

    if already_joined == 1:
        await message.answer(f"Xush kelibsiz **{name}**!", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await message.answer(
            f"Assalomu alaykum **{name}**!\n\nTanlovda qatnashish uchun quyidagi kanallarga a'zo bo'ling 👇", 
            reply_markup=get_sub_buttons(), 
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "check_sub")
async def callback_check(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT referrer_id, is_joined FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    if res and res[1] == 0:
        if res[0]:
            # Referal egasiga ball berish
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (res[0],))
            try:
                await bot.send_message(res[0], f"🎁 **Tabriklaymiz!** Taklifingiz muvaffaqiyatli qo'shildi. Sizga 1 ball berildi.")
            except: pass
        
        cursor.execute("UPDATE users SET is_joined = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    
    conn.close()
    
    await call.message.delete()
    await call.message.answer("🎉 **Muvaffaqiyatli ro'yxatdan o'tdingiz!**", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "🎁 Yutuqlar")
async def prizes(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ko'rish", url=PRIZE_POST_URL)]])
    await message.answer("🎁 **Yutuqlar haqida:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "👤 Profil")
async def show_profile(message: types.Message, state: FSMContext):
    await state.clear()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    points = res[0] if res else 0
    conn.close()
    await message.answer(f"👤 **Profilingiz**\n\nIsm: `{message.from_user.full_name}`\n🏆 **Ballar: {points}**", parse_mode="Markdown")

@dp.message(F.text == "📊 Statistika")
async def statistics(message: types.Message, state: FSMContext):
    await state.clear()
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
        res += "Ishtirokchilar topilmadi."
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "🔗 Havola")
async def get_link(message: types.Message, state: FSMContext):
    await state.clear()
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    share_url = f"https://t.me/share/url?url={link}&text=Tanlovda qatnashing!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Yuborish", url=share_url)]])
    await message.answer(f"🔗 **Havolangiz:**\n`{link}`", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "❗ Shartlar")
async def rules(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📝 Ko'rish", url=RULES_POST_URL)]])
    await message.answer("❗ **Shartlar:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text.contains("Hamkorlik"))
async def support(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(FeedbackState.waiting_for_message)
    await message.answer(f"👨🏻‍💻 Murojaat yozing yoki adminga murojaat qiling: {SUPPORT_USER}")

@dp.message(FeedbackState.waiting_for_message)
async def forward_feedback(message: types.Message, state: FSMContext):
    if message.text in ["🎁 Yutuqlar", "👤 Profil", "📊 Statistika", "🔗 Havola", "❗ Shartlar", "👨🏻‍💻 Hamkorlik"]:
        await state.clear()
        return
    try:
        await bot.send_message(ADMIN_ID, f"📩 **MUROJAAT:**\n👤 {message.from_user.full_name}\n📝 {message.text}")
        await message.answer("✅ Adminga yetkazildi.", reply_markup=main_menu())
    except:
        await message.answer("❌ Xatolik!")
    await state.clear()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pass
    

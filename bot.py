import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- KONFIGURATSIYA ---
TOKEN = "8735179134:AAGcVDl-X2INj0ZNVzkIcIGXeRmzplq8jF0"
CHANNEL_ID = "@instagram_kasimov"  # Masalan: @inst_kasimov
ADMIN_ID = 6052580480 # O'zingizning Telegram ID-ingiz (Raqamlarda)

# --- POST HAVOLALARI ---
PRIZE_POST_URL = "https://t.me/instagram_gifts/6?single"  # Yutuqlar haqida post linki
RULES_POST_URL = "https://t.me/instagram_gifts/7"  # Qoidalar haqida post linki
SUPPORT_USER = "@xodim_aka"                    # Murojaat va hamkorlik uchun

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
            username TEXT,
            referrer_id INTEGER,
            points INTEGER DEFAULT 0,
            is_joined INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# --- ASOSIY REPLIKATSIYA MENYUSI ---
def main_menu():
    kb = [
        [KeyboardButton(text="YUTUQLAR 🎁"), KeyboardButton(text="PROFIL 👤")],
        [KeyboardButton(text="STATISTIKA 📊"), KeyboardButton(text="HAVOLA OLISH 🔗")],
        [KeyboardButton(text="QOIDALAR ℹ️"), KeyboardButton(text="MUROJAAT VA HAMKORLIK 🤝")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- A'ZOLIKNI TEKSHIRISH FUNKSIYASI ---
async def is_member(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Tekshirishda xato: {e}")
        return False

# --- ASOSIY HANDLERLAR ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    uname = message.from_user.username or "Noma'lum"
    args = message.text.split()
    
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    
    if not existing_user:
        # Yangi odam haqida adminga bildirishnoma
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
        [InlineKeyboardButton(text="Kanalga a'zo bo'lish 📢", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check_sub")]
    ])
    
    await message.answer(f"Assalomu alaykum **{name}**!\n\nTanlovda qatnashish uchun kanalimizga a'zo bo'lishingiz shart. Keyin 'Tasdiqlash' tugmasini bosing 👇", reply_markup=btn, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def callback_check(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await is_member(user_id):
        conn = sqlite3.connect("contest.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referrer_id, is_joined FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        if res and res[1] == 0:
            if res[0]:
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (res[0],))
                try:
                    await bot.send_message(res[0], f"🎁 **Tabriklaymiz!** Sizning havolangiz orqali yangi a'zo qo'shildi. Sizga 1 ball berildi.")
                except: pass
            cursor.execute("UPDATE users SET is_joined = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        conn.close()
        
        await call.message.delete()
        await call.message.answer("🎉 **Muvaffaqiyatli ro'yxatdan o'tdingiz!**\n\nQuyidagi tugmalar orqali ballaringizni tekshirishingiz va havolangizni olishingiz mumkin:", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await call.answer("❌ Siz hali kanalga a'zo emassiz!", show_alert=True)

# --- TUGMALAR BILAN ISHLASH ---

@dp.message(F.text == "YUTUQLAR 🎁")
async def prizes(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yutuqlarni ko'rish 👀", url=PRIZE_POST_URL)]
    ])
    await message.answer("🎁 **Tanlov yutuqlari va sovg'alar haqida to'liq ma'lumot olish uchun quyidagi tugmani bosing:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "PROFIL 👤")
async def show_profile(message: types.Message):
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (message.from_user.id,))
    points = cursor.fetchone()[0]
    conn.close()
    
    text = (
        f"👤 **Sizning profilingiz**\n\n"
        f"📋 Ism: `{message.from_user.full_name}`\n"
        f"🆔 ID: `{message.from_user.id}`\n\n"
        f"🏆 **To'plangan ballaringiz: {points} ta**\n"
        f"💡 Ball yig'ish uchun 'HAVOLA OLISH' tugmasidan foydalaning."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "STATISTIKA 📊")
async def statistics(message: types.Message):
    conn = sqlite3.connect("contest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, points FROM users WHERE is_joined = 1 ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()

    res = "🏆 **TOP 10 ISHTIROKCHILAR**\n\n"
    if not top_users:
        res += "Hozircha ishtirokchilar yo'q."
    else:
        for i, (name, p) in enumerate(top_users, 1):
            medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            res += f"{medal} {name} — **{p}** ball\n"
    
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "QOIDALAR ℹ️")
async def rules(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qoidalarni o'qish 📝", url=RULES_POST_URL)]
    ])
    await message.answer("ℹ️ **Tanlov shartlari, g'oliblarni aniqlash tartibi va qoidalar bilan tanishish uchun tugmani bosing:**", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "HAVOLA OLISH 🔗")
async def get_link(message: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    text = (
        f"🔗 **Sizning taklif havolangiz:**\n\n`{link}`\n\n"
        f"👆 Ushbu havolani nusxalab do'stlaringizga yuboring. Har bir qo'shilgan a'zo uchun sizga 1 ball beriladi!"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "MUROJAAT VA HAMKORLIK 🤝")
async def support(message: types.Message):
    text = (
        f"🤝 **Murojaat va Hamkorlik**\n\n"
        f"Savollar, takliflar yoki reklama masalalari bo'yicha bizning managerga yozishingiz mumkin:\n\n"
        f"👤 Manager: {SUPPORT_USER}\n\n"
        f"🛑 _Iltimos, faqat muhim masalalar yuzasidan murojaat qiling!_"
    )
    await message.answer(text, parse_mode="Markdown")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        

import asyncio
import os
import random
import sqlite3
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN or TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("BOT_TOKEN را در فایل .env وارد کنید.")

DB = "game.db"
bot = Bot(TOKEN)
dp = Dispatcher()

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      user_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      coins INTEGER DEFAULT 100,
      xp INTEGER DEFAULT 0,
      wins INTEGER DEFAULT 0,
      games INTEGER DEFAULT 0,
      daily_at TEXT
    );
    CREATE TABLE IF NOT EXISTS groups(
      chat_id INTEGER PRIMARY KEY,
      title TEXT
    );
    """)
    con.commit()
    con.close()

def ensure_user(u):
    con = db()
    con.execute("""INSERT INTO users(user_id,name) VALUES(?,?)
                   ON CONFLICT(user_id) DO UPDATE SET name=excluded.name""",
                (u.id, u.full_name[:80]))
    con.commit()
    con.close()

def get_user(uid):
    con = db()
    row = con.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return row

def add_stats(uid, coins=0, xp=0, win=False):
    con = db()
    con.execute("""UPDATE users SET coins=coins+?, xp=xp+?, wins=wins+?, games=games+? WHERE user_id=?""",
                (coins, xp, int(win), 1, uid))
    con.commit(); con.close()

def main_kb():
    b = InlineKeyboardBuilder()
    b.button(text="👤 پروفایل / موجودی", callback_data="profile")
    b.button(text="🎮 بازی‌ها", callback_data="games")
    b.button(text="🏆 جدول امتیازات", callback_data="leaderboard")
    b.button(text="🎁 جایزه روزانه", callback_data="daily")
    b.button(text="🛍 فروشگاه", callback_data="shop")
    b.button(text="👥 بازی گروهی", callback_data="groupgame")
    b.button(text="📊 آمار من", callback_data="stats")
    b.button(text="❓ راهنما", callback_data="help")
    b.adjust(1,2,2,2,1)
    return b.as_markup()

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 برگشت به منو", callback_data="home")]
    ])

@dp.message(CommandStart())
async def start(m: Message):
    ensure_user(m.from_user)
    u = get_user(m.from_user.id)
    if m.chat.type in ("group","supergroup"):
        con=db(); con.execute("INSERT OR REPLACE INTO groups(chat_id,title) VALUES(?,?)",(m.chat.id,m.chat.title or "گروه")); con.commit(); con.close()
    text = (
        f"سلام {m.from_user.first_name} 👋\n\n"
        f"💰 موجودی: {u['coins']} سکه\n"
        f"⭐ امتیاز: {u['xp']}\n"
        f"🏆 بردها: {u['wins']}\n\n"
        "از منوی زیر انتخاب کن:"
    )
    await m.answer(text, reply_markup=main_kb())

@dp.callback_query(F.data=="home")
async def home(c: CallbackQuery):
    ensure_user(c.from_user)
    u=get_user(c.from_user.id)
    await c.message.edit_text(
        f"سلام {c.from_user.first_name} 👋\n\n💰 موجودی: {u['coins']} سکه\n⭐ امتیاز: {u['xp']}\n🏆 بردها: {u['wins']}\n\nاز منوی زیر انتخاب کن:",
        reply_markup=main_kb())
    await c.answer()

@dp.callback_query(F.data=="profile")
async def profile(c: CallbackQuery):
    u=get_user(c.from_user.id)
    await c.message.edit_text(
        f"👤 پروفایل {u['name']}\n\n💰 سکه: {u['coins']}\n⭐ XP: {u['xp']}\n🏆 برد: {u['wins']}\n🎮 بازی: {u['games']}",
        reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="stats")
async def stats(c: CallbackQuery):
    u=get_user(c.from_user.id)
    rate=(u['wins']/u['games']*100) if u['games'] else 0
    await c.message.edit_text(
        f"📊 آمار شما\n\n🎮 تعداد بازی: {u['games']}\n🏆 برد: {u['wins']}\n📈 نرخ برد: {rate:.0f}%\n⭐ XP: {u['xp']}",
        reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="games")
async def games(c: CallbackQuery):
    b=InlineKeyboardBuilder()
    b.button(text="🔢 حدس عدد",callback_data="guess")
    b.button(text="✊ سنگ کاغذ قیچی",callback_data="rps")
    b.button(text="🧠 اطلاعات عمومی",callback_data="quiz")
    b.button(text="🎨 حدس ایموجی",callback_data="emoji")
    b.button(text="👥 مسابقه گروهی",callback_data="groupgame")
    b.button(text="🔙 برگشت",callback_data="home")
    b.adjust(2,2,1,1)
    await c.message.edit_text("🎮 بازی موردنظرت را انتخاب کن:",reply_markup=b.as_markup()); await c.answer()

@dp.callback_query(F.data=="guess")
async def guess(c: CallbackQuery):
    n=random.randint(1,5)
    b=InlineKeyboardBuilder()
    for i in range(1,6): b.button(text=str(i),callback_data=f"g:{n}:{i}")
    b.button(text="🔙 برگشت",callback_data="games"); b.adjust(5,1)
    await c.message.edit_text("🔢 یک عدد از ۱ تا ۵ حدس بزن:",reply_markup=b.as_markup()); await c.answer()

@dp.callback_query(F.data.startswith("g:"))
async def guess_answer(c: CallbackQuery):
    _,n,g=c.data.split(":"); n=int(n); g=int(g)
    if n==g:
        add_stats(c.from_user.id,50,10,True)
        txt=f"🎉 درست گفتی! عدد {n} بود.\n💰 +50 سکه"
    else:
        add_stats(c.from_user.id,5,1,False)
        txt=f"❌ اشتباه بود! عدد {n} بود.\n💰 +5 سکه"
    await c.message.edit_text(txt,reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="rps")
async def rps(c: CallbackQuery):
    b=InlineKeyboardBuilder()
    for x,t in [("rock","🪨 سنگ"),("paper","📄 کاغذ"),("scissors","✂️ قیچی")]:
        b.button(text=t,callback_data=f"rps:{x}")
    b.button(text="🔙 برگشت",callback_data="games"); b.adjust(3,1)
    await c.message.edit_text("✊ انتخابت را بزن:",reply_markup=b.as_markup()); await c.answer()

@dp.callback_query(F.data.startswith("rps:"))
async def rps_answer(c: CallbackQuery):
    mine=c.data.split(":")[1]; botc=random.choice(["rock","paper","scissors"])
    names={"rock":"🪨 سنگ","paper":"📄 کاغذ","scissors":"✂️ قیچی"}
    win=(mine,botc) in [("rock","scissors"),("paper","rock"),("scissors","paper")]
    draw=mine==botc
    if draw: add_stats(c.from_user.id,10,2); result="مساوی 😐\n💰 +10 سکه"
    elif win: add_stats(c.from_user.id,40,8,True); result="بردی! 🎉\n💰 +40 سکه"
    else: add_stats(c.from_user.id,3,1); result="باختی 😄\n💰 +3 سکه"
    await c.message.edit_text(f"تو: {names[mine]}\nربات: {names[botc]}\n\n{result}",reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="quiz")
async def quiz(c: CallbackQuery):
    questions=[("پایتخت ایران کدام است؟",["تهران","شیراز","تبریز","مشهد"],0),
               ("۲+۳×۲ چند می‌شود؟",["10","8","7","12"],2),
               ("بزرگ‌ترین سیاره منظومه شمسی؟",["زمین","مریخ","مشتری","زحل"],2)]
    q=random.choice(questions)
    b=InlineKeyboardBuilder()
    for i,a in enumerate(q[1]): b.button(text=a,callback_data=f"quiz:{q[2]}:{i}")
    b.button(text="🔙 برگشت",callback_data="games"); b.adjust(2,2,1)
    await c.message.edit_text("🧠 "+q[0],reply_markup=b.as_markup()); await c.answer()

@dp.callback_query(F.data.startswith("quiz:"))
async def quiz_answer(c: CallbackQuery):
    _,correct,g=c.data.split(":"); correct=int(correct); g=int(g)
    if correct==g:
        add_stats(c.from_user.id,35,7,True); txt="🎉 پاسخ درست!\n💰 +35 سکه"
    else:
        add_stats(c.from_user.id,4,1); txt="❌ پاسخ اشتباه بود.\n💰 +4 سکه"
    await c.message.edit_text(txt,reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="emoji")
async def emoji(c: CallbackQuery):
    items=[("🍎📱","آیفون"),("🌧️☂️","باران"),("🔥🐦","ققنوس"),("🌙⭐","شب")]
    em,ans=random.choice(items)
    b=InlineKeyboardBuilder()
    for a in ["آیفون","باران","ققنوس","شب"]: b.button(text=a,callback_data=f"em:{ans}:{a}")
    b.button(text="🔙 برگشت",callback_data="games"); b.adjust(2,2,1)
    await c.message.edit_text(f"🎨 این ایموجی‌ها چی رو نشون میدن؟\n\n{em}",reply_markup=b.as_markup()); await c.answer()

@dp.callback_query(F.data.startswith("em:"))
async def emoji_answer(c: CallbackQuery):
    _,ans,g=c.data.split(":")
    if ans==g: add_stats(c.from_user.id,30,6,True); txt="🎉 درست!\n💰 +30 سکه"
    else: add_stats(c.from_user.id,4,1); txt="❌ اشتباه!\n💰 +4 سکه"
    await c.message.edit_text(txt,reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="leaderboard")
async def leaderboard(c: CallbackQuery):
    con=db(); rows=con.execute("SELECT name,xp,wins FROM users ORDER BY xp DESC LIMIT 10").fetchall(); con.close()
    text="🏆 جدول امتیازات\n\n"
    for i,r in enumerate(rows,1): text += f"{i}. {r['name']} — ⭐ {r['xp']} | 🏆 {r['wins']}\n"
    await c.message.edit_text(text,reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="daily")
async def daily(c: CallbackQuery):
    u=get_user(c.from_user.id); today=date.today().isoformat()
    if u["daily_at"]==today:
        txt="🎁 جایزه امروز را قبلاً گرفتی. فردا دوباره بیا!"
    else:
        con=db(); con.execute("UPDATE users SET coins=coins+100,daily_at=? WHERE user_id=?",(today,c.from_user.id)); con.commit(); con.close()
        txt="🎁 جایزه روزانه دریافت شد!\n💰 +100 سکه"
    await c.message.edit_text(txt,reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="shop")
async def shop(c: CallbackQuery):
    await c.message.edit_text(
        "🛍 فروشگاه\n\n"
        "فعلاً آیتم‌های نمایشی داریم.\n"
        "در نسخه بعدی می‌توانیم قاب پروفایل، عنوان، ایموجی ویژه و آیتم‌های تزئینی اضافه کنیم.",
        reply_markup=back_kb()); await c.answer()

@dp.callback_query(F.data=="groupgame")
async def groupgame(c: CallbackQuery):
    if c.message.chat.type not in ("group","supergroup"):
        await c.answer("این گزینه را داخل گروه اجرا کن.",show_alert=True); return
    await c.message.answer(
        "👥 مسابقه گروهی شروع شد!\n\n"
        "هرکس می‌خواهد شرکت کند روی دکمه زیر بزند.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 شرکت در مسابقه",callback_data="join")]
        ]))
    await c.answer()

@dp.callback_query(F.data=="join")
async def join(c: CallbackQuery):
    await c.answer("ثبت شد! وقتی بازی کامل شود شروع می‌کنیم 🎮",show_alert=True)

@dp.callback_query(F.data=="help")
async def help_(c: CallbackQuery):
    await c.message.edit_text(
        "❓ راهنما\n\n"
        "این ربات برای بازی و سرگرمی ساخته شده.\n"
        "• در چت خصوصی از منوی بازی‌ها استفاده کن.\n"
        "• ربات را به گروه اضافه کن تا مسابقه گروهی داشته باشید.\n"
        "• سکه‌ها مجازی هستند و ارزش پولی ندارند.\n"
        "• جدول امتیازات بر اساس XP مرتب می‌شود.",
        reply_markup=back_kb()); await c.answer()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())

import asyncio
import os
import aiohttp
import re
from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command as Cmd
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from downloader.models import TikTokVideo, TikTokAuthor, DownloadHistory, UserProfile
from dotenv import load_dotenv

load_dotenv()

class AuthState(StatesGroup):
    login = State()
    password = State()
    is_register = State()

@sync_to_async
def get_user_by_tg(tg_id):
    try: return UserProfile.objects.get(telegram_id=str(tg_id)).user
    except: return None

@sync_to_async
def create_user(username, password, tg_id):
    if User.objects.filter(username=username).exists(): return None
    u = User.objects.create_user(username, password=password)
    UserProfile.objects.create(user=u, telegram_id=str(tg_id))
    return u

@sync_to_async
def login_user(username, password, tg_id):
    u = authenticate(username=username, password=password)
    if u:
        UserProfile.objects.get_or_create(user=u, defaults={'telegram_id': str(tg_id)})
        p = u.profile
        p.telegram_id = str(tg_id)
        p.save()
    return u

@sync_to_async
def logout_user(tg_id):
    UserProfile.objects.filter(telegram_id=str(tg_id)).delete()

@sync_to_async
def save_history(user, url, data):
    def clean(val, limit): return (str(val[0]) if isinstance(val, list) else str(val))[:limit]
    author = clean(data.get("author", "U"), 490)
    title = clean(data.get("description", "V"), 990)
    
    a_obj, _ = TikTokAuthor.objects.get_or_create(username=author)
    v_obj, _ = TikTokVideo.objects.update_or_create(
        original_url=url, defaults={'title': title, 'author': a_obj}
    )
    if user:
        DownloadHistory.objects.create(user=user, video=v_obj)
        return True
    return False

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_kb(user):
    kb = []
    if user:
        kb.append([KeyboardButton(text=f"👤 {user.username}"), KeyboardButton(text="🚪 Вийти")])
    else:
        kb.append([KeyboardButton(text="🔐 Вхід"), KeyboardButton(text="📝 Реєстрація")])
    kb.append([KeyboardButton(text="❓ Допомога")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Cmd("start"))
async def start(m: types.Message):
    user = await get_user_by_tg(m.chat.id)
    await m.answer("👋 <b>TikRip Bot</b>\nКидай посилання!", parse_mode="HTML", reply_markup=get_kb(user))

@dp.message(F.text.in_({"📝 Реєстрація", "🔐 Вхід"}))
async def auth_start(m: types.Message, state: FSMContext):
    await state.update_data(is_reg=(m.text == "📝 Реєстрація"))
    await m.answer("Введіть <b>Логін</b>:", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthState.login)

@dp.message(AuthState.login)
async def auth_login(m: types.Message, state: FSMContext):
    await state.update_data(login=m.text)
    await m.answer("Введіть <b>Пароль</b>:", parse_mode="HTML")
    await state.set_state(AuthState.password)

@dp.message(AuthState.password)
async def auth_pass(m: types.Message, state: FSMContext):
    data = await state.get_data()
    if data['is_reg']:
        user = await create_user(data['login'], m.text, m.chat.id)
        msg = "✅ Створено!" if user else "❌ Логін зайнятий."
    else:
        user = await login_user(data['login'], m.text, m.chat.id)
        msg = "✅ Вхід успішний!" if user else "❌ Невірні дані."
    
    await m.answer(msg, reply_markup=get_kb(user))
    await state.clear()

@dp.message(F.text == "🚪 Вийти")
async def logout_h(m: types.Message):
    await logout_user(m.chat.id)
    await m.answer("Вийшли.", reply_markup=get_kb(None))

@dp.message(F.text.contains("tiktok.com"))
async def download(m: types.Message):
    user = await get_user_by_tg(m.chat.id)
    status = await m.answer("⏳ ...")
    try:
        async with aiohttp.ClientSession() as sess:
            API_KEY = os.getenv("RAPID_API_KEY")
            API_HOST = os.getenv("RAPID_API_HOST")
            async with sess.get(os.getenv("RAPID_API_URL"), headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}, params={"url": m.text}) as r:
                data = await r.json()
            
            link = data.get("hdplay") or data.get("play") or data["video"][0]
            async with sess.get(link) as f:
                b = await f.read()
            
            saved = await save_history(user, m.text, data)
            await status.delete()
            await m.answer_video(BufferedInputFile(b, "video.mp4"), caption="✅ Збережено" if saved else "⚠️ Анонімно", reply_markup=get_kb(user))
    except Exception as e:
        await status.edit_text("Помилка.")

class Command(BaseCommand):
    help = 'Run Bot'
    def handle(self, *args, **options):
        asyncio.run(dp.start_polling(bot))
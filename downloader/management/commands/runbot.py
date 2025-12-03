# downloader/management/commands/runbot.py
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

# --- СТАНИ ---
class AuthState(StatesGroup):
    login = State()
    password = State()
    is_register = State()

# --- ВАЛІДАТОР ЛОГІНА ---
def is_valid_username(username):
    pattern = r"^[a-zA-Z0-9_]{4,20}$"
    return re.match(pattern, username) is not None

# --- DB HELPERS ---
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
def save_to_history(user, url, data):
    def clean(val, limit): return (str(val[0]) if isinstance(val, list) else str(val))[:limit]
    
    auth = clean(data.get("author", "Unk"), 490)
    tit = clean(data.get("description", "Vid"), 990)
    
    a_obj, _ = TikTokAuthor.objects.get_or_create(username=auth)
    v_obj, _ = TikTokVideo.objects.update_or_create(
        original_url=url, defaults={'title': tit, 'author': a_obj}
    )
    
    if user:
        DownloadHistory.objects.create(user=user, video=v_obj)
        return True
    return False

# --- BOT SETUP ---
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

# --- HANDLERS ---

@dp.message(Cmd("start"))
async def start(m: types.Message):
    user = await get_user_by_tg(m.chat.id)
    await m.answer("👋 <b>TikRip Bot</b>\nКидай посилання!", parse_mode="HTML", reply_markup=get_kb(user))

@dp.message(F.text.in_({"📝 Реєстрація", "🔐 Вхід"}))
async def auth_start(m: types.Message, state: FSMContext):
    await state.update_data(is_reg=(m.text == "📝 Реєстрація"))
    await m.answer("Введіть <b>Логін</b> (лат.):", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthState.login)

@dp.message(AuthState.login)
async def auth_login(m: types.Message, state: FSMContext):
    login = m.text.strip()
    if not is_valid_username(login):
        await m.answer("❌ <b>Невірний формат!</b>\nТільки a-z, 0-9, мін. 4 символи.", parse_mode="HTML")
        return
    await state.update_data(login=login)
    await m.answer("Введіть <b>Пароль</b>:", parse_mode="HTML")
    await state.set_state(AuthState.password)

@dp.message(AuthState.password)
async def auth_pass(m: types.Message, state: FSMContext):
    password = m.text.strip()
    if len(password) < 6:
        await m.answer("❌ Пароль закороткий (мін. 6).")
        return

    data = await state.get_data()
    user = None
    
    if data['is_reg']:
        user = await create_user(data['login'], password, m.chat.id)
        msg = "✅ Акаунт створено!" if user else "❌ Логін зайнятий."
    else:
        user = await login_user(data['login'], password, m.chat.id)
        msg = "✅ Вхід успішний!" if user else "❌ Невірні дані."
    
    await m.answer(msg, reply_markup=get_kb(user))
    await state.clear()

@dp.message(F.text == "🚪 Вийти")
async def logout_handler(m: types.Message):
    await logout_user(m.chat.id)
    await m.answer("Ви вийшли.", reply_markup=get_kb(None))

@dp.message(F.text == "❓ Допомога")
async def help_handler(m: types.Message):
    await m.answer("Я скачаю відео в оригінальній якості (HD).")

@dp.message(F.text.contains("tiktok.com"))
async def download(m: types.Message):
    user = await get_user_by_tg(m.chat.id)
    status = await m.answer("⏳ Завантаження HD...")
    
    try:
        API_KEY = os.getenv("RAPID_API_KEY")
        API_HOST = os.getenv("RAPID_API_HOST")
        API_URL = os.getenv("RAPID_API_URL")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}, params={"url": m.text}) as resp:
                data = await resp.json()
            
            # Перевірка на помилки
            if "video" not in data and "hdplay" not in data:
                await status.edit_text("❌ Відео не знайдено.")
                return
            
            # --- ЛОГІКА ВИБОРУ НАЙКРАЩОЇ ЯКОСТІ ---
            link = None
            
            # 1. Пробуємо HD посилання
            if data.get("hdplay"):
                link = data["hdplay"]
            
            # 2. Пробуємо звичайне (без водяного знаку)
            elif data.get("play"):
                link = data["play"]
            
            # 3. Пробуємо зі списку
            elif "video" in data:
                video_list = data["video"]
                link = video_list[0] if isinstance(video_list, list) else video_list
            
            if not link:
                await status.edit_text("❌ Помилка отримання посилання.")
                return
            
            # Скачування
            async with session.get(link) as v_resp:
                v_bytes = await v_resp.read()
            
            # Збереження
            saved = await save_to_history(user, m.text, data)
            
            # Відправка
            caption = "✅ Збережено в архів" if saved else "⚠️ Анонімно (без історії)"
            await status.delete()
            await m.answer_video(BufferedInputFile(v_bytes, "video.mp4"), caption=caption, reply_markup=get_kb(user))

    except Exception as e:
        print(f"Bot Error: {e}")
        await status.edit_text("Помилка завантаження.")

class Command(BaseCommand):
    help = 'Run Async Bot'
    def handle(self, *args, **options):
        asyncio.run(dp.start_polling(bot))
# downloader/management/commands/runbot.py

import telebot
import os
import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from downloader.models import TikTokVideo, TikTokAuthor, DownloadHistory, UserProfile
from dotenv import load_dotenv
from telebot import types

load_dotenv()

class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **options):
        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        API_KEY = os.getenv("RAPID_API_KEY")
        API_HOST = os.getenv("RAPID_API_HOST")
        API_URL = os.getenv("RAPID_API_URL")

        if not TOKEN or not API_KEY:
            print("❌ ПОМИЛКА: Не знайдено токени в .env файлі!")
            return

        bot = telebot.TeleBot(TOKEN)
        print("Бот TikRip запущено...")

        # --- СТАРТ І МЕНЮ ---
        @bot.message_handler(commands=['start'])
        def send_welcome(message):
            if UserProfile.objects.filter(telegram_id=str(message.chat.id)).exists():
                bot.send_message(message.chat.id, "👋 Привіт! Ти вже в системі. Кидай посилання!")
                return

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton("📝 Реєстрація"), types.KeyboardButton("🔗 Підключити існуючий акаунт"))
            
            bot.send_message(message.chat.id, "Привіт! Обери дію:", reply_markup=markup)

        # --- РЕЄСТРАЦІЯ ---
        @bot.message_handler(func=lambda m: m.text == "📝 Реєстрація")
        def reg_start(message):
            msg = bot.send_message(message.chat.id, "Введіть новий <b>Логін</b>:", parse_mode="HTML")
            bot.register_next_step_handler(msg, reg_login)

        def reg_login(message):
            username = message.text.strip()
            if User.objects.filter(username=username).exists():
                bot.send_message(message.chat.id, "❌ Логін зайнятий. Тисни /start")
                return
            msg = bot.send_message(message.chat.id, "Введіть <b>Пароль</b>:", parse_mode="HTML")
            bot.register_next_step_handler(msg, reg_password, username)

        def reg_password(message, username):
            try:
                user = User.objects.create_user(username=username, password=message.text.strip())
                UserProfile.objects.create(user=user, telegram_id=str(message.chat.id))
                bot.send_message(message.chat.id, "✅ Реєстрація успішна! Кидай відео.", reply_markup=types.ReplyKeyboardRemove())
            except Exception as e:
                bot.send_message(message.chat.id, f"Помилка: {e}")

        # --- ВХІД ---
        @bot.message_handler(func=lambda m: m.text == "🔗 Підключити існуючий акаунт")
        def login_start(message):
            msg = bot.send_message(message.chat.id, "Введіть ваш <b>Логін</b>:", parse_mode="HTML")
            bot.register_next_step_handler(msg, login_username)

        def login_username(message):
            msg = bot.send_message(message.chat.id, "Введіть ваш <b>Пароль</b>:", parse_mode="HTML")
            bot.register_next_step_handler(msg, login_password, message.text.strip())

        def login_password(message, username):
            user = authenticate(username=username, password=message.text.strip())
            if user:
                UserProfile.objects.get_or_create(user=user, defaults={'telegram_id': str(message.chat.id)})
                # Оновлюємо ID якщо профіль вже був
                p = user.profile
                p.telegram_id = str(message.chat.id)
                p.save()
                bot.send_message(message.chat.id, f"✅ Вхід успішний, {user.username}!", reply_markup=types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.chat.id, "❌ Невірні дані. /start")

        # --- ОБРОБКА ВІДЕО (ТУТ ВІДБУВАЄТЬСЯ СКАЧУВАННЯ) ---
        @bot.message_handler(func=lambda message: True)
        def handle_video(message):
            url = message.text.strip()
            
            if "tiktok.com" not in url:
                bot.reply_to(message, "Це не TikTok посилання. 🧐")
                return

            # Перевірка авторизації
            try:
                profile = UserProfile.objects.get(telegram_id=str(message.chat.id))
                user = profile.user
            except UserProfile.DoesNotExist:
                bot.send_message(message.chat.id, "🔒 Спочатку увійдіть або зареєструйтесь! /start")
                return

            status_msg = bot.reply_to(message, "🔎 Шукаю відео...")

            try:
                # 1. Отримуємо пряме посилання через API
                querystring = {"url": url}
                headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
                response = requests.get(API_URL, headers=headers, params=querystring)
                data = response.json()

                if "video" not in data:
                    bot.edit_message_text("❌ API не повернуло відео.", message.chat.id, status_msg.message_id)
                    return

                video_list = data["video"]
                download_link = video_list[0] if isinstance(video_list, list) else video_list

                # 2. СКАЧУВАННЯ (ОСЬ ЦЕЙ МОМЕНТ)
                bot.edit_message_text("⬇️ Завантажую файл на сервер...", message.chat.id, status_msg.message_id)
                
                # requests.get().content завантажує байти відео в змінну video_content
                video_content = requests.get(download_link).content

                # 3. ЗБЕРЕЖЕННЯ В БД
                bot.edit_message_text("💾 Записую в Базу Даних...", message.chat.id, status_msg.message_id)
                
                author_name = "Unknown"
                if "author" in data:
                     author_raw = data["author"]
                     author_name = author_raw[0] if isinstance(author_raw, list) else str(author_raw)
                
                title = "TikTok Video"
                if "description" in data:
                    desc_raw = data["description"]
                    title = desc_raw[0] if isinstance(desc_raw, list) else str(desc_raw)

                author_obj, _ = TikTokAuthor.objects.get_or_create(username=author_name)
                video_obj, _ = TikTokVideo.objects.update_or_create(
                    original_url=url,
                    defaults={'title': title[:490], 'author': author_obj}
                )
                DownloadHistory.objects.create(user=user, video=video_obj)

                # 4. ВІДПРАВКА В ТЕЛЕГРАМ
                bot.edit_message_text("🚀 Відправляю тобі...", message.chat.id, status_msg.message_id)
                
                caption = f"🎬 {title}\n👤 {author_name}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("📂 Мій Кабінет", url="http://127.0.0.1:8000/cabinet/"))

                # bot.send_video приймає байти (video_content) і відправляє їх як файл
                bot.send_video(message.chat.id, video_content, caption=caption, reply_markup=markup)
                
                # Видаляємо повідомлення про статус
                bot.delete_message(message.chat.id, status_msg.message_id)

            except Exception as e:
                print(f"Error: {e}")
                bot.edit_message_text(f"Помилка: {e}", message.chat.id, status_msg.message_id)

        bot.infinity_polling()
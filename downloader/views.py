# downloader/views.py

import os
import requests
from dotenv import load_dotenv

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _ 

from .forms import CustomUserCreationForm
# Імпортуємо всі три моделі
from .models import DownloadHistory, TikTokAuthor, TikTokVideo

load_dotenv()

API_KEY = os.getenv("RAPID_API_KEY")
API_HOST = os.getenv("RAPID_API_HOST")
API_URL = os.getenv("RAPID_API_URL")

# --- РЕЄСТРАЦІЯ ---
def register_view(request):
    if request.user.is_authenticated:
        return redirect('cabinet')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'downloader/register.html', {'form': form})

# --- ГОЛОВНА ЛОГІКА ---
def home_view(request):
    video_url = request.GET.get('url')

    if video_url:
        # Перевірка на фото-галерею
        if "/photo/" in video_url:
            messages.error(request, _("Це посилання на фото-галерею. Цей сервіс завантажує тільки відео."))
            return render(request, 'downloader/home.html')

        if not API_KEY:
            messages.error(request, _("API ключ не знайдено."))
            return render(request, 'downloader/home.html')

        try:
            querystring = {"url": video_url}
            headers = {
                "x-rapidapi-key": API_KEY,
                "x-rapidapi-host": API_HOST
            }

            response = requests.get(API_URL, headers=headers, params=querystring)
            data = response.json()

            # Перевіряємо відповідь API
            if "video" not in data:
                messages.error(request, _("Не вдалося отримати дані. Перевірте посилання."))
                return render(request, 'downloader/home.html')

            # Отримуємо посилання на відео
            video_list = data["video"]
            if isinstance(video_list, list) and len(video_list) > 0:
                download_link = video_list[0]
            elif isinstance(video_list, str):
                download_link = video_list
            else:
                download_link = None

            if not download_link:
                if data.get("images_count", 0) > 0:
                    messages.error(request, _("Вибачте, завантаження фото-слайдшоу поки не підтримується."))
                else:
                    messages.error(request, _("Не вдалося знайти посилання на відеофайл."))
                return render(request, 'downloader/home.html')

            # Завантажуємо відео у пам'ять
            video_content = requests.get(download_link).content
            
            # --- РОБОТА З БАЗОЮ ДАНИХ (Нормалізація) ---
            if request.user.is_authenticated:
                # 1. Витягуємо дані (Автор, Назва, Обкладинка)
                # API повертає списки ['текст'], тому беремо [0] елемент
                
                author_raw = data.get("author", ["Unknown"])
                author_name = author_raw[0] if isinstance(author_raw, list) and author_raw else str(author_raw)

                desc_raw = data.get("description", [])
                title = desc_raw[0] if isinstance(desc_raw, list) and desc_raw else str(desc_raw)
                if not title: title = "TikTok Video"

                cover_raw = data.get("cover", [])
                cover_url = cover_raw[0] if isinstance(cover_raw, list) and cover_raw else str(cover_raw)

                # 2. Створюємо або беремо існуючого Автора
                author_obj, _created = TikTokAuthor.objects.get_or_create(
                    username=author_name
                )

                # 3. Створюємо або беремо існуюче Відео
                # update_or_create зручно, якщо назва відео змінилася, але url той самий
                video_obj, _created = TikTokVideo.objects.update_or_create(
                    original_url=video_url,
                    defaults={
                        'title': title[:490], # Обрізаємо до ліміту БД
                        'author': author_obj,
                        'cover_image': cover_url
                    }
                )

                # 4. Записуємо факт завантаження в історію
                DownloadHistory.objects.create(
                    user=request.user,
                    video=video_obj
                )

            # Віддаємо файл
            response = HttpResponse(video_content, content_type="video/mp4")
            response['Content-Disposition'] = 'attachment; filename="tiktok_video.mp4"'
            return response

        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, _("Сталася технічна помилка при завантаженні."))
            return render(request, 'downloader/home.html')

    return render(request, 'downloader/home.html')

# --- КАБІНЕТ ---
@login_required
def cabinet_view(request):
    # select_related оптимізує запит до БД (робить JOIN таблиць)
    history = DownloadHistory.objects.filter(user=request.user).select_related('video', 'video__author').order_by('-download_date')
    
    total_downloads = history.count()
    
    context = {
        'history': history,
        'total_downloads': total_downloads
    }
    return render(request, 'downloader/cabinet.html', context)

# --- ВИХІД (Щоб не було помилки 405) ---
def custom_logout_view(request):
    logout(request)
    return render(request, 'downloader/logout.html')
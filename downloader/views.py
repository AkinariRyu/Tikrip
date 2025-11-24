import os
import requests
from dotenv import load_dotenv

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from .models import DownloadHistory

load_dotenv()

API_KEY = os.getenv("RAPID_API_KEY")
API_HOST = os.getenv("RAPID_API_HOST")
API_URL = os.getenv("RAPID_API_URL")

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

def home_view(request):
    video_url = request.GET.get('url')

    if video_url:
        if not API_KEY:
            messages.error(request, "Помилка: API ключ не знайдено в .env файлі.")
            return render(request, 'downloader/home.html')

        try:
            querystring = {"url": video_url}
            headers = {
                "x-rapidapi-key": API_KEY,
                "x-rapidapi-host": API_HOST
            }

            response = requests.get(API_URL, headers=headers, params=querystring)
            data = response.json()

            if "data" not in data or not isinstance(data["data"], dict):
                messages.error(request, "Не вдалося отримати дані. Перевірте посилання.")
                return render(request, 'downloader/home.html')

            video_data = data["data"]
            
            download_link = video_data.get("play")
            
            if not download_link:
                messages.error(request, "API не повернуло посилання на відео.")
                return render(request, 'downloader/home.html')

            video_content = requests.get(download_link).content
            
            if request.user.is_authenticated:
                title = video_data.get("title") or video_data.get("description") or "Відео TikTok"
                
                if len(title) > 100:
                    title = title[:97] + "..."
                
                DownloadHistory.objects.create(
                    user=request.user,
                    tiktok_url=video_url,
                    video_title=title
                )

            response = HttpResponse(video_content, content_type="video/mp4")
            response['Content-Disposition'] = 'attachment; filename="tiktok_video.mp4"'
            return response

        except Exception as e:
            print(f"Error: {e}") 
            messages.error(request, f"Сталася помилка: {str(e)}")
            return render(request, 'downloader/home.html')

    return render(request, 'downloader/home.html')

@login_required
def cabinet_view(request):
    history = DownloadHistory.objects.filter(user=request.user).order_by('-download_date')
    return render(request, 'downloader/cabinet.html', {'history': history})
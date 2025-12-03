# downloader/views.py
import os
import requests
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils.translation import gettext as _
from .forms import CustomUserCreationForm
from .models import DownloadHistory, TikTokAuthor, TikTokVideo, UserProfile

load_dotenv()

API_KEY = os.getenv("RAPID_API_KEY")
API_HOST = os.getenv("RAPID_API_HOST")
API_URL = os.getenv("RAPID_API_URL")

def register_view(request):
    if request.user.is_authenticated: return redirect('cabinet')
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
    fmt = request.GET.get('format', 'video')
    
    if not video_url:
        return render(request, 'downloader/home.html', {})

    if "/photo/" in video_url:
        return render(request, 'downloader/home.html', {'error': _("Це слайдшоу. Тільки відео!")})

    try:
        # API Request
        querystring = {"url": video_url}
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
        response = requests.get(API_URL, headers=headers, params=querystring, timeout=20)
        data = response.json()

        if "video" not in data and "hdplay" not in data:
            return render(request, 'downloader/home.html', {'error': _("Відео не знайдено.")})

        # --- ЛОГІКА ВИБОРУ ЯКОСТІ (HD) ---
        dl_link = None
        filename = "tiktok_video.mp4"
        content_type = "video/mp4"

        if fmt == 'audio':
            # Для музики беремо найкращий бітрейт, якщо доступний
            m_list = data.get("music", [])
            # Перевірка різних ключів для музики
            dl_link = data.get("music_info", {}).get("play") or (m_list[0] if isinstance(m_list, list) and m_list else str(m_list))
            filename = "audio.mp3"
            content_type = "audio/mpeg"
        else:
            # Пріоритет: HD > Standard > List[0]
            dl_link = data.get("hdplay") or data.get("play")
            if not dl_link and "video" in data:
                dl_link = data["video"][0] if isinstance(data["video"], list) else data["video"]

        if not dl_link:
             return render(request, 'downloader/home.html', {'error': _("Посилання на файл відсутнє.")})

        # Збереження в БД
        if request.user.is_authenticated:
            try:
                def clean(val, limit):
                    s = str(val[0]) if isinstance(val, list) else str(val)
                    return s[:limit]

                author = clean(data.get("author", "Unknown"), 490)
                title = clean(data.get("description", "Video"), 990)
                cover = clean(data.get("cover", ""), 990)

                a_obj, _ = TikTokAuthor.objects.get_or_create(username=author)
                v_obj, _ = TikTokVideo.objects.update_or_create(
                    original_url=video_url,
                    defaults={'title': title, 'author': a_obj, 'cover_image': cover}
                )
                DownloadHistory.objects.create(user=request.user, video=v_obj)
            except Exception as e:
                print(f"DB Save Error: {e}")

        # Стрімінг
        file_resp = requests.get(dl_link, stream=True, timeout=20)
        
        def stream():
            for chunk in file_resp.iter_content(chunk_size=8192):
                if chunk: yield chunk

        resp = StreamingHttpResponse(stream(), content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    except Exception as e:
        print(f"Error: {e}")
        return render(request, 'downloader/home.html', {'error': _("Помилка завантаження")})

# ... Cabinet View і Logout залишаються без змін ...
# (Я не дублюю їх, щоб не займати місце, залиште як були в минулій версії)
@login_required
def cabinet_view(request):
    from .models import UserProfile
    history = DownloadHistory.objects.filter(user=request.user).select_related('video', 'video__author').order_by('-download_date')[:50]
    total = DownloadHistory.objects.filter(user=request.user).count()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    bot_link = f"https://t.me/TikRip_Bot?start={profile.connect_token}"
    is_linked = profile.telegram_id is not None
    return render(request, 'downloader/cabinet.html', {'history': history, 'total_downloads': total, 'bot_link': bot_link, 'is_telegram_linked': is_linked})

def custom_logout_view(request):
    logout(request)
    return render(request, 'downloader/logout.html')
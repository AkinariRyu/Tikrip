import os
import aiohttp
from asgiref.sync import sync_to_async
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, aget_user
from django.utils.translation import gettext as _
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from dotenv import load_dotenv

from .forms import CustomUserCreationForm
from .models import DownloadHistory, TikTokAuthor, TikTokVideo, UserProfile

load_dotenv()

API_KEY = os.getenv("RAPID_API_KEY")
API_HOST = os.getenv("RAPID_API_HOST")
API_URL = os.getenv("RAPID_API_URL")

@sync_to_async
def async_render(request, template, context=None):
    """Запускає рендер шаблону в синхронному потоці"""
    return render(request, template, context)

@sync_to_async
def save_video_async(user, url, data):
    """Зберігає відео в БД без блокування"""
    try:
        def clean(val, limit):
            s = str(val[0]) if isinstance(val, list) else str(val)
            return s[:limit]

        author = clean(data.get("author", "Unknown"), 490)
        title = clean(data.get("description", "Video"), 990)
        cover = clean(data.get("cover", ""), 990)

        a_obj, _ = TikTokAuthor.objects.get_or_create(username=author)
        v_obj, _ = TikTokVideo.objects.update_or_create(
            original_url=url,
            defaults={'title': title, 'author': a_obj, 'cover_image': cover}
        )
        if user.is_authenticated:
            DownloadHistory.objects.create(user=user, video=v_obj)
    except Exception as e:
        print(f"DB Error: {e}")

@sync_to_async
def get_dashboard_data(user):
    """Отримує статистику для кабінету"""
    last_week = timezone.now() - timedelta(days=7)
    
    history = list(DownloadHistory.objects.filter(user=user).select_related('video', 'video__author').order_by('-download_date')[:50])
    total = DownloadHistory.objects.filter(user=user).count()
    
    stats = (DownloadHistory.objects.filter(user=user, download_date__gte=last_week)
             .annotate(date=TruncDate('download_date')).values('date')
             .annotate(count=Count('id')).order_by('date'))
    
    dates = [s['date'].strftime('%d.%m') for s in stats]
    counts = [s['count'] for s in stats]
    
    profile, _ = UserProfile.objects.get_or_create(user=user)
    bot_link = f"https://t.me/TikRip_Bot?start={profile.connect_token}"
    is_linked = profile.telegram_id is not None
    
    return history, total, dates, counts, bot_link, is_linked

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

async def home_view(request):
    video_url = request.GET.get('url')
    fmt = request.GET.get('format', 'video')
    user = await aget_user(request)
    
    if not video_url:
        return await async_render(request, 'downloader/home.html', {})

    if "/photo/" in video_url:
        return await async_render(request, 'downloader/home.html', {'error': _("Це слайдшоу. Тільки відео!")})

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}, params={"url": video_url}, timeout=20) as resp:
                if resp.status != 200:
                    return await async_render(request, 'downloader/home.html', {'error': f"API Error: {resp.status}"})
                data = await resp.json()

        if "video" not in data and "hdplay" not in data:
            return await async_render(request, 'downloader/home.html', {'error': _("Відео не знайдено.")})

        dl_link = None
        filename = "video.mp4"
        content_type = "video/mp4"

        if fmt == 'audio':
            m_list = data.get("music", [])
            dl_link = m_list[0] if isinstance(m_list, list) else m_list
            filename = "audio.mp3"
            content_type = "audio/mpeg"
        else:
            dl_link = data.get("hdplay") or data.get("play")
            if not dl_link:
                v_list = data.get("video", [])
                dl_link = v_list[0] if isinstance(v_list, list) else v_list

        if not dl_link:
            return await async_render(request, 'downloader/home.html', {'error': _("Посилання пусте")})

        if user.is_authenticated:
            await save_video_async(user, video_url, data)

        async def stream_file():
            async with aiohttp.ClientSession() as session:
                async with session.get(dl_link) as resp:
                    async for chunk in resp.content.iter_chunked(8192):
                        yield chunk

        response = StreamingHttpResponse(stream_file(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        print(f"Async Error: {e}")
        return await async_render(request, 'downloader/home.html', {'error': _("Помилка сервера")})

@login_required
async def cabinet_view(request):
    user = await aget_user(request)
    history, total, dates, counts, bot_link, is_linked = await get_dashboard_data(user)
    
    context = {
        'history': history,
        'total_downloads': total,
        'chart_dates': dates,
        'chart_counts': counts,
        'bot_link': bot_link,
        'is_telegram_linked': is_linked,
        'user': user
    }
    return await async_render(request, 'downloader/cabinet.html', context)

def custom_logout_view(request):
    logout(request)
    return render(request, 'downloader/logout.html')
# downloader/admin.py

from django.contrib import admin
from .models import DownloadHistory, TikTokAuthor, TikTokVideo

# 1. Адмінка для Авторів
@admin.register(TikTokAuthor)
class TikTokAuthorAdmin(admin.ModelAdmin):
    list_display = ('username',)
    search_fields = ('username',)

# 2. Адмінка для Відео
@admin.register(TikTokVideo)
class TikTokVideoAdmin(admin.ModelAdmin):
    list_display = ('short_title', 'author', 'created_at')
    search_fields = ('title', 'original_url')
    
    def short_title(self, obj):
        return obj.title[:30] + "..." if obj.title else "Без назви"
    short_title.short_description = "Назва"

# 3. Адмінка для Історії (Зв'язки)
@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    # Тепер ми не можемо писати 'tiktok_url', бо його тут немає.
    # Ми пишемо методи, які дістають дані з сусідньої таблиці video.
    list_display = ('user', 'get_video_title', 'get_video_url', 'download_date')
    
    # Фільтруємо по даті та користувачу
    list_filter = ('download_date', 'user')

    # Функція, щоб показати назву відео (через зв'язок)
    def get_video_title(self, obj):
        return obj.video.title[:30] + "..." if obj.video.title else "---"
    get_video_title.short_description = "Відео"

    # Функція, щоб показати URL (через зв'язок)
    def get_video_url(self, obj):
        return obj.video.original_url
    get_video_url.short_description = "Посилання"
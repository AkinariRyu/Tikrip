from django.contrib import admin
from .models import DownloadHistory, TikTokAuthor, TikTokVideo

@admin.register(TikTokAuthor)
class TikTokAuthorAdmin(admin.ModelAdmin):
    list_display = ('username',)
    search_fields = ('username',)

@admin.register(TikTokVideo)
class TikTokVideoAdmin(admin.ModelAdmin):
    list_display = ('short_title', 'author', 'created_at')
    search_fields = ('title', 'original_url')
    
    def short_title(self, obj):
        return obj.title[:30] + "..." if obj.title else "Без назви"
    short_title.short_description = "Назва"

@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_video_title', 'get_video_url', 'download_date')
    list_filter = ('download_date', 'user')

    def get_video_title(self, obj):
        return obj.video.title[:30] + "..." if obj.video.title else "---"
    get_video_title.short_description = "Відео"

    def get_video_url(self, obj):
        return obj.video.original_url
    get_video_url.short_description = "Посилання"
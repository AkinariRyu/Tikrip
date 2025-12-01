# downloader/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid

# 1. Профіль користувача (Зв'язок Телеграм <-> Сайт)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    # Токен для підключення (якщо треба буде в майбутньому)
    connect_token = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"Profile: {self.user.username}"

# 2. Автори ТікТоку
class TikTokAuthor(models.Model):
    username = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.username

# 3. Відео
class TikTokVideo(models.Model):
    author = models.ForeignKey(TikTokAuthor, on_delete=models.CASCADE, related_name='videos', null=True)
    original_url = models.URLField(max_length=1000, unique=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    cover_image = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title[:30] if self.title else "Video"

# 4. Історія завантажень
class DownloadHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(TikTokVideo, on_delete=models.CASCADE)
    download_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.video.id}"
from django.db import models
from django.contrib.auth.models import User
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_id = models.CharField(max_length=100, blank=True, null=True, unique=True, db_index=True)
    connect_token = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self): return self.user.username

class TikTokAuthor(models.Model):
    username = models.CharField(max_length=500, unique=True, db_index=True)
    def __str__(self): return self.username

class TikTokVideo(models.Model):
    author = models.ForeignKey(TikTokAuthor, on_delete=models.CASCADE, related_name='videos', null=True)
    original_url = models.URLField(max_length=2000, unique=True, db_index=True)
    title = models.CharField(max_length=1000, blank=True, null=True)
    cover_image = models.URLField(blank=True, null=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.title[:50] if self.title else "Video"

class DownloadHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    video = models.ForeignKey(TikTokVideo, on_delete=models.CASCADE)
    download_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-download_date']

    def __str__(self): return f"{self.user.username} -> {self.video.id}"
# downloader/models.py

from django.db import models
from django.contrib.auth.models import User

# Таблиця 1: Автори ТікТоку
class TikTokAuthor(models.Model):
    # unique=True гарантує, що ми не створимо дублікатів авторів
    username = models.CharField(max_length=255, unique=True, verbose_name="Нікнейм автора")
    
    def __str__(self):
        return self.username

# Таблиця 2: Унікальні відео
class TikTokVideo(models.Model):
    # Зв'язок: У одного автора багато відео
    author = models.ForeignKey(TikTokAuthor, on_delete=models.CASCADE, related_name='videos', null=True)
    
    # original_url має бути унікальним, щоб не дублювати відео в базі
    original_url = models.URLField(max_length=1000, unique=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    cover_image = models.URLField(blank=True, null=True) # Додамо посилання на обкладинку
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title[:30]

# Таблиця 3: Журнал завантажень (Хто і коли скачав)
class DownloadHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Тепер ми посилаємось не на URL, а на об'єкт відео
    video = models.ForeignKey(TikTokVideo, on_delete=models.CASCADE)
    
    download_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.video.id}"
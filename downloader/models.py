from django.db import models
from django.contrib.auth.models import User

class DownloadHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    tiktok_url = models.URLField(max_length=1000)
    
    download_date = models.DateTimeField(auto_now_add=True)
    
    video_title = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.video_title or self.tiktok_url}"
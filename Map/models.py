from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from simple_history.models import HistoricalRecords
from django.db.models.signals import post_save
# from colorful.fields import ColorField
from colorfield.fields import ColorField


class Map(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[('review', 'Review'), ('pending', 'Pending'), ('published', 'Published'), ('reject', 'Reject')])
    thumbnail = models.ImageField(upload_to='thumbnails/', default='thumbnails/Default-thum.png')
    publishing_date = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)
    history = HistoricalRecords()

    def __str__(self):
        return self.title
    
    
    

    

class MapFile(models.Model):
    map = models.ForeignKey(Map, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='maps/files/')

    class Meta:
        verbose_name = 'Map File'
        verbose_name_plural = 'Map Files'

    def __str__(self):
        return f"{self.map.title} - {self.file.name}"

class MapColor(models.Model):
    COLOR_PALETTE = [ 
    ("#000000", "black"), 
    ("#FF0000", "red"), 
    ("#00FF00", "green"), 
    ("#0000FF", "blue"), 
    ("#FFFF00", "yellow"), 
    ("#00FFFF", "cyan"), 
    ("#FF00FF", "magenta"), 
    ("#800080", "purple"), 
    ("#FFA500", "orange")
]
    map = models.ForeignKey(Map, on_delete=models.CASCADE, related_name='colors')
    color = ColorField(format="hexa", samples=COLOR_PALETTE, default="#007279")

    class Meta:
        verbose_name = 'Map Color'
        verbose_name_plural = 'Map Colors'

    def __str__(self):
        return f"{self.map.title} - {self.color}"

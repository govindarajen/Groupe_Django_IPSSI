from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse
import time

User = get_user_model()

class GameProject(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    genre = models.CharField(max_length=100)
    ambiance = models.CharField(max_length=200, blank=True)
    keywords = models.TextField(blank=True)
    references = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    generated = models.JSONField(null=True, blank=True)
    image_character = models.ImageField(upload_to="generated/characters/", null=True, blank=True)
    image_environment = models.ImageField(upload_to="generated/environments/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:150]
            self.slug = f"{base}-{int(time.time())}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:project_detail", args=[self.slug])

    def __str__(self):
        return f"{self.title} — {self.author.username}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    project = models.ForeignKey(GameProject, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")

class ApiUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    day_key = models.CharField(max_length=10)  # format YYYYMMDD
    count = models.IntegerField(default=0)

    class Meta:
        unique_together = ("user", "day_key")
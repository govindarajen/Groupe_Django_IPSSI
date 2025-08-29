from django.contrib import admin
from .models import GameProject, Favorite, ApiUsage

@admin.register(GameProject)
class GameProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "genre", "is_public", "created_at")
    search_fields = ("title", "author__username", "genre")

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "created_at")

@admin.register(ApiUsage)
class ApiUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "day_key", "count")
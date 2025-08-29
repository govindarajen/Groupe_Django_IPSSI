from django import forms
from .models import GameProject

class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = GameProject
        fields = ["title", "genre", "ambiance", "keywords", "references", "is_public"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder":"Nom du jeu"}),
            "genre": forms.TextInput(attrs={"placeholder":"RPG, FPS, Metroidvania..."}),
            "ambiance": forms.TextInput(attrs={"placeholder":"cyberpunk, post-apo, onirique..."}),
            "keywords": forms.TextInput(attrs={"placeholder":"boucle temporelle, IA rebelle..."}),
            "references": forms.Textarea(attrs={"rows":2, "placeholder":"Zelda, Hollow Knight..."}),
        }
import json, io, datetime
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.files.base import ContentFile
from django.db.models import Q
from django.template.loader import render_to_string
from weasyprint import HTML

from .models import GameProject, Favorite, ApiUsage
from .forms import ProjectCreateForm
from ai.generator import generate_structured_game, generate_concept_image, random_seed_game

class HomeView(ListView):
    model = GameProject
    template_name = "core/home.html"
    context_object_name = "projects"
    paginate_by = 12
    def get_queryset(self):
        return GameProject.objects.filter(is_public=True).order_by("-created_at")

def search_view(request):
    q = request.GET.get("q", "")
    projects = GameProject.objects.filter(is_public=True).filter(
        Q(title__icontains=q) | Q(genre__icontains=q) | Q(keywords__icontains=q) | Q(ambiance__icontains=q)
    ).order_by("-created_at")
    return render(request, "core/home.html", {"projects": projects, "search": q})

class DashboardView(LoginRequiredMixin, ListView):
    model = GameProject
    template_name = "core/dashboard.html"
    context_object_name = "projects"
    def get_queryset(self):
        return GameProject.objects.filter(author=self.request.user).order_by("-created_at")

class ProjectDetailView(DetailView):
    model = GameProject
    template_name = "core/project_detail.html"
    slug_field = "slug"

class CreateProjectView(LoginRequiredMixin, CreateView):
    model = GameProject
    form_class = ProjectCreateForm
    template_name = "core/create_project.html"
    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.author = self.request.user
        obj.save()
        return redirect(obj.get_absolute_url())

def _day_key():
    now = datetime.datetime.utcnow()
    return now.strftime("%Y%m%d")

def _check_quota(user):
    if not user.is_authenticated:
        return False, "Authentification requise."
    day = _day_key()
    usage, _ = ApiUsage.objects.get_or_create(user=user, day_key=day)
    if usage.count >= settings.DAILY_GENERATION_LIMIT:
        return False, f"Limite quotidienne atteinte ({settings.DAILY_GENERATION_LIMIT}). Réessaie demain."
    usage.count += 1
    usage.save()
    return True, ""

@login_required
def generate_game_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST requis"}, status=400)
    try:
        data = json.loads(request.body.decode())
    except Exception:
        return JsonResponse({"error": "Payload JSON invalide"}, status=400)

    project_id = data.get("project_id")
    if not project_id:
        return JsonResponse({"error": "project_id manquant"}, status=400)

    ok, msg = _check_quota(request.user)
    if not ok:
        return JsonResponse({"error": msg}, status=429)

    project = get_object_or_404(GameProject, id=project_id, author=request.user)

    # 1) Génération texte
    raw = generate_structured_game(project.title, project.genre, project.ambiance or "", project.keywords or "", project.references or "")
    if isinstance(raw, dict):
        project.generated = raw
    else:
        # sécurité si la fonction change
        try:
            project.generated = json.loads(str(raw))
        except Exception:
            project.generated = {"raw_text": str(raw)}

    # 2) Génération images (ne bloque pas si erreur)
    try:
        char_img = generate_concept_image(f"Concept art character, {project.ambiance or 'stylized'}, game style, full body, clean background")
        buf = io.BytesIO(); char_img.save(buf, format="PNG")
        project.image_character.save(f"{project.slug}-char.png", ContentFile(buf.getvalue()), save=False)
    except Exception as e:
        print("Image personnage KO:", e)

    try:
        env_img = generate_concept_image(f"Concept art environment, {project.ambiance or 'stylized'}, game scene, wide composition, highly detailed")
        buf2 = io.BytesIO(); env_img.save(buf2, format="PNG")
        project.image_environment.save(f"{project.slug}-env.png", ContentFile(buf2.getvalue()), save=False)
    except Exception as e:
        print("Image environnement KO:", e)

    project.save()
    return JsonResponse({"status": "ok", "project_url": project.get_absolute_url()})

@login_required
def toggle_favorite(request, slug):
    project = get_object_or_404(GameProject, slug=slug)
    fav, created = Favorite.objects.get_or_create(user=request.user, project=project)
    if not created:
        fav.delete()
    return redirect(project.get_absolute_url())

@login_required
def favorites_view(request):
    projects = GameProject.objects.filter(favorited_by__user=request.user).order_by("-created_at")
    return render(request, "core/favorites.html", {"projects": projects})

def export_project_pdf(request, slug):
    project = get_object_or_404(GameProject, slug=slug)
    if not project.is_public and (not request.user.is_authenticated or request.user != project.author):
        return HttpResponse("Accès refusé", status=403)
    html_string = render_to_string("core/pdf_template.html", {"project": project})
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{project.slug}.pdf"'
    return resp

@login_required
def explore_free_view(request):
    ok, msg = _check_quota(request.user)
    if not ok:
        return HttpResponse(msg, status=429)

    seed = random_seed_game()
    p = GameProject.objects.create(
        author=request.user,
        title=seed["title"],
        genre=seed["genre"],
        ambiance=seed["ambiance"],
        keywords=seed["keywords"],
        references=seed["references"],
        is_public=False,
    )
    # Auto-génère le contenu puis redirige vers le détail
    # On réutilise la fonction de génération
    payload = {"project_id": p.id}
    request._body = json.dumps(payload).encode()
    response = generate_game_view(request)
    # si succès -> on redirige
    if getattr(response, "status_code", 200) == 200:
        return redirect(p.get_absolute_url())
    return HttpResponse("Erreur génération", status=500)
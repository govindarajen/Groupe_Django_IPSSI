from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("search/", views.search_view, name="search"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("create/", views.CreateProjectView.as_view(), name="create"),
    path("project/<slug:slug>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("favorite/<slug:slug>/", views.toggle_favorite, name="toggle_favorite"),
    path("favorites/", views.favorites_view, name="favorites"),
    path("export/<slug:slug>/pdf/", views.export_project_pdf, name="export_pdf"),

    # IA
    path("generate/", views.generate_game_view, name="generate"),           # POST JSON {project_id}
    path("explore/", views.explore_free_view, name="explore_free"),         # GET -> crée & génère aléatoire
]
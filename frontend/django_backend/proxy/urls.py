from django.urls import path
from proxy import views

urlpatterns = [
    path("health/", views.health, name="ml-health"),
    path("analyze/", views.analyze, name="ml-analyze"),
    path("chat/", views.chat, name="ml-chat"),
    path("top_skills/", views.top_skills, name="ml-top-skills"),
    path("market_stats/", views.market_stats, name="ml-market-stats"),
    path("skills_by_role/", views.skills_by_role, name="ml-skills-by-role"),
    path("extract_jd/", views.extract_jd, name="ml-extract-jd"),
]

from accounts import views
from django.urls import path

urlpatterns = [
    path("register/", views.register, name="auth-register"),
    path("login/", views.login_view, name="auth-login"),
    path("logout/", views.logout_view, name="auth-logout"),
    path("me/", views.me, name="auth-me"),
]

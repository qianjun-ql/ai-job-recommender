"""
FR-09 accounts — auth views: register, login, logout, me.

Uses Django's built-in auth. Session-based (cookie) for browser clients.
Replace with JWT (djangorestframework-simplejwt) when building a mobile app.
"""

from accounts.serializers import RegisterSerializer, UserSerializer
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["POST"])
def register(request: Request) -> Response:
    """Create a new user account.

    Body: { username, email, password }
    Returns: { id, username, email, date_joined }
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user: User = serializer.save()
        login(request, user)  # log in immediately after registration
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def login_view(request: Request) -> Response:
    """Authenticate and create a session.

    Body: { username, password }
    Returns: { id, username, email, date_joined }
    """
    username = request.data.get("username", "")
    password = request.data.get("password", "")

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"error": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
def logout_view(request: Request) -> Response:
    """Clear the session."""
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request: Request) -> Response:
    """Return the currently authenticated user's details."""
    return Response(UserSerializer(request.user).data)

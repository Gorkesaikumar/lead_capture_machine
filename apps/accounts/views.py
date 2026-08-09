"""
Authentication API Views for Admin Dashboard.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.serializers import LoginSerializer, UserResponseSerializer
from apps.accounts.services import AuthService


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates Admin user and returns authentication token with safe profile details.
    """

    permission_classes = [AllowAny]
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token = serializer.validated_data["token"]
        user_data = UserResponseSerializer(user).data

        return Response(
            {
                "status": "success",
                "data": {
                    "token": token,
                    "user": user_data,
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Revokes the current Admin's active authentication token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        AuthService.logout_admin(request.user)
        return Response(
            {
                "status": "success",
                "message": "Successfully logged out.",
            },
            status=status.HTTP_200_OK,
        )


class CurrentAdminView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the authenticated Admin's profile details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserResponseSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

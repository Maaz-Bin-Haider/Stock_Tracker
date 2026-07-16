from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audits.models import AuditLog
from apps.audits.services import record_audit

from .models import User
from .permissions import IsAdmin
from .serializers import LoginSerializer, MeSerializer, UserSerializer


class LoginView(APIView):
    """Session login. Success/failure audit rows come from Django's auth signals."""

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active:
            return Response({"detail": "This account is disabled."}, status=400)
        login(request, user)
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="get")
class MeView(APIView):
    """Who am I + role; also guarantees the CSRF cookie is set for the SPA."""

    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        """Self-service profile bits — currently the theme preference
        (FR-126: remembered per user, follows them across devices)."""
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """User management, admin only (FR-004). Users are disabled, never deleted."""

    module = "users"
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]

    def _snapshot(self, instance):
        return self.get_serializer(instance).data

    def perform_create(self, serializer):
        instance = serializer.save()
        record_audit(
            action=AuditLog.Action.CREATE,
            module=self.module,
            record_id=instance.pk,
            record_repr=instance.username,
            after=self._snapshot(instance),
        )

    def perform_update(self, serializer):
        before = self._snapshot(serializer.instance)
        instance = serializer.save()
        record_audit(
            action=AuditLog.Action.UPDATE,
            module=self.module,
            record_id=instance.pk,
            record_repr=instance.username,
            before=before,
            after=self._snapshot(instance),
        )

from django.conf import settings
from django.contrib.auth import get_user_model
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, HTTP_401_UNAUTHORIZED
)
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView
)

from users.permissions import CurrentUserOrAdminPermission
from users.serializers import (
    CookieTokenRefreshSerializer, CookieTokenVerifySerializer, UserSerializer,
    RegisterUserSerializer, UpdateUserSerializer
)
from users.swagger import (
    CookieTokenObtainPairResponseSerializer, CookieTokenRefreshResponseSerializer,
    CookieTokenVerifyResponseSerializer
)

User = get_user_model()


class JWTObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/token/
    """

    @swagger_auto_schema(responses={
        HTTP_200_OK: openapi.Response('OK', CookieTokenObtainPairResponseSerializer)
    })
    def post(self, request: Request, *args, **kwargs) -> Response:
        return super().post(request, *args, **kwargs)

    def finalize_response(self, request: Request, response: Response, *args, **kwargs) -> Response:
        """Returns the final response object."""

        if access := response.data.get('access'):
            access_cookie_max_age = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
            response.set_cookie(
                key=settings.SIMPLE_JWT['ACCESS_TOKEN_COOKIE'],
                value=access,
                max_age=access_cookie_max_age,
                expires=access_cookie_max_age,
                secure=not settings.DEBUG,
                domain="vercel.app",
                httponly=True,
                samesite="None" if not settings.DEBUG else "Lax"
            )

        if refresh := response.data.get('refresh'):
            refresh_cookie_max_age = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
            response.set_cookie(
                key=settings.SIMPLE_JWT['REFRESH_TOKEN_COOKIE'],
                value=refresh,
                max_age=refresh_cookie_max_age,
                expires=refresh_cookie_max_age,
                secure=not settings.DEBUG,
                domain="vercel.app",
                httponly=True,
                samesite="None" if not settings.DEBUG else "Lax"
            )
        return super().finalize_response(request, response, *args, **kwargs)


class JWTRefreshView(TokenRefreshView):
    """
    POST /api/auth/token/refresh/
    """
    serializer_class = CookieTokenRefreshSerializer

    @swagger_auto_schema(responses={
        HTTP_200_OK: openapi.Response('OK', CookieTokenRefreshResponseSerializer)
    })
    def post(self, request, *args, **kwargs) -> Response:
        # if refresh cookie exists and refresh was not submitted via form/request
        if refresh := request.COOKIES.get('refresh') and not request.data.get('refresh'):
            _data = dict(request.data)
            _data.update({"refresh": str(refresh)})
            serializer = self.get_serializer(data=_data)
        else:
            serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=HTTP_200_OK)

    def finalize_response(self, request: Request, response: Response, *args, **kwargs) -> Response:
        """Returns the final response object."""

        if access_token := response.data.get('access'):
            access_cookie_max_age = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
            response.set_cookie(
                key=settings.SIMPLE_JWT['ACCESS_TOKEN_COOKIE'],
                value=access_token,
                max_age=access_cookie_max_age,
                expires=access_cookie_max_age,
                secure=not settings.DEBUG,
                domain="vercel.app",
                httponly=True,
                samesite="None" if not settings.DEBUG else "Lax"
            )
        return super().finalize_response(request, response, *args, **kwargs)


class JWTVerifyView(TokenVerifyView):
    """
    POST /api/auth/token/verify/
    """
    serializer_class = CookieTokenVerifySerializer

    @swagger_auto_schema(responses={
        HTTP_200_OK: openapi.Response('OK', CookieTokenVerifyResponseSerializer)
    })
    def post(self, request, *args, **kwargs) -> Response:
        print("[REQUEST DATA]", request.data)
        print("[REQUEST COOKIES]", request.COOKIES)

        # if access cookie exists and token was not submitted via form/request
        if access := request.COOKIES.get('access') and not request.data.get('token'):
            _data = dict(request.data)
            _data.update({"token": str(access)})
            serializer = self.get_serializer(data=_data)
        else:
            serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=HTTP_200_OK)


class JWTLogoutView(APIView):
    """
    GET /api/auth/logout/
    """

    @swagger_auto_schema(responses={
        HTTP_200_OK: 'Logout successful!',
        HTTP_401_UNAUTHORIZED: 'Could not logout! Cookie \'refresh\' not found in request!',
    })
    def get(self, request: Request, *args, **kwargs) -> Response:
        if refresh := request.COOKIES.get('refresh'):
            response = Response({'message': 'Logout successful!'}, status=HTTP_200_OK)
            response.delete_cookie('access')

            try:
                refresh_token = RefreshToken(refresh)
                refresh_token.blacklist()
            except TokenError:
                # if refresh token has already been blacklisted, then just delete refresh cookie
                pass

            response.delete_cookie('refresh')
            return response
        return Response(
            {'message': 'Could not logout! Cookie \'refresh\' not found in request!'},
            status=HTTP_401_UNAUTHORIZED
        )


# to do tests
class UserViewSet(viewsets.ModelViewSet):
    """
    GET     /api/users/          - list all users
    POST    /api/users/          - register new user
    GET     /api/users/<int:id>/ - retrieve user
    PUT     /api/users/<int:id>/ - update user
    PATCH   /api/users/<int:id>/ - partially update user
    DELETE  /api/users/<int:id>/ - delete user
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return RegisterUserSerializer
        elif hasattr(self, 'action') and self.action in ['update', 'partial_update']:
            return UpdateUserSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.request.method == "POST":
            # allow registration for users who are not logged in
            permission_classes = [AllowAny]
            return [permission() for permission in permission_classes]
        elif self.request.method in ["PUT", "PATCH", "DELETE"]:
            # allow modification for user themselves or admins
            permission_classes = [IsAuthenticated, CurrentUserOrAdminPermission]
            return [permission() for permission in permission_classes]
        return super().get_permissions()

    @swagger_auto_schema(responses={
        HTTP_200_OK: openapi.Response('OK', UserSerializer)}
    )
    def update(self, request: Request, *args, **kwargs) -> Response:
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(responses={
        HTTP_200_OK: openapi.Response('OK', UserSerializer)}
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        return super().partial_update(request, *args, **kwargs)


class GetCurrentUser(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /api/users/me/"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_object(self) -> User:
        return self.request.user

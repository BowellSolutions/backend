from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.status import (
    HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
)
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from users.serializers import UserSerializer
from users.utils import get_tokens_for_user

User = get_user_model()


class TestUsersViews(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    @classmethod
    def setUpTestData(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.user = User.objects.create_user(
            email='test@gmail.com', password='testing123',
            first_name='te', last_name='st', type=User.Types.STAFF
        )

    def _require_jwt_cookies(self, user) -> None:
        """Client will attach valid JWT Cookies"""
        access, refresh = get_tokens_for_user(user=user)
        self.client.cookies.load({
            'access': access,
            'refresh': refresh,
        })

    def test_obtain_jwt(self):
        response = self.client.post('/api/auth/token/', {
            'email': 'test@gmail.com',
            'password': 'testing123'
        })
        res_json = response.json()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn('access', res_json)
        self.assertIn('refresh', res_json)

    def test_obtain_jwt_missing_fields(self):
        response = self.client.post('/api/auth/token/', {
            'email': 'test@gmail.com',
        })
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'password': ['This field is required.']})

    def test_obtain_jwt_user_not_found(self):
        response = self.client.post('/api/auth/token/', {
            'email': 'nouser@gmail.com',
            'password': 'nouser123'
        })
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {'detail': 'No active account found with the given credentials'})

    def test_refresh_jwt_refresh_in_request(self):
        access, refresh = get_tokens_for_user(self.user)
        res_refresh_token = self.client.post('/api/auth/token/refresh/', data={
            'refresh': refresh
        })
        refresh_data = res_refresh_token.json()
        self.assertEqual(res_refresh_token.status_code, HTTP_200_OK)
        self.assertIn('access', refresh_data)
        self.assertNotEqual(access, refresh_data['access'])

    def test_refresh_jwt_refresh_in_cookie(self):
        self._require_jwt_cookies(self.user)
        prev_access = self.client.cookies['access']
        res_refresh_token = self.client.post('/api/auth/token/refresh/', data={})
        refresh_data = res_refresh_token.json()
        self.assertEqual(res_refresh_token.status_code, HTTP_200_OK)
        self.assertIn('access', refresh_data)
        self.assertNotEqual(prev_access, refresh_data['access'])

    def test_refresh_jwt_missing_fields(self):
        response = self.client.post('/api/auth/token/refresh/', {})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'refresh': ['This field is required.']})

    def test_refresh_jwt_invalid_refresh(self):
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': 'blablablablabla'
        })
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {'detail': 'Token is invalid or expired', 'code': 'token_not_valid'})

    def test_verify_jwt_token_in_request(self):
        access, refresh = get_tokens_for_user(self.user)
        res_verify_access = self.client.post('/api/auth/token/verify/', {
            'token': access
        })
        self.assertEqual(res_verify_access.status_code, HTTP_200_OK)
        self.assertEqual(res_verify_access.json(), {})

        res_verify_refresh = self.client.post('/api/auth/token/verify/', {
            'token': refresh
        })
        self.assertEqual(res_verify_refresh.status_code, HTTP_200_OK)
        self.assertEqual(res_verify_refresh.json(), {})

    def test_verify_jwt_token_in_cookie(self):
        self._require_jwt_cookies(user=self.user)
        response = self.client.post('/api/auth/token/verify/', {})
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_verify_jwt_no_token_in_data_nor_cookies(self):
        response = self.client.post('/api/auth/token/verify/', {})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'token': ['This field is required.']})

    def test_verify_jwt_token_invalid(self):
        response = self.client.post('/api/auth/token/verify/', {
            'token': 'totally_legit_jwt_xd'
        })
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {'detail': 'Token is invalid or expired', 'code': 'token_not_valid'})

    def test_verify_jwt_invalid_token_in_cookie(self):
        self.client.cookies.load({
            'access': 'blablabla'
        })
        response = self.client.post('/api/auth/token/verify/', {})
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {'detail': 'Token is invalid or expired', 'code': 'token_not_valid'})

    def test_logout(self):
        self._require_jwt_cookies(user=self.user)
        self.assertEqual(BlacklistedToken.objects.all().count(), 0)
        response = self.client.get('/api/auth/logout/')
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.all().count(), 1)
        self.assertEqual(response.json(), {'message': 'Logout successful!'})

    def test_logout_cookies_not_found(self):
        response = self.client.get('/api/auth/logout/')
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {'message': "Could not logout! Cookie 'refresh' not found in request!"}
        )

    def test_get_current_user(self):
        self._require_jwt_cookies(user=self.user)
        response = self.client.get('/api/users/me/', {})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), UserSerializer(self.user).data)

    def test_get_current_user_without_cookies_and_headers(self):
        response = self.client.get('/api/users/me/', {})
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {'detail': 'Authentication credentials were not provided.'})

    def test_get_current_user_invalid_token(self):
        self.client.cookies.load({
            'access': 'qwerty1234567890'
        })
        response = self.client.get('/api/users/me/', {})
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {
                'detail': 'Given token not valid for any token type',
                'code': 'token_not_valid',
                'messages': [
                    {
                        'token_class': 'AccessToken',
                        'token_type': 'access',
                        'message': 'Token is invalid or expired'
                    }
                ]
            }
        )

    # to do: test UserViewSet

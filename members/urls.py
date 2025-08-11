from django.urls import path
from .views import SignUpView, LoginView, UserUpdateView, GoogleLoginView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register', SignUpView.as_view(), name='register'),
    path('login', LoginView.as_view(), name='login'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('update-user', UserUpdateView.as_view(), name='update-user'),
    path('google-login', GoogleLoginView.as_view(), name='google-login')
]

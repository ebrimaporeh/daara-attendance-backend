# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import TokenRefreshView
# from . import views

# # Use a different variable name to avoid conflicts
# users_router = DefaultRouter()
# users_router.register(r'users', views.UserViewSet)

# urlpatterns = [
#     path('api/', include(users_router.urls)),
#     path('api/register/', views.RegisterView.as_view(), name='register'),
#     path('api/login/', views.LoginView.as_view(), name='login'),
#     path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
#     path('api/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
# ]
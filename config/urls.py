from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from shop.api import router

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("shop.urls")),
]
if not settings.USE_B2:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

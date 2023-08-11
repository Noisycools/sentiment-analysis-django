from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("core.urls")),
    path("analytic/", include("analytic.urls")),
    path("admin/", admin.site.urls),
]

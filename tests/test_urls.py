from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", include("admin_email_2fa.urls")),
    path("admin/", admin.site.urls),
]

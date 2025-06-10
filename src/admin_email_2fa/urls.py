from django.urls import path

from .views import AdminEmail2FAView

urlpatterns = [
    path("admin/email-2fa/", AdminEmail2FAView.as_view(), name="admin_email_2fa"),
]

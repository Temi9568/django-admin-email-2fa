import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from admin_email_2fa.middleware import AdminEmail2FAMiddleware
from admin_email_2fa.settings import NAMESPACE

User = get_user_model()


@pytest.fixture
def request_factory():
    """Fixture to create a request factory."""
    return RequestFactory()


def create_request(factory, user, path, session_data=None):
    """Helper function to create a request with user and session."""
    request = factory.get(path)
    request.user = user
    request.session = session_data or {}
    return request


@pytest.fixture
def middleware():
    """Fixture to create a middleware instance."""
    return AdminEmail2FAMiddleware(get_response=lambda r: None)


@pytest.mark.django_db
class TestAdminEmail2FAMiddleware:
    """Test the AdminEmail2FAMiddleware class."""

    def test_non_admin_url(self, request_factory, middleware: AdminEmail2FAMiddleware):
        """Test that the mware does not redirect to the 2FA page for non-admin URLs."""
        request = create_request(request_factory, AnonymousUser(), "/some-other-url/")
        assert not middleware.should_we_redirect_to_2fa_page(request)

    def test_admin_url_not_authenticated(
        self, request_factory, middleware: AdminEmail2FAMiddleware
    ):
        """Test that the mware does not redirect to the 2FA page for non-admin URLs."""
        request = create_request(
            request_factory, AnonymousUser(), reverse("admin:index")
        )
        assert not middleware.should_we_redirect_to_2fa_page(request)

    def test_admin_url_authenticated_not_verified(
        self, request_factory, admin_user, middleware
    ):
        """Test that the mware redirects to the 2FA page for admin URLs when the user
        is not verified."""
        request = create_request(request_factory, admin_user, reverse("admin:index"))
        assert middleware.should_we_redirect_to_2fa_page(request)

    def test_admin_url_authenticated_and_verified(
        self, request_factory, admin_user, middleware
    ):
        """Test that the mware does not redirect to the 2FA page for admin URLs when
        the user is verified."""
        request = create_request(
            request_factory,
            admin_user,
            reverse("admin:index"),
            {NAMESPACE: {"is_verified": True}},
        )
        assert not middleware.should_we_redirect_to_2fa_page(request)

    def test_admin_login_url(
        self, request_factory, admin_user, middleware: AdminEmail2FAMiddleware
    ):
        """Test that the mware does not redirect to the 2FA page for admin login
        URLs."""
        request = create_request(request_factory, admin_user, reverse("admin:login"))
        assert not middleware.should_we_redirect_to_2fa_page(request)

    def test_admin_logout_url(
        self, request_factory, admin_user, middleware: AdminEmail2FAMiddleware
    ):
        """Test that the mware does not redirect to the 2FA page for admin logout
        URLs."""
        request = create_request(request_factory, admin_user, reverse("admin:logout"))
        assert not middleware.should_we_redirect_to_2fa_page(request)

    def test_2fa_url(
        self, request_factory, admin_user, middleware: AdminEmail2FAMiddleware
    ):
        """Test that the mware does not redirect to the 2FA page for the 2FA page."""
        request = create_request(
            request_factory, admin_user, reverse("admin_email_2fa")
        )
        assert not middleware.should_we_redirect_to_2fa_page(request)

    def test_redirect_saves_next_url(
        self, request_factory, admin_user, middleware: AdminEmail2FAMiddleware
    ):
        """Test that the mware saves the next URL when redirecting to the 2FA page."""
        request = create_request(request_factory, admin_user, reverse("admin:index"))
        response = middleware.process_request(request)

        assert request.session["next_url"] == request.get_full_path()
        assert response.status_code == 302
        assert response.url == reverse("admin_email_2fa")

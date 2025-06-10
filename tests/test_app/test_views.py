import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.urls import reverse

from admin_email_2fa.otp import TokenManager
from admin_email_2fa.settings import NAMESPACE

User = get_user_model()


@pytest.fixture
def admin_client(admin_user):
    """A client that is logged in as the admin user."""
    client = Client()
    client.login(username="admin", password="adminpass123")
    return client


@pytest.mark.django_db
class TestAdminEmail2FAView:
    """Test the AdminEmail2FAView."""

    def test_get_without_auth(self, client):
        """Test that the view redirects to the login page if the user is not
        authenticated."""
        response = client.get(reverse("admin_email_2fa"))
        assert response.status_code == 302
        assert response.url == reverse("admin:login")

    def test_get_with_auth_already_verified(self, admin_client):
        """Test that the view redirects to the admin index page if the user is already
        verified."""
        session = admin_client.session
        session[NAMESPACE] = {"is_verified": True}
        session.save()

        response = admin_client.get(reverse("admin_email_2fa"))
        assert response.status_code == 302
        assert response.url == reverse("admin:index")

    def test_get_generates_and_sends_otp(self, admin_client, admin_user):
        """Test that the view generates and sends an OTP to the user's email."""
        response = admin_client.get(reverse("admin_email_2fa"))
        assert response.status_code == 200

        # Check that email was sent
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [admin_user.email]
        assert "OTP" in mail.outbox[0].subject

        # Check that token manager was stored in session
        session = admin_client.session
        assert NAMESPACE in session
        assert "tkm" in session[NAMESPACE]

    def test_post_invalid_form(self, admin_client):
        """Test that the view returns a 200 status code and an error message if the
        form is invalid."""
        response = admin_client.post(reverse("admin_email_2fa"), {"otp": ""})
        assert response.status_code == 200
        assert "error_msg" in response.context

    def test_post_without_token_manager(self, admin_client):
        """Test that the view raises an assertion error if the token manager is not
        in the session."""
        with pytest.raises(AssertionError):
            admin_client.post(reverse("admin_email_2fa"), {"otp": "12345"})

    def test_post_correct_otp(self, admin_client):
        """Test that the view redirects to the admin index page if the correct
        OTP is submitted."""
        # First get to generate OTP
        admin_client.get(reverse("admin_email_2fa"))

        # Get the OTP from the session
        session = admin_client.session
        tkm_dict = session[NAMESPACE]["tkm"]
        tkm = TokenManager.reload_state(tkm_dict)
        otp = tkm.token.otp

        # Submit the correct OTP
        response = admin_client.post(reverse("admin_email_2fa"), {"otp": otp})
        assert response.status_code == 302
        assert response.url == reverse("admin:index")

        # Check that session is marked as verified
        session = admin_client.session
        assert session[NAMESPACE]["is_verified"]

    def test_post_incorrect_otp(self, admin_client):
        """Test that the view returns a 200 status code and an error message if the
        OTP is incorrect."""
        # First get to generate OTP
        admin_client.get(reverse("admin_email_2fa"))

        # Submit incorrect OTP
        response = admin_client.post(reverse("admin_email_2fa"), {"otp": "wrong-otp"})
        assert response.status_code == 200
        assert "error_msg" in response.context
        assert "error_type" in response.context
        assert response.context["error_type"] == "IncorrectAttempt"

    def test_post_expired_token(self, admin_client):
        """Test that the view returns a 200 status code and an error message if the
        OTP is expired."""
        # First get to generate OTP
        admin_client.get(reverse("admin_email_2fa"))

        # Manipulate session to expire token
        session = admin_client.session
        tkm_dict = session[NAMESPACE]["tkm"]
        tkm = TokenManager.reload_state(tkm_dict)
        tkm._token = tkm.token._replace(gen_time=0)  # Set gen_time to past
        session[NAMESPACE]["tkm"] = tkm.dump_state()
        session.save()

        # Submit OTP
        response = admin_client.post(reverse("admin_email_2fa"), {"otp": tkm.token.otp})
        assert response.status_code == 200
        assert "error_msg" in response.context
        assert "error_type" in response.context
        assert response.context["error_type"] == "ExpiredToken"
        assert response.context["show_regen_btn"]

    def test_post_max_retries_exceeded(self, admin_client):
        """Test that the view returns a 200 status code and an error message if the
        OTP is incorrect."""
        # First get to generate OTP
        admin_client.get(reverse("admin_email_2fa"))

        # Submit incorrect OTP multiple times
        for _ in range(3):  # Assuming max_retries is 3
            response = admin_client.post(
                reverse("admin_email_2fa"), {"otp": "wrong-otp"}
            )

        assert response.status_code == 200
        assert "error_msg" in response.context
        assert "error_type" in response.context
        assert response.context["error_type"] == "NoMoreRetries"
        assert response.context["show_regen_btn"]

    def test_next_url_redirect(self, admin_client):
        """Test that the view redirects to the next URL if it is set in the session."""
        # Set next_url in session
        session = admin_client.session
        next_url = reverse("admin:auth_user_changelist")
        session["next_url"] = next_url
        session.save()

        # First get to generate OTP
        admin_client.get(reverse("admin_email_2fa"))

        # Get the OTP from the session
        session = admin_client.session
        tkm_dict = session[NAMESPACE]["tkm"]
        tkm = TokenManager.reload_state(tkm_dict)
        otp = tkm.token.otp

        # Submit the correct OTP
        response = admin_client.post(reverse("admin_email_2fa"), {"otp": otp})
        assert response.status_code == 302
        assert response.url == next_url

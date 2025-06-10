from typing import Any, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .exceptions import ExpiredToken, IncorrectAttempt, NoMoreRetries, ThrottleExceeded
from .forms import OTPForm
from .otp import AbstractOTPGenerator, TokenManager
from .settings import NAMESPACE, app_settings


class AdminEmail2FAView(View):
    NAMESPACE = NAMESPACE

    @property
    def default_otp_generator(self) -> AbstractOTPGenerator:
        """Returns the otp generator used by this view."""
        return app_settings.DEFAULT_OTP_GENERATOR_CLASS()

    @property
    def default_template(self) -> str:
        """Returns the template name used by this view."""
        return app_settings.DEFAULT_TEMPLATE

    @property
    def email_template(self) -> Optional[str]:
        """Returns the email template name used by this view."""
        return app_settings.DEFAULT_EMAIL_TEMPLATE

    @property
    def throttle_in_seconds(self) -> int:
        """Returns the throttle time in seconds used by this view."""
        return app_settings.THROTTLE_IN_SECONDS

    @property
    def otp_expiration_in_seconds(self) -> int:
        """Returns the OTP expiration time in seconds used by this view."""
        return app_settings.OTP_EXPIRATION_IN_SECONDS

    @property
    def max_retries(self) -> int:
        """Returns the maximum number of retries used by this view."""
        return app_settings.MAX_RETRIES

    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        """Dispatches the request to the appropriate method based on the request
        type."""
        if not self.request.user.is_authenticated:
            return redirect(reverse("admin:login"))

        if self.already_verified(request):
            return redirect(reverse("admin:index"))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Handles GET requests.

        Generates a token and sends it to the user's email.
        """
        email = request.user.email
        context = {"email": email}

        # Initialize the token manager from the session or create a new one
        tkm = self.load_tkm_from_request(request) or TokenManager(
            otp_generator=self.default_otp_generator,
            throttle_s=self.throttle_in_seconds,
            token_expiration_s=self.otp_expiration_in_seconds,
            max_retries=self.max_retries,
        )

        # Generate a token
        try:
            tkm.generate_token()
            self.send_otp_email(request, tkm.token.otp, email)
        except ThrottleExceeded as e:
            context["error_type"] = e.__class__.__qualname__.split(".")[-1]
            context["error_msg"] = str(e)

        # Update the request session with new token manager state
        self.save_tkm_in_request(request, tkm, context)

        return render(request, self.default_template, context=context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Handles POST requests.

        Validates the form and validates the OTP.
        """
        email = request.user.email
        context: dict[str, Any] = {"email": email}

        # Validate form
        form = OTPForm(request.POST)
        if not form.is_valid():
            print(form.errors, form.__dict__)
            context["error_msg"] = form.errors["otp"]
            return render(request, self.default_template, context)
        otp = form.cleaned_data["otp"]

        tkm = self.load_tkm_from_request(request)
        assert tkm, "TKM not in session data when it should be."
        try:
            tkm.validate(otp)
            return self.handle_post_verify(request)
        except (ExpiredToken, IncorrectAttempt, NoMoreRetries) as e:
            context["error_type"] = e.__class__.__qualname__.split(".")[-1]
            context["error_msg"] = str(e)
            if isinstance(e, (NoMoreRetries, ExpiredToken)):
                context["show_regen_btn"] = True

        # Update the request session with new token manager state
        self.save_tkm_in_request(request, tkm, context)

        return render(request, self.default_template, context=context)

    def already_verified(self, request: HttpRequest) -> bool:
        """Checks if the user has already verified their email."""
        return request.session.get(self.NAMESPACE, {}).get("is_verified", False)

    def handle_post_verify(self, request: HttpRequest) -> HttpResponse:
        """Handles the POST request after the user has verified their email."""
        request.session[self.NAMESPACE] = {"is_verified": True}
        next_url = request.session.get("next_url", None)
        return redirect(next_url or reverse("admin:index"))

    def load_tkm_from_request(self, request: HttpRequest) -> Optional[TokenManager]:
        """Loads the token manager from the request session."""
        tkm_dict = request.session.get(self.NAMESPACE, {}).get("tkm", {})
        if tkm_dict:
            return TokenManager.reload_state(tkm_dict)
        return None

    def save_tkm_in_request(
        self, request: HttpRequest, tkm: TokenManager, context: dict
    ) -> None:
        """Saves the token manager in the request session."""
        tkm_dict = tkm.dump_state()
        request.session[self.NAMESPACE] = {"tkm": tkm_dict}
        context["tkm"] = tkm_dict

    def send_otp_email(self, request: HttpRequest, otp: str, email: str) -> None:
        """Sends the OTP token via email."""
        send_mail(
            subject="Your 2FA OTP Code",
            from_email=settings.DEFAULT_FROM_EMAIL,
            message=f"Your OTP code is: {otp}",
            recipient_list=[email],
            html_message=(
                render(
                    request,
                    self.email_template,
                    context={"otp": otp, "email": email, "request": request},
                ).content.decode("utf-8")
                if self.email_template
                else None
            ),
        )

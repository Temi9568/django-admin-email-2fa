from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from .settings import NAMESPACE


class AdminEmail2FAMiddleware(MiddlewareMixin):
    """Middleware to redirect non 2fa verified requests made to admin routes to the 2fa
    page."""

    def process_request(self, request: HttpRequest) -> HttpResponse:
        """Redrects non 2fa verified requests made to admin routes to the 2fa page.

        Args:
            request: The incoming HTTP request.

        Returns:
            HttpResponseRedirect to the 2FA page if conditions are met, otherwise
            default response.
        """

        if self.should_we_redirect_to_2fa_page(request):
            request.session["next_url"] = request.get_full_path()
            return HttpResponseRedirect(reverse("admin_email_2fa"))

        return self.get_response(request)

    def should_we_redirect_to_2fa_page(self, request: HttpRequest) -> bool:
        """Checks if the request should be redirected to the 2FA page.

        This checks if the request is for an admin page, the user is authenticated,
        and the user has not verified their 2FA status. Login and logout pages are
        excluded from this check, in order to prevent recursion.

        Args:
            request: The incoming HTTP request.

        Returns:
            True if the request should be redirected to the 2FA page, False otherwise.
        """
        path = request.path

        if (
            path.startswith(reverse("admin:index"))
            and path
            not in [
                reverse("admin:login"),
                reverse("admin_email_2fa"),
                reverse("admin:logout"),
            ]
            and request.user.is_authenticated
            and not request.session.get(NAMESPACE, {}).get("is_verified", False)
        ):
            return True

        return False

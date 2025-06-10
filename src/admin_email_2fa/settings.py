from django.conf import settings
from django.core.signals import setting_changed

from .otp import AbstractOTPGenerator
from .utils import klass_from_str

# Settings Namespace
NAMESPACE = "ADMIN_EMAIL_2FA"

# Default settings
DEFAULTS = {
    "DEFAULT_OTP_GENERATOR_CLASS": "admin_email_2fa.otp.RandomOTPGenerator",
    "DEFAULT_TEMPLATE": "admin_email_2fa/verification.html",
    "DEFAULT_EMAIL_TEMPLATE": "admin_email_2fa/email.html",
    "THROTTLE_IN_SECONDS": 60,
    "OTP_EXPIRATION_IN_SECONDS": 120,
    "MAX_RETRIES": 3,
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = ["DEFAULT_OTP_GENERATOR_CLASS"]


class APISettings:
    """A settings object that allows settings to be accessed as properties."""

    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        if user_settings:
            self._user_settings = self.__check_user_settings(user_settings)
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, NAMESPACE, {})
            self._user_settings = self.__check_user_settings(self._user_settings)
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = klass_from_str(val)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def __check_user_settings(self, user_settings):
        # Check default otp generator class
        if "DEFAULT_OTP_GENERATOR_CLASS" in user_settings:
            otp_gen_cls_str = user_settings["DEFAULT_OTP_GENERATOR_CLASS"]
            try:
                otp_gen_cls = klass_from_str(otp_gen_cls_str)
            except (ImportError, AttributeError) as e:
                raise RuntimeError(
                    f"Unable to import class {otp_gen_cls_str}. Setting "
                    f"`{NAMESPACE}.DEFAULT_OTP_GENERATOR_CLASS` must be a valid "
                    "class."
                ) from e

            if not issubclass(otp_gen_cls, AbstractOTPGenerator):
                raise RuntimeError(
                    f"`{otp_gen_cls}` is not subclass of `AbstractOTPGenerator`."
                )

        # Check types of other settings
        for setting in [
            "THROTTLE_IN_SECONDS",
            "OTP_EXPIRATION_IN_SECONDS",
            "MAX_RETRIES",
        ]:
            if setting in user_settings:
                user_setting = user_settings[setting]
                if not isinstance(user_setting, int) or user_setting < 0:
                    raise RuntimeError(
                        f"The setting `{NAMESPACE}.{setting}` must be of type "
                        "int and must be greater than 0."
                    )
        return user_settings

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")

        self.user_settings  # Force user settings to be checked on reload


app_settings = APISettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_api_settings(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == NAMESPACE:
        app_settings.reload()


setting_changed.connect(reload_api_settings)

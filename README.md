# Django Admin Email 2FA

A Django package that adds email-based two-factor authentication to the Django admin interface. When enabled, users will need to verify their identity using a one-time password (OTP) sent to their email address before accessing the admin site.

## Features

- Email-based two-factor authentication for Django admin
- Configurable OTP settings (length, expiration, retry limits)
- Session-based verification
- Customizable email templates
- Seamless integration with Django admin

## Installation

```bash
pip install django-admin-email-2fa
```

## Quick Start

1. Add `admin_email_2fa` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'admin_email_2fa',  # Add this line
]
```

2. Add the middleware to your `MIDDLEWARE` setting. It must be placed **after** `AuthenticationMiddleware`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Must be before our middleware
    'admin_email_2fa.middleware.AdminEmailOTPMiddleware',  # Add this line
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

3. Update your root URLconf (`urls.py`). The admin_email_2fa URLs must be included **before** the admin URLs:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', include('admin_email_2fa.urls')),  # Must be before admin URLs
    path('admin/', admin.site.urls),
]
```

4. Make sure you have configured your email settings in Django settings:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'your-email@example.com'
```

## Configuration

The package can be configured through the following settings in your Django settings file:

```python
# All settings are optional with sensible defaults

ADMIN_EMAIL_2FA = {
    'OTP_EXPIRATION_IN_SECONDS': 300,  # OTP Expiration time
    'THROTTLE_IN_SECONDS': 60,  # Minimum time between OTP generation requests
    'MAX_RETRIES': 3,  # Maximum number of incorrect attempts before requiring new OTP
    'DEFAULT_TEMPLATE': 'admin_email_2fa/verification.html',  # Template for verification page
    'DEFAULT_EMAIL_TEMPLATE': 'admin_email_2fa/email.html',  # Template for OTP email
    'DEFAULT_OTP_GENERATOR_CLASS': 'admin_email_2fa.otp.RandomOTPGenerator', # See section on OTP_GENERATOR_CLASS.
}
```

## Customizing Templates

The package uses Django's template system and follows Django's template lookup rules. You can override the default templates by creating your own in your project's templates directory.

### Template Locations

The package looks for templates in the following locations (in order):
1. Your project's templates directory: `your_project/templates/admin_email_2fa/`
2. The package's default templates

### Available Templates

#### 1. Verification Page Template
**Location**: `admin_email_2fa/verification.html`

This template renders the 2FA verification page. It extends the Django admin base template by default.

**Context Variables**:
- `email`: The user's email address where the OTP was sent
- `form`: The OTP verification form
- `error_msg`: Error message if verification failed
- `error_type`: Type of error (e.g., 'ExpiredToken', 'IncorrectAttempt', 'NoMoreRetries')
- `show_regen_btn`: Boolean indicating if the regenerate button should be shown
- `tkm`: Token manager state dictionary containing:
  - `otp_generator`: The class path of the OTP generator
  - `throttle_s`: Rate limit in seconds between OTP generations
  - `token_expiration_s`: Token expiration time in seconds
  - `max_retries`: Maximum number of allowed incorrect attempts
  - `incorrect_attempts`: Current number of incorrect attempts
  - `otp`: The current OTP value
  - `token_gen_time`: Timestamp of when the token was generated

#### 2. Email Template
**Location**: `admin_email_2fa/email.html`

This template is used for the email containing the OTP code.

**Context Variables**:
- `otp`: The generated OTP code
- `email`: The user's email address where the OTP was sent
- `request`: The current request object

### Example Directory Structure

To override the templates, create them in your project like this:

```
your_project/
├── templates/
│   └── admin_email_2fa/
│       ├── verification.html   # Override verification page
│       └── email.html         # Override email template
```

### Template Settings

You can configure which templates to use in your settings:

```python
ADMIN_EMAIL_2FA = {
    'DEFAULT_TEMPLATE': 'admin_email_2fa/verification.html',
    'DEFAULT_EMAIL_TEMPLATE': 'admin_email_2fa/email.html',
    # ... other settings ...
}
```

If you don't specify these settings, the package will use its default templates.

## OTP Generator Class

The package uses a flexible OTP generation system based on the `AbstractOTPGenerator` class. By default, it uses the `RandomOTPGenerator` class, but you can customize the OTP generation by either:

1. Configuring the default generator
2. Creating your own generator class

### Default Generator Configuration

The default `RandomOTPGenerator` can be configured through class attributes:

```python
from admin_email_2fa.otp import RandomOTPGenerator

class CustomRandomOTPGenerator(RandomOTPGenerator):
    digits_only = True    # Generate only digits (default: True)
    letters_only = False  # Generate only letters (default: False)
    length = 6           # Length of the OTP (default: 5)

# Add to your settings
ADMIN_EMAIL_2FA = {
    'DEFAULT_OTP_GENERATOR_CLASS': 'path.to.CustomRandomOTPGenerator',
    # ... other settings ...
}
```

### Creating a Custom Generator

You can create your own OTP generator by subclassing `AbstractOTPGenerator`:

```python
from admin_email_2fa.otp import AbstractOTPGenerator

class PrefixedOTPGenerator(AbstractOTPGenerator):
    """Generate OTPs with a custom prefix."""
    
    def __init__(self, prefix="TEST"):
        self.prefix = prefix
    
    def generate_otp(self) -> str:
        """Generate a token with a prefix."""
        import random
        digits = ''.join(str(random.randint(0, 9)) for _ in range(4))
        return f"{self.prefix}-{digits}"

# Add to your settings
ADMIN_EMAIL_2FA = {
    'DEFAULT_OTP_GENERATOR_CLASS': 'path.to.PrefixedOTPGenerator',
    # ... other settings ...
}
```

### Generator Requirements

If you create your own generator, it must:

1. Inherit from `AbstractOTPGenerator`
2. Implement the `generate_otp()` method
3. Return a string from `generate_otp()`

The generator class will be instantiated once per OTP generation request, so you can safely use instance attributes.

### Built-in Generator Options

The built-in `RandomOTPGenerator` provides these options:

- `digits_only`: Generate OTPs using only digits (0-9)
- `letters_only`: Generate OTPs using only letters (a-zA-Z)
- `length`: The length of the generated OTP

If both `digits_only` and `letters_only` are False, it will use both digits and letters.

Example configurations:

```python
# Digits-only OTP (default)
class DigitsOTPGenerator(RandomOTPGenerator):
    digits_only = True
    letters_only = False
    length = 6

# Letters-only OTP
class LettersOTPGenerator(RandomOTPGenerator):
    digits_only = False
    letters_only = True
    length = 8

# Mixed digits and letters
class MixedOTPGenerator(RandomOTPGenerator):
    digits_only = False
    letters_only = False
    length = 10
```

## Development

To set up the development environment:

1. Clone the repository:
```bash
git clone https://github.com/yourusername/django-admin-email-2fa.git
cd django-admin-email-2fa
```

2. Install development dependencies:
```bash
pip install -e ".[dev]"
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

4. Run tests:
```bash
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

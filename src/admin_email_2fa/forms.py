from django.forms import fields, forms


class OTPForm(forms.Form):
    """Form for handling OTP input."""

    otp = fields.CharField(min_length=1, max_length=None, required=True)

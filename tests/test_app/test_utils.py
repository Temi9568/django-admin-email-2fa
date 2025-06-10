import pytest

from admin_email_2fa.otp import RandomOTPGenerator
from admin_email_2fa.utils import klass_from_str, klass_to_string


class TestUtils:
    """Test the utils module."""

    def test_klass_to_string(self):
        """Test that the klass_to_string function converts a class to a string."""
        klass = RandomOTPGenerator
        klass_str = klass_to_string(klass)
        assert klass_str == "admin_email_2fa.otp.RandomOTPGenerator"

    def test_klass_from_str(self):
        """Test that the klass_from_str function converts a string to a class."""
        klass_str = "admin_email_2fa.otp.RandomOTPGenerator"
        klass = klass_from_str(klass_str)
        assert klass == RandomOTPGenerator

    def test_klass_from_str_invalid_module(self):
        """Test that the klass_from_str function raises an ImportError if the string
        is an invalid module."""
        klass_str = "nonexistent.module.Class"
        with pytest.raises(ImportError):
            klass_from_str(klass_str)

    def test_klass_from_str_invalid_class(self):
        """Test that the klass_from_str function raises an AttributeError if the string
        is an invalid class."""
        klass_str = "admin_email_2fa.otp.NonexistentClass"
        with pytest.raises(AttributeError):
            klass_from_str(klass_str)

    def test_roundtrip_conversion(self):
        """Test that the klass_to_string and klass_from_str functions roundtrip."""
        original_klass = RandomOTPGenerator
        klass_str = klass_to_string(original_klass)
        recovered_klass = klass_from_str(klass_str)
        assert recovered_klass == original_klass

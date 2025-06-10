import time

import pytest

from admin_email_2fa.exceptions import (
    ExpiredToken,
    IncorrectAttempt,
    NoMoreRetries,
    ThrottleExceeded,
)
from admin_email_2fa.otp import RandomOTPGenerator, TokenManager


@pytest.fixture
def otp_generator():
    """Fixture to create a random OTP generator."""
    return RandomOTPGenerator()


@pytest.fixture
def token_manager(otp_generator):
    """Fixture to create a token manager."""
    return TokenManager(
        otp_generator=otp_generator,
        throttle_s=5,  # 5 seconds throttle
        token_expiration_s=300,  # 5 minutes expiration
        max_retries=3,
    )


class TestRandomOTPGenerator:
    """Test the RandomOTPGenerator class."""

    def test_generate_digits_only(self):
        """Test that the generate_otp method generates a string of digits only."""
        generator = RandomOTPGenerator()
        generator.digits_only = True
        generator.letters_only = False
        generator.length = 6

        otp = generator.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_letters_only(self):
        """Test that the generate_otp method generates a string of letters only."""
        generator = RandomOTPGenerator()
        generator.digits_only = False
        generator.letters_only = True
        generator.length = 8

        otp = generator.generate_otp()
        assert len(otp) == 8
        assert otp.isalpha()

    def test_generate_mixed(self):
        """Test that the generate_otp method generates a string of mixed digits and
        letters."""
        generator = RandomOTPGenerator()
        generator.digits_only = False
        generator.letters_only = False
        generator.length = 10

        otp = generator.generate_otp()
        assert len(otp) == 10
        assert any(c.isdigit() for c in otp) or any(c.isalpha() for c in otp)

    def test_invalid_configuration(self):
        """Test that the generate_otp method raises a ValueError if the configuration
        is invalid."""
        generator = RandomOTPGenerator()
        generator.digits_only = True
        generator.letters_only = True

        with pytest.raises(ValueError, match="Cannot generate token"):
            generator.generate_otp()


class TestTokenManager:
    def test_generate_token(self, token_manager: TokenManager):
        """Test that the generate_token method generates a token."""
        token_manager.generate_token()
        assert token_manager.token is not None
        assert isinstance(token_manager.token.otp, str)
        assert isinstance(token_manager.token.gen_time, float)

    def test_throttle(self, token_manager: TokenManager):
        """Test that the generate_token method raises a ThrottleExceeded exception if
        the token is generated too quickly."""
        token_manager.generate_token()
        with pytest.raises(ThrottleExceeded):
            token_manager.generate_token()

    def test_validate_correct_token(self, token_manager: TokenManager):
        """Test that the validate method does not raise an exception if the token is
        correct."""
        token_manager.generate_token()
        otp = token_manager.token.otp
        token_manager.validate(otp)  # Should not raise any exception

    def test_validate_incorrect_token(self, token_manager: TokenManager):
        """Test that the validate method raises an IncorrectAttempt exception if the
        token is incorrect."""
        token_manager.generate_token()
        with pytest.raises(IncorrectAttempt):
            token_manager.validate("wrong-token")

    def test_max_retries(self, token_manager: TokenManager):
        """Test that the validate method raises a NoMoreRetries exception if the token
        is incorrect too many times."""
        token_manager.generate_token()

        # Try incorrect tokens up to max_retries
        for _ in range(token_manager.max_retries - 1):
            with pytest.raises(IncorrectAttempt):
                token_manager.validate("wrong-token")

        # Next attempt should raise NoMoreRetries
        with pytest.raises(NoMoreRetries):
            token_manager.validate("wrong-token")

    def test_token_expiration(self, token_manager: TokenManager):
        """Test that the validate method raises an ExpiredToken exception if the
        token is expired."""
        token_manager.generate_token()
        # Manipulate the token generation time to simulate expiration
        token_manager._token = token_manager.token._replace(
            gen_time=time.time() - (token_manager.token_expiration_s + 1)
        )

        with pytest.raises(ExpiredToken):
            token_manager.validate(token_manager.token.otp)

    def test_state_serialization(self, token_manager: TokenManager):
        """Test that the dump_state method dumps the state of the token manager."""
        token_manager.generate_token()
        state = token_manager.dump_state()

        # Check that all required fields are present
        assert "otp_generator" in state
        assert "throttle_s" in state
        assert "token_expiration_s" in state
        assert "max_retries" in state
        assert "incorrect_attempts" in state
        assert "otp" in state
        assert "token_gen_time" in state

    def test_state_deserialization(self, token_manager: TokenManager):
        """Test that the reload_state method reloads the state of the token manager."""
        token_manager.generate_token()
        state = token_manager.dump_state()

        # Reload state into a new token manager
        new_token_manager = TokenManager.reload_state(state)

        # Verify the state was properly restored
        assert new_token_manager.token.otp == token_manager.token.otp
        assert new_token_manager.token.gen_time == token_manager.token.gen_time
        assert new_token_manager.throttle_s == token_manager.throttle_s
        assert new_token_manager.token_expiration_s == token_manager.token_expiration_s
        assert new_token_manager.max_retries == token_manager.max_retries
        assert new_token_manager.incorrect_attempts == token_manager.incorrect_attempts

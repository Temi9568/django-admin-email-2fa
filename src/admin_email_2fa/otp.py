import random
import time
from abc import ABC, abstractmethod
from typing import NamedTuple

from .exceptions import ExpiredToken, IncorrectAttempt, NoMoreRetries, ThrottleExceeded
from .utils import klass_from_str, klass_to_string


class Token(NamedTuple):
    """Represents a token."""

    otp: str
    gen_time: float


class AbstractOTPGenerator(ABC):
    """Abstract base class for otp generators."""

    @abstractmethod
    def generate_otp(self) -> str:
        """Generate a token."""
        raise NotImplementedError("Subclasses must implement this method.")


class RandomOTPGenerator(AbstractOTPGenerator):
    """Generates a random otp consisting of digits and/or letters."""

    digits_only = True
    letters_only = False
    length = 5

    def generate_otp(self) -> str:
        """Generate a random otp based on the specified class attributes.

        The otp can consist of digits, letters, or both based on the
        `digits_only` and `letters_only` class attributes.

        The otp length is determined by the `length` class attribute.

        Returns:
            A randomly generated otp as a string.

        Raises:
            ValueError: If both `digits_only` and `letters_only` are set to True.

        """

        if self.digits_only and self.letters_only:
            raise ValueError(
                "Cannot generate token. Expected only one of `digits_only` or "
                "`letters_only` to be true."
            )

        if self.digits_only:
            characters = "0123456789"
        elif self.letters_only:
            characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        else:
            # If both digits_only and letters_only are False, use both
            characters = (
                "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            )
        token = "".join(random.choice(characters) for _ in range(self.length))
        return token


class TokenManager:
    """Manages the generation and validation of tokens using an OTP generator."""

    def __init__(
        self,
        otp_generator: AbstractOTPGenerator,
        throttle_s: int,
        token_expiration_s: int,
        max_retries: int,
    ):
        """Initialize the TokenManager with an OTP generator and configuration.

        Args:
            otp_generator: An instance of AbstractOTPGenerator to generate tokens.
            throttle_s: The rate limit in seconds for generating a new token.
            token_expiration_s: The expiration time for the token in seconds.
            max_retries: The maximum number of incorrect attempts allowed before
                raising an exception.
        """
        self._otp_generator = otp_generator
        self._throttle_s = throttle_s
        self._token_expiration_s = token_expiration_s
        self._max_retries = max_retries
        self._incorrect_attempts = 0

    @property
    def token(self) -> Token:
        """Returns the current token."""
        return self._token

    @property
    def otp_generator(self) -> AbstractOTPGenerator:
        """Returns the OTP generator used by this manager."""
        return self._otp_generator

    @property
    def throttle_s(self) -> int:
        """Returns the rate limit in seconds for generating a new token."""
        return self._throttle_s

    @property
    def token_expiration_s(self) -> int:
        """Returns the token expiration time in seconds."""
        return self._token_expiration_s

    @property
    def max_retries(self) -> int:
        """Returns the maximum number of incorrect attempts allowed before raising an
        exception."""
        return self._max_retries

    @property
    def incorrect_attempts(self) -> int:
        """Returns the current number of incorrect attempts made to validate the
        token."""
        return self._incorrect_attempts

    def time_since_gen(self) -> float:
        """Returns the time (in seconds) since the token was generated."""
        if getattr(self, "_token", None) is None:
            raise ValueError(
                "Token has not been generated yet. Ensure you call replace_token() "
                "first."
            )

        return time.time() - self.token.gen_time

    def generate_token(self, ignore_rate_limit=False) -> None:
        """Generates a new token and replaces the currently stored token with
        the newly generated one.

        Args:
            ignore_rate_limit: If True, bypasses the rate limit check and forces
                a token replacement. Defaults to False.

        Raises:
            ThrottleExceeded: If attempting to generate a token too soon and
            `ignore_rate_limit` is set to False.
        """
        if not ignore_rate_limit and getattr(self, "_token", None):
            time_since_gen = self.time_since_gen()
            if time_since_gen < self.throttle_s:  # type: ignore
                time_to_wait = self.throttle_s - self.time_since_gen()  # type: ignore
                raise ThrottleExceeded(
                    "Attempting to generate a token too soon, please "
                    f"wait {time_to_wait: .0f} seconds before trying again."
                )

        # Generate a new token
        token = self._otp_generator.generate_otp()
        self._token = Token(otp=token, gen_time=time.time())
        self._incorrect_attempts = 0

    def validate(self, token: str) -> None:
        """Validate the provided token against the stored token.

        Args:
            token: The token to validate.

        Raises:
            ExpiredToken: If the stored token has expired.
            NoMoreRetries: If too many incorrect attempts have been made against
            the stored token.
            IncorrectAttempt: If the token is invalid.
        """
        # Check expiry
        if self.token_expiration_s and (
            self.time_since_gen() > self.token_expiration_s
        ):
            raise ExpiredToken("Token has expired. Please generate a new token.")

        # Check token
        if self.token.otp != token:
            self._incorrect_attempts += 1

            # Check retry count
            if self.max_retries and self.incorrect_attempts >= self.max_retries:
                raise NoMoreRetries("Maximum number of incorrect attempts exceeded.")

            raise IncorrectAttempt("Incorrect token provided. Please try again.")

        return None  # Valid token

    def dump_state(self) -> dict:
        """Dump the state of the TokenManager to a dictionary.

        Returns:
            A dictionary representation of the TokenManager state. The otp
            generator is converted into a serializable string format (i.e its
            absolute import path for the class).
        """
        return {
            "otp_generator": klass_to_string(self.otp_generator.__class__),
            "throttle_s": self.throttle_s,
            "token_expiration_s": self.token_expiration_s,
            "max_retries": self.max_retries,
            "incorrect_attempts": self.incorrect_attempts,
            "otp": self.token.otp,
            "token_gen_time": self.token.gen_time,
        }

    @staticmethod
    def reload_state(data: dict) -> "TokenManager":
        """Reload the TokenManager state from a dictionary.

        Args:
            data: A dictionary containing the state of the TokenManager.

        Returns:
            An instance of TokenManager initialized with the provided state.

        Raises:
            ValueError: If the provided data is missing required keys or has invalid
            types.
        """
        key_types = {
            "otp_generator": (AbstractOTPGenerator, False),
            "throttle_s": (int, True),
            "token_expiration_s": (int, True),
            "max_retries": (int, True),
            "incorrect_attempts": (int, True),
            "otp": (str, True),
            "token_gen_time": (float, True),
        }

        # Check for missing keys
        missing_keys = set(key_types) - set(data)
        if missing_keys:
            raise ValueError(
                f"Unable to reload state as the following keys are "
                f"missing:\n{missing_keys}"
            )

        # Import the otp generator
        try:
            otp_generator = data["otp_generator"]
            klass = klass_from_str(otp_generator)
            data["otp_generator"] = klass()
        except (ImportError, AttributeError):
            raise ValueError(f"Failed to import the otp generator {otp_generator}")

        # Check Types
        for key, value in data.items():
            expected_type, coerce = key_types[key]

            if not isinstance(value, expected_type):
                raise_error = True

                if coerce:
                    try:
                        data[key] = expected_type(value)
                        raise_error = False
                    except Exception:
                        pass

                if raise_error:
                    raise ValueError(
                        f"Invalid Value. The value `{value}` associated with "
                        f"the key {key} should be an instance of {expected_type}"
                    )

        otp = data.pop("otp")
        token_gen_time = data.pop("token_gen_time")
        retry_count = data.pop("incorrect_attempts")

        tkm = TokenManager(**data)
        tkm._token = Token(otp=otp, gen_time=token_gen_time)
        tkm._incorrect_attempts = retry_count

        return tkm

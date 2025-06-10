import os
import sys
from pathlib import Path

import django
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


def pytest_configure():
    """Configure pytest to use our test settings."""
    # Add the root directory to PYTHONPATH
    root_dir = Path(__file__).resolve().parent.parent
    sys.path.append(str(root_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")
    django.setup()


@pytest.fixture
def admin_user():
    """Create a superuser for testing."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass123"
    )

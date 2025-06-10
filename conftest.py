import os
import sys
from pathlib import Path

# Add the root directory to PYTHONPATH
root_dir = Path(__file__).resolve().parent
sys.path.append(str(root_dir))

# Add src directory to PYTHONPATH so our package can be imported
sys.path.append(str(root_dir / "src"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")

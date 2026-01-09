#!/usr/bin/env python
"""Django command-line utility for Feature-Based Architecture."""

import os
import sys
from pathlib import Path


def main() -> None:
    """Run administrative tasks from the repo root."""
    project_root = Path(__file__).resolve().parent

    # Add project root and api folder to path for imports
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "api"))

    # Use new config location
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Ensure it is installed and available on your PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

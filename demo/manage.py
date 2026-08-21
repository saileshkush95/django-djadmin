#!/usr/bin/env python
"""Django's command-line utility for the djadmin demo project."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Run this with `uv run demo/manage.py …` "
            "from the project root, or activate the virtualenv first."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

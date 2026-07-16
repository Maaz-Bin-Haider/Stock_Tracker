"""Settings for the host pytest run: dev settings + eager Celery so export
jobs run inline (no broker), and export files go to a temp directory."""

import tempfile
from pathlib import Path

from .dev import *  # noqa: F403

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EXPORTS_ROOT = Path(tempfile.gettempdir()) / "stock_tracker_test_exports"
MEDIA_ROOT = Path(tempfile.gettempdir()) / "stock_tracker_test_media"

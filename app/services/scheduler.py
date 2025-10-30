"""Scheduler service - DEPRECATED.

This module is deprecated and replaced by the worker-based architecture.
The new system uses app/workers/dispatcher.py for reliable notification dispatch.

DO NOT START APScheduler IN THE WEB PROCESS.
"""

import logging

logger = logging.getLogger(__name__)

def setup_scheduler():
    """DEPRECATED - Do not use APScheduler in web process."""
    logger.warning(
        "APScheduler setup_scheduler() called - this is deprecated. "
        "Use app/workers/dispatcher.py instead."
    )
    pass

# Legacy compatibility
scheduler = None
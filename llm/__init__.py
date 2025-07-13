__version__ = "0.1.0"

from .local import request_for_commands
from .cloud import get_daily_report
__all__ = [
    "request_for_commands",
    "get_daily_report"
]
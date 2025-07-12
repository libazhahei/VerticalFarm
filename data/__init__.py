__version__ = "0.1.0"

from .tables import BoardData
from .config import init_schema

__all__ = ["BoardData", "init_schema"]
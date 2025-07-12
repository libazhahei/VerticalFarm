__version__ = "0.1.0"

from .config import init_schema
from .tables import BoardData

__all__ = ["BoardData", "init_schema"]

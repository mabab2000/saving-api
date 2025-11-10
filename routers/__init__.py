"""Routers package - re-export router modules for easy import.

This file exposes the individual router modules so callers can do:
	from routers import auth, savings, loans, penalties, users, dashboard, stats_ws

Keep this list in sync when adding/removing router modules.
"""

from . import auth
from . import savings
from . import loans
from . import penalties
from . import users
from . import dashboard
from . import stats_ws

__all__ = [
	"auth",
	"savings",
	"loans",
	"penalties",
	"users",
	"dashboard",
	"stats_ws",
]
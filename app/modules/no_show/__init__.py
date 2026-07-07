"""app/modules/no_show/__init__.py — No-Show Blueprint tanımı"""

from flask import Blueprint

no_show_bp = Blueprint("no_show", __name__)

from . import routes  # noqa: F401, E402

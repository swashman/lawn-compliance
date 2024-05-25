"""
Application config
"""

# Django
from django.apps import AppConfig

from . import __version__


class ComplianceConfig(AppConfig):
    name = "lawn_compliance"
    label = "lawn_compliance"
    verbose_name = f"Lawn Compliance v{__version__}"

    # def ready(self):
    # import asmek_authcogs.signals

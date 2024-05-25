"""Hooking into the auth system"""

from allianceauth import hooks

from . import app_settings


@hooks.register("discord_cogs_hook")
def register_cogs():
    """
    Registering our discord cogs
    """
    return app_settings.LAWN_COMPLIANCE_COGS

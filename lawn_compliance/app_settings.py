"""App Settings"""

# Django
from django.apps import apps
from django.conf import settings

# put your app settings here
LAWN_COMPLIANCE_COGS = getattr(
    settings,
    "LAWN_COMPLIANCE_COGS",
    [
        "lawn_compliance.cogs.compliance",
        "lawn_compliance.cogs.pagetest",
    ],
)

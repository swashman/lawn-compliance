"""Models."""

from django.db import models


class General(models.Model):
    """A meta model for app permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("own_corp", "Can access own corp compliance"),
            ("any_corp", "Can access any corp compliance"),
            ("alliance", "Can access alliance compliance"),
        )

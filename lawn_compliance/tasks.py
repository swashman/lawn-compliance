"""Tasks."""

from celery import shared_task
from corpstats import models
from discord import Embed
from discord.colour import Color

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.tasks import QueueOnce

logger = get_extension_logger(__name__)


@shared_task(bind=True, base=QueueOnce)
def send_alliance_compliance(self):
    channel_id = settings.LAWN_COMPLIANCE_CHANNEL[0]
    if not channel_id:
        return "No Channel ID set"
    from aadiscordbot.tasks import send_message

    embed = Embed(title="Alliance Compliance")
    try:
        ally = EveAllianceInfo.objects.get(alliance_id=150097440)
        corps = EveCorporationInfo.objects.filter(alliance=ally).order_by(
            "corporation_name"
        )
        corpstring = ""
        for corp in corps:
            corpstring += f"**{corp}**\n"
            try:
                cstat = models.CorpStat.objects.get(
                    corp_id__corporation_name__iexact=corp
                )
                (
                    members,
                    mains,
                    orphans,
                    unregistered,
                    total_mains,
                    total_unreg,
                    total_members,
                    auth_percent,
                    alt_ratio,
                    service_percent,
                    tracking,
                    services,
                ) = cstat.get_stats()
                corpstring += f"Mains:{total_mains}\n"
                corpstring += f"Members:{total_members}\n"
                corpstring += f"Unregistered:{total_unreg}\n\n"
            except models.CorpStat.DoesNotExist:
                corpstring += "!!! THIS CORP IS NOT REGISTERED !!!\n\n"
        embed.description = corpstring
        embed.colour = Color.blurple()
    except ObjectDoesNotExist:
        logger.error("Alliance or corp data doesnot exist in the database")
        embed.description = "An error has occured, please contact IT"
        embed.color = Color.red()
    send_message(embed=embed, channel_id=channel_id)

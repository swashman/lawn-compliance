"""Tasks."""

from aadiscordbot.tasks import send_message
from celery import shared_task
from corpstats.models import CorpStat
from corptools.models import CorporationAudit
from discord import Embed
from discord.colour import Color
from structures.models import Owner

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.tasks import QueueOnce

logger = get_extension_logger(__name__)

# Set MIN_VALID_CHARACTERS and THRESHOLD_DAYS with defaults if not in settings
MIN_VALID_CHARACTERS = getattr(settings, "MIN_VALID_CHARACTERS", 5)
THRESHOLD_DAYS = getattr(settings, "THRESHOLD_DAYS", 5)


@shared_task(bind=True, base=QueueOnce)
def send_alliance_compliance(self):
    channel_id = settings.LAWN_COMPLIANCE_CHANNEL[0]
    if not channel_id:
        return "No Channel ID set"

    # Initialize variables for multiple embeds
    embeds = []
    embed = Embed(title="Corp Member Compliance")
    corpstring = ""
    page_number = 1  # Track page number

    try:
        ally = EveAllianceInfo.objects.get(alliance_id=150097440)
        corps = EveCorporationInfo.objects.filter(alliance=ally).order_by(
            "corporation_name"
        )

        for corp in corps:
            # Add the header for each corporation
            corpstring += f"## {corp}\n"

            # Populate data for the corporation
            try:
                cstat = CorpStat.objects.get(corp_id__corporation_name__iexact=corp)
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

                corpstring += f"👤 **Mains:** {total_mains}\n"

                if total_unreg > 0:
                    unregistered_warning = " ⚠️" if total_unreg > 1 else ""
                    corpstring += f"🚫 **Unregistered Toons:** {total_unreg}{unregistered_warning}\n"
                else:
                    corpstring += "🟢 **Unregistered Toons:** All Registered\n"

            except CorpStat.DoesNotExist:
                corpstring += "🔴 Corp Stats Token Missing!\n"

            # Token checks for outdated and missing
            outdated_tokens = []
            missing_tokens = []
            yellow_tokens = []

            # Corp Tools check
            try:
                ctools = CorporationAudit.objects.get(
                    corporation_id__corporation_name__iexact=corp
                )

                if ctools.last_update_wallet:
                    wallet_days_since = (
                        timezone.now() - ctools.last_update_wallet
                    ).days
                    if wallet_days_since > THRESHOLD_DAYS:
                        outdated_tokens.append("Corp Tools Wallet")
                else:
                    missing_tokens.append("Corp Tools Wallet")

                if ctools.last_update_assets:
                    assets_days_since = (
                        timezone.now() - ctools.last_update_assets
                    ).days
                    if assets_days_since > THRESHOLD_DAYS:
                        outdated_tokens.append("Corp Tools Assets")
                else:
                    missing_tokens.append("Corp Tools Assets")

            except CorporationAudit.DoesNotExist:
                missing_tokens.append("Corp Tools")

            # Structures check
            try:
                struct = Owner.objects.get(
                    corporation_id__corporation_name__iexact=corp
                )
                enabled = struct.valid_characters_count()

                if struct.is_up == 1:
                    if enabled < MIN_VALID_CHARACTERS:
                        yellow_tokens.append(
                            f"Structures: Below recommended of {MIN_VALID_CHARACTERS}"
                        )
                    else:
                        corpstring += f"🟢 **Structures:** {enabled} Characters\n"
            except Owner.DoesNotExist:
                missing_tokens.append("Structures")

            # Status Lines
            if not outdated_tokens and not missing_tokens:
                corpstring += "🟢 **All Tokens OK**\n"

            if yellow_tokens:
                corpstring += f"🟡 **Warnings:** {', '.join(yellow_tokens)}\n"

            if outdated_tokens:
                corpstring += f"🟠 **Outdated Tokens:** {', '.join(outdated_tokens)}\n"

            if missing_tokens:
                corpstring += f"🔴 **Missing Tokens:** {', '.join(missing_tokens)}\n"

            corpstring += "\n"

            # Check if adding this corporation would exceed the character limit
            if len(corpstring) > 3000:
                # Finalize and store the current embed
                embed.description = corpstring
                embed.colour = Color.blurple()
                embeds.append(embed)

                # Start a new embed and reset variables
                embed = Embed(title="Corp Member Compliance")
                corpstring = (
                    f"## {corp}\n"  # Start new corpstring with the current corp
                )
                page_number += 1

        # Add the last page if any content remains
        if corpstring:
            embed.description = corpstring
            embed.colour = Color.blurple()
            embeds.append(embed)

    except ObjectDoesNotExist:
        logger.error("Alliance or corp data does not exist in the database")
        error_embed = Embed(
            title="Error",
            description="An error has occurred, please contact IT",
            color=Color.red(),
        )
        send_message(embed=error_embed, channel_id=channel_id)
        return

    # Calculate total pages
    total_pages = len(embeds)

    # Send all embeds sequentially with "Page X of Y" footer
    for i, embed in enumerate(embeds):
        embed.set_footer(text=f"Page {i + 1} of {total_pages}")
        send_message(embed=embed, channel_id=channel_id)


@shared_task(bind=True)
def send_corp_compliance(self, input_corp, channel_id=None, user_id=None):
    """
    Celery task to send a detailed corporation compliance embed with wallet, assets, structures checks.
    """
    embeds = []
    corp_embed = Embed(title=f"{input_corp} Compliance Overview")
    corpstring = ""

    # Initial check for CorpStat
    corp = None
    try:
        corp = CorpStat.objects.get(corp_id__corporation_name__iexact=input_corp)
    except CorpStat.DoesNotExist:
        corpstring += "🔴 Corp Stats Token Missing [Add Token](https://auth.lawnalliance.space/corpstat/add/)\n\n"

    if corp:
        # Overview Section
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
        ) = corp.get_stats()

        corpstring += f"👤 **Mains:** {total_mains}\n"
        corpstring += f"👥 **Total Characters:** {total_members}\n"
        if total_unreg > 0:
            corpstring += f"🚫 **Unregistered Toons:** {total_unreg} ⚠️\n\n"
        else:
            corpstring += "🟢 **Unregistered Toons:** All Registered\n\n"

        # Services Compliance Section
        corpstring += "**Services Compliance**\n"
        for service in services:
            percent = service_percent[service]["percent"]
            icon = (
                "✅"
                if percent == 100.0
                else "🟡" if percent >= 75.0 else "🟠" if percent >= 50.0 else "🔴"
            )
            corpstring += f"{icon} {service}: {percent}%\n"
        corpstring += "\n"

    # Wallet, Assets, and Structures Checks
    token_statuses = {}

    try:
        ctools = CorporationAudit.objects.get(
            corporation_id__corporation_name__iexact=input_corp
        )

        # Wallet check
        if ctools.last_update_wallet:
            wallet_days_since = (timezone.now() - ctools.last_update_wallet).days
            if wallet_days_since > THRESHOLD_DAYS:
                token_statuses["Wallet"] = (
                    "🟠 Outdated [Update Token](https://auth.lawnalliance.space/audit/corp/r/#/)"
                )
            else:
                token_statuses["Wallet"] = "🟢 OK"
        else:
            token_statuses["Wallet"] = (
                "🔴 Missing [Add Token](https://auth.lawnalliance.space/audit/corp/r/#/)"
            )

        # Assets check
        if ctools.last_update_assets:
            assets_days_since = (timezone.now() - ctools.last_update_assets).days
            if assets_days_since > THRESHOLD_DAYS:
                token_statuses["Assets"] = (
                    "🟠 Outdated [Update Token](https://auth.lawnalliance.space/audit/corp/r/#/)"
                )
            else:
                token_statuses["Assets"] = "🟢 OK"
        else:
            token_statuses["Assets"] = (
                "🔴 Missing [Add Token](https://auth.lawnalliance.space/audit/corp/r/#/)"
            )

    except CorporationAudit.DoesNotExist:
        token_statuses["Wallet"] = (
            "🔴 Missing [Add Token](https://auth.lawnalliance.space/audit/corp/r/#/)"
        )
        token_statuses["Assets"] = (
            "🔴 Missing [Add Token](https://auth.lawnalliance.space/audit/corp/r/#/)"
        )

    # Structures check
    try:
        struct = Owner.objects.get(corporation_id__corporation_name__iexact=input_corp)
        enabled = struct.valid_characters_count()
        if struct.is_up == 1:
            if enabled < MIN_VALID_CHARACTERS:
                token_statuses["Structures"] = (
                    f"🟡 {enabled} Characters (Recommend {MIN_VALID_CHARACTERS}) [Add Token](https://auth.lawnalliance.space/structures/add_structure_owner)"
                )
            else:
                token_statuses["Structures"] = f"🟢 {enabled} Characters"
    except Owner.DoesNotExist:
        token_statuses["Structures"] = (
            "🔴 Missing [Add Token](https://auth.lawnalliance.space/structures/add_structure_owner)"
        )

    # Corp Stats Token Status
    if corp:
        token_statuses["Corp Stats"] = "🟢 OK"

    # Display each token status individually
    corpstring += "**Token Status**\n"
    for token, status in token_statuses.items():
        corpstring += f"{token}: {status}\n"
    corpstring += "\n"

    # Unregistered Characters Section with On-the-Fly Split
    if corp and unregistered:
        corpstring += "**Unregistered Characters**\n"
        for character in unregistered:
            character_info = f"{character} - Join Date: {character.start_date.strftime('%Y-%m-%d')}\n"

            # Check if adding this character would exceed the limit
            if len(corpstring) + len(character_info) > 3000:
                # Finalize and store the current embed
                corp_embed.description = corpstring
                corp_embed.colour = Color.blurple()
                embeds.append(corp_embed)

                # Start a new embed
                corp_embed = Embed(title=f"{input_corp} Compliance (continued)")
                corpstring = "**Unregistered Characters (cont.)**\n" + character_info
            else:
                corpstring += character_info

    # Finalize last embed
    corp_embed.description = corpstring
    corp_embed.colour = Color.blurple()
    embeds.append(corp_embed)

    # Send the embeds
    for embed in embeds:
        if channel_id:
            send_message(embed=embed, channel_id=channel_id)
        elif user_id:
            send_message(embed=embed, user_id=user_id)

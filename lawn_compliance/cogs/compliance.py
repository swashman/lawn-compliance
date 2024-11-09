from aadiscordbot.cogs.utils.decorators import (
    message_in_channels,
    sender_has_any_perm,
    sender_has_perm,
)
from discord import AutocompleteContext, option
from discord.commands import SlashCommandGroup
from discord.ext import commands

from django.conf import settings

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.modules.discord.models import DiscordUser

from lawn_compliance.tasks import send_alliance_compliance, send_corp_compliance

logger = get_extension_logger(__name__)


class Compliance(commands.Cog):
    """
    All about me!
    """

    def __init__(self, bot):
        self.bot = bot

    compliance_commands = SlashCommandGroup(
        "compliance",
        "Compliance Commands",
        guild_ids=[int(settings.DISCORD_GUILD_ID)],
    )

    async def search_corps(ctx: AutocompleteContext):
        """
        Returns a list of corps within a specific alliance that match the characters entered so far.
        """

        try:
            # Get the specified alliance
            ally = EveAllianceInfo.objects.get(alliance_id=150097440)

            # Filter corporations by alliance and search term
            matching_corps = (
                EveCorporationInfo.objects.filter(
                    alliance=ally, corporation_name__icontains=ctx.value
                )
                .order_by("corporation_name")
                .values_list("corporation_name", flat=True)[:10]
            )

            return list(matching_corps)

        except EveAllianceInfo.DoesNotExist:
            # Return an empty list if the alliance doesn't exist
            return []

    # alliance command
    @compliance_commands.command(
        name="alliance", guild_ids=[int(settings.DISCORD_GUILD_ID)], pass_context=True
    )
    @sender_has_perm("lawn_compliance.alliance")
    # @message_in_channels(settings.LAWN_COMPLIANCE_CHANNEL)
    async def alliance(self, ctx):
        """
        Returns basic compliance data for all corps in the alliance
        """
        await ctx.defer(ephemeral=False)
        channel_id = ctx.channel.id
        send_alliance_compliance.delay(channel_id=channel_id)
        await ctx.respond(
            "Requested Alliance Compliance. It will be shown here momentarily.",
            ephemeral=False,
        )

    # any corp command
    @compliance_commands.command(
        name="corp", guild_ids=[int(settings.DISCORD_GUILD_ID)]
    )
    @sender_has_any_perm(["lawn_compliance.alliance", "lawn_compliance.any_corp"])
    @message_in_channels(settings.LAWN_COMPLIANCE_CHANNEL)
    @option(
        "corp",
        description="Search for a corp!",
        autocomplete=search_corps,
    )
    async def corp(self, ctx, corp: str):
        """
        Returns compliance data for selected corp
        """
        await ctx.defer(ephemeral=False)
        send_corp_compliance.delay(
            input_corp=corp, channel_id=settings.LAWN_COMPLIANCE_CHANNEL[0]
        )
        await ctx.respond(f"Requested compliance data for **{corp}**.", ephemeral=False)

    # own corp command
    @compliance_commands.command(
        name="mycorp", guild_ids=[int(settings.DISCORD_GUILD_ID)]
    )
    @sender_has_any_perm(
        [
            "lawn_compliance.alliance",
            "lawn_compliance.any_corp",
            "lawn_compliance.own_corp",
        ]
    )
    async def mycorp(self, ctx):
        """
        Returns persons own corp compliance data
        """
        await ctx.defer(ephemeral=True)
        try:
            duser = DiscordUser.objects.get(uid=ctx.author.id)
            user = duser.user
            profile = user.profile
            mchar = profile.main_character
            corp = mchar.corporation_name
            send_corp_compliance.delay(input_corp=corp, user_id=ctx.author.id)
            await ctx.respond(
                f"Sent compliance data for your corp, **{corp}**, via DM.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error("Failed to determine the requester's corp: %s", e)
            await ctx.respond(
                message="Unable to retrieve your corp data. Please check your tokens in the alliance auth system.",
                ephemeral=True,
            )


def setup(bot):
    bot.add_cog(Compliance(bot))

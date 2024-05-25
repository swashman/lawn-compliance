from aadiscordbot.cogs.utils.decorators import (
    message_in_channels,
    sender_has_any_perm,
    sender_has_perm,
)
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.modules.discord.models import DiscordUser
from corpstats import models
from discord import AutocompleteContext, Embed, InputTextStyle, Interaction, option
from discord.colour import Color
from discord.commands import SlashCommandGroup
from discord.embeds import Embed
from discord.ext import commands
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

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

    # generates a corp embed
    def get_corp_embed(self, input_corp):
        embed = Embed(title="{corp_name} Compliance".format(corp_name=input_corp))
        try:
            corp = models.CorpStat.objects.get(
                corp_id__corporation_name__iexact=input_corp
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
            ) = corp.get_stats()

            embed.set_thumbnail(url=corp.corp_logo())
            embed.add_field(name=f"Mains", value=total_mains, inline=True)
            embed.add_field(name=f"Members", value=total_members, inline=True)
            embed.add_field(name=f"Unregistered", value=total_unreg, inline=True)
            svcstring = ""
            for service in services:
                svcstring += "{svc}: {svcpct}\n".format(
                    svc=service, svcpct=service_percent[service]["percent"]
                )
            embed.add_field(name=f"Services", value=svcstring, inline=False)
            embed.add_field(
                name=f"Unregistered Characters",
                value="\n".join(str(x) for x in unregistered),
                inline=False,
            )
            embed.colour = Color.blurple()
        except models.CorpStat.DoesNotExist:
            embed.colour = Color.red()
            embed.description = (
                "Corp **{corp_name}** does not exist in our Auth system"
            ).format(corp_name=input_corp)
        return embed

    # generates a alliance embed
    def get_alliance_embed(self, input_alliance):
        embed = Embed(title="Alliance Compliance")
        try:
            ally = EveAllianceInfo.objects.get(alliance_id=input_alliance)
            corps = EveCorporationInfo.objects.filter(alliance=ally).order_by(
                "corporation_name"
            )
            corpstring = ""
            for corp in corps:
                corpstring += "**{c}**\n".format(c=corp)
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
                    corpstring += "Mains:{x}\n".format(x=total_mains)
                    corpstring += "Members:{x}\n".format(x=total_members)
                    corpstring += "Unregistered:{x}\n\n".format(x=total_unreg)
                except models.CorpStat.DoesNotExist:
                    corpstring += "!!! THIS CORP IS NOT REGISTERED !!!\n\n"
            embed.description = corpstring
            embed.colour = Color.blurple()
        except ObjectDoesNotExist:
            logger.error("Alliance or corp data doesnot exist in the database")
            embed.description = "An error has occured, please contact IT"
            embed.color = Color.red()
        return embed

    async def search_corps(ctx: AutocompleteContext):
        """Returns a list of corps that begin with the characters entered so far."""
        return list(
            models.CorpStat.objects.filter(
                corp_id__corporation_name__icontains=ctx.value
            ).values_list("corp_id__corporation_name", flat=True)[:10]
        )

    # alliance command
    @compliance_commands.command(
        name="alliance", guild_ids=[int(settings.DISCORD_GUILD_ID)], pass_context=True
    )
    @sender_has_perm("lawn_compliance.alliance")
    # @message_in_channels([int(settings.LAWN_COMPLIANCE_CHANNELS)])
    async def alliance(self, ctx):
        """
        Returns basic compliance data for all corps in the alliance
        """
        await ctx.defer(ephemeral=False)
        await ctx.respond(embed=self.get_alliance_embed(150097440), ephemeral=False)

    # any corp command
    @compliance_commands.command(
        name="corp", guild_ids=[int(settings.DISCORD_GUILD_ID)]
    )
    @sender_has_any_perm(["lawn_compliance.alliance", "lawn_compliance.any_corp"])
    # @message_in_channels(settings.LAWN_COMPLIANCE_CHANNELS)
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
        await ctx.respond(embed=self.get_corp_embed(corp), ephemeral=False)

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
        try:
            duser = DiscordUser.objects.get(uid=ctx.author.id)
            user = duser.user
            profile = user.profile
            mchar = profile.main_character
            corp = mchar.corporation_name
        except:
            logger.error("Could not figure out who made the request")
            pass
        await ctx.defer(ephemeral=True)
        await ctx.respond(embed=self.get_corp_embed(corp), ephemeral=True)


def setup(bot):
    bot.add_cog(Compliance(bot))

from aadiscordbot.cogs.utils.decorators import (
    message_in_channels,
    sender_has_any_perm,
    sender_has_perm,
)
from corpstats import models
from discord import AutocompleteContext, Embed, option
from discord.colour import Color
from discord.commands import SlashCommandGroup
from discord.ext import commands

from django.conf import settings

from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.modules.discord.models import DiscordUser

from lawn_compliance.tasks import send_alliance_compliance

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
        embed = Embed(title=f"{input_corp} Compliance")
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
            embed.add_field(name="Mains", value=total_mains, inline=True)
            embed.add_field(name="Members", value=total_members, inline=True)
            embed.add_field(name="Unregistered", value=total_unreg, inline=True)

            svcstring = ""
            for service in services:
                percent = service_percent[service]["percent"]
                # Add icons based on the percentage
                if percent == 100.0:
                    icon = "✅"
                elif percent >= 75.0:
                    icon = "🟡"
                elif percent >= 50.0:
                    icon = "🟠"
                else:
                    icon = "🔴"

                svcstring += "{icon} {svc}: {svcpct}%\n".format(
                    icon=icon, svc=service, svcpct=percent
                )
            embed.add_field(name="Services", value=svcstring, inline=False)

            # Helper function to chunk the data into multiple fields
            def chunk_string(s, chunk_size):
                return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]

            # Generate the unregistered characters list
            unregistered_characters = "\n".join(
                f"{x} - Start Date: {x.start_date.strftime('%Y-%m-%d')}"
                for x in unregistered
            )

            # Split the string into chunks of up to 1024 characters
            chunks = chunk_string(unregistered_characters, 1024)

            # Add each chunk as a separate embed field
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Unregistered Characters (Part {i + 1})",
                    value=chunk,
                    inline=False,
                )

            embed.colour = Color.blurple()
        except models.CorpStat.DoesNotExist:
            embed.colour = Color.red()
            embed.description = (
                "Corp **{corp_name}** does not exist in our Auth system"
            ).format(corp_name=input_corp)
        return embed

    async def search_corps(ctx: AutocompleteContext):
        """Returns a list of corps that begin with the characters entered so far."""
        return list(
            models.CorpStat.objects.filter(
                corp_id__corporation_name__icontains=ctx.value
            ).values_list("corp_id__corporation_name", flat=True)[:10]
        )

    ########
    # TODO: WE NEED TO MOVE THIS TO A TASK
    ########
    # alliance command
    @compliance_commands.command(
        name="alliance", guild_ids=[int(settings.DISCORD_GUILD_ID)], pass_context=True
    )
    @sender_has_perm("lawn_compliance.alliance")
    @message_in_channels(settings.LAWN_COMPLIANCE_CHANNEL)
    async def alliance(self, ctx):
        """
        Returns basic compliance data for all corps in the alliance
        """
        await ctx.defer(ephemeral=True)
        send_alliance_compliance.delay()
        await ctx.respond("Requested Alliance Compliance", ephemeral=True)

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
        await ctx.defer(ephemeral=True)
        try:
            duser = DiscordUser.objects.get(uid=ctx.author.id)
            user = duser.user
            profile = user.profile
            mchar = profile.main_character
            corp = mchar.corporation_name
            await ctx.respond(embed=self.get_corp_embed(corp), ephemeral=True)
        except Exception:
            logger.error("Could not figure out who made the request")
            await ctx.respond(
                message="Corp token missing from Corporation Stats Module! Please add your token in alliance auth!",
                ephemeral=True,
            )
            pass


def setup(bot):
    bot.add_cog(Compliance(bot))

import logging

logging.basicConfig(level=logging.INFO)

import re
import shutil
import tomli
import redis

import discord
from discord import ui
from discord.ext import commands
from __future__ import annotations

REGEX_CODE = re.compile(r"\d{3} ?\d{3}")

try:
    with open("config.toml", "rb") as f:
        config = tomli.load(f)
except FileNotFoundError:
    print("config.toml was not found; creating a default config.")
    print("Edit your config file and restart the bot")
    shutil.copyfile("default.toml", "config.toml")
    exit(1)

db = redis.Redis(
    host=config["redis"]["host"],
    port=config["redis"]["port"],
    db=config["redis"]["db"],
)


class LinkModal(ui.Modal):
    def __init__(self, bot: IroBot):
        super().__init__(title="인증")
        self.bot = bot
        self.add_item(
            ui.InputText(
                label="닉네임",
                placeholder="마인크래프트 닉네임을 입력하세요.",
                row=1,
            )
        )
        self.add_item(
            ui.InputText(
                label="인증번호",
                placeholder="000000",
                min_length=6,
                max_length=6,
                row=2,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        nick = self.children[0].value
        code = self.children[1].value
        user = interaction.user
        print(f"user: {user}, nick: {nick}, code: {code}")  # DEBUG
        assert nick and code and isinstance(user, discord.Member)

        code = "".join(code.split())  # remove whitespace
        await user.remove_roles(self.bot.newbie_role)
        await user.edit(nick=nick)
        await interaction.response.send_message("성공적으로 인증되었습니다.", ephemeral=True)
        # if not db.exists(nickname):
        #    pass
        # else:
        #    pass


class VerifyView(ui.View):
    def __init__(self, bot: IroBot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(
        label=config["message"]["verify_button"],
        style=discord.ButtonStyle.green,
        custom_id="dislinkmc:verify",
    )
    async def verify(self, button: ui.Button, interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        if self.bot.newbie_role in interaction.user.roles:
            modal = LinkModal(self.bot)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("이미 인증된 계정입니다.", ephemeral=True)


class IroBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False

        self.working_guild: discord.Guild
        self.verify_channel: discord.TextChannel
        self.newbie_role: discord.Role

    async def on_ready(self):
        if self.initialized:
            return
        self.initialized = True

        guild = self.get_guild(config["discord"]["guild_id"])
        assert isinstance(guild, discord.Guild)

        channel = guild.get_channel(config["discord"]["verify_channel_id"])
        role = guild.get_role(config["discord"]["newbie_role_id"])
        assert isinstance(channel, discord.TextChannel)
        assert isinstance(role, discord.Role)

        self.working_guild = guild
        self.verify_channel = channel
        self.newbie_role = role

        print(repr(guild))  # DEBUG
        print(repr(channel))  # DEBUG
        print(repr(role))  # DEBUG

        view = VerifyView(self)
        self.add_view(view)

        msg = f"Logged in as {self.user} ({self.user.id})"  # type: ignore
        print(f"{msg}\n{'-'*len(msg)}")

    async def on_member_join(self, member: discord.Member):
        await member.add_roles(self.newbie_role)


intents = discord.Intents(members=True, guilds=True)
bot = IroBot(intents=intents)


@bot.slash_command(name="init", guild_ids=[config["discord"]["guild_id"]])
@commands.is_owner()
async def init(ctx: discord.ApplicationContext):
    await bot.verify_channel.send(view=VerifyView(bot))
    await ctx.respond("초기화가 완료되었습니다.", ephemeral=True)


@bot.slash_command(name="userinfo", guild_ids=[config["discord"]["guild_id"]])
@commands.is_owner()
async def userinfo(ctx: discord.ApplicationContext, user: discord.User):
    ... # TODO: Query info from DB


bot.run(config["bot"]["token"])

import logging

logging.basicConfig(level=logging.INFO)

from shutil import copyfile
from os.path import exists
from discord import ApplicationContext, ButtonStyle, Interaction, Intents, Member
from discord.ext import commands
from discord.ui import Modal, InputText, View, button, Button

from tomli import load
from redis import Redis
from re import compile

REGEX_CODE = compile(r"\d{3} ?\d{3}")

if exists("config.toml"):
    with open("config.toml", "rb") as f:
        config = load(f)
else:
    print("config.toml does not exists. generate default config.toml")
    copyfile("default_config.toml", "config.toml")
    print("Edit your config and restart this bot")

rd = Redis(
    host=config["redis"]["host"], port=config["redis"]["port"], db=config["redis"]["db"]
)


class LinkModal(Modal):
    def __init__(self) -> None:
        super().__init__(title="인증")
        self.add_item(InputText(label="닉네임", placeholder="마인크래프트 닉네임을 입력하세요."))
        self.add_item(
            InputText(
                label="인증번호", placeholder="000000", min_length=6, max_length=6, row=1
            )
        )

    async def callback(self, interaction: Interaction):
        nickname: str
        code: str
        nickname, code = map(lambda x: x.value, self.children)
        code = code.replace(" ", "")
        print(nickname, code)
        await interaction.user.remove_roles(newbie_role)
        await interaction.user.edit(nick=nickname)
        await interaction.response.send_message("성공적으로 인증되었습니다.", ephemeral=True)
        # if not rd.exists(nickname):
        #    pass
        # else:
        #    pass


class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label=config["message"]["verify_button"],
        style=ButtonStyle.green,
        custom_id="dislinkmc:verify",
    )
    async def verify(self, button: Button, interaction: Interaction):
        if newbie_role in interaction.user.roles:
            await interaction.response.send_modal(LinkModal())
        else:
            await interaction.response.send_message("이미 인증한 계정입니다.", ephemeral=True)


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(intents=Intents(members=True, guilds=True))
        self.views_added = False

    async def on_ready(self):

        global channel
        global newbie_role

        guild = self.get_guild(config["discord"]["guild_id"])
        channel = guild.get_channel(config["discord"]["verify_channel_id"])
        newbie_role = guild.get_role(config["discord"]["newbie_role_id"])
        print(repr(guild))
        print(repr(channel))
        print(repr(newbie_role))
        if not self.views_added:
            self.add_view(VerifyView())
            self.views_added = True

        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def on_member_join(self, member: Member):
        await member.add_roles(newbie_role)


bot = Bot()


@bot.slash_command(name="init", guild_ids=[config["discord"]["guild_id"]])
@commands.is_owner()
async def init(ctx: ApplicationContext):
    await channel.send(view=VerifyView())
    await ctx.respond("초기화가 완료되었습니다.", ephemeral=True)


bot.run(config["bot"]["token"])

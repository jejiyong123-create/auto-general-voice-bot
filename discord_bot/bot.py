import os
import asyncio
from typing import Set

import discord
from discord import app_commands
from discord.ext import commands


INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.voice_states = True


class AutoVoiceBot(commands.Bot):
	def __init__(self):
		super().__init__(command_prefix='!', intents=INTENTS)
		self.temp_channels: Set[int] = set()

	async def setup_hook(self) -> None:
		await self.tree.sync()

	async def on_ready(self):
		print(f"Logged in as {self.user} (id: {self.user.id})")

	async def on_voice_state_update(self, member, before, after):
		# If a tracked temp channel becomes empty, delete it
		channel = before.channel
		if channel and channel.id in self.temp_channels:
			# small delay to wait for quick rejoins
			await asyncio.sleep(1)
			if len(channel.members) == 0:
				try:
					await channel.delete()
				except Exception as e:
					print(f"Failed to delete channel {channel.id}: {e}")
				finally:
					self.temp_channels.discard(channel.id)


bot = AutoVoiceBot()


@bot.tree.command(name="create_voice", description="임시 음성채널을 생성합니다")
@app_commands.describe(name="음성채널 이름", user_limit="최대 사용자 수(선택, 0=무제한)")
async def create_voice(interaction: discord.Interaction, name: str, user_limit: int = 0):
	guild = interaction.guild
	if guild is None:
		await interaction.response.send_message("서버에서만 사용 가능한 명령어입니다.", ephemeral=True)
		return

	# Make the channel name unique-ish and mark it as temp
	chan_name = f"temp-{name}"
	category = None
	if isinstance(interaction.channel, discord.abc.GuildChannel):
		category = interaction.channel.category

	kwargs = {}
	if user_limit and user_limit > 0:
		kwargs['user_limit'] = user_limit

	try:
		creator = interaction.user
		overwrites = {creator: discord.PermissionOverwrite(manage_channels=True)}
		channel = await guild.create_voice_channel(chan_name, category=category, overwrites=overwrites, **kwargs)
		bot.temp_channels.add(channel.id)
		await interaction.response.send_message(f"생성됨: {channel.mention} (채널 편집 권한이 부여되었습니다)")
	except discord.Forbidden:
		await interaction.response.send_message("봇에게 채널 생성 권한이 없습니다.", ephemeral=True)
	except Exception as e:
		await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


if __name__ == '__main__':
	token = os.environ.get('DISCORD_TOKEN')
	if not token:
		print('DISCORD_TOKEN 환경변수가 필요합니다.')
	else:
		bot.run(token)


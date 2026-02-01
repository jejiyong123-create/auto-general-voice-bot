import os
import asyncio
from typing import Set

import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import json


INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.voice_states = True


class AutoVoiceBot(commands.Bot):
	def __init__(self):
		super().__init__(command_prefix='!', intents=INTENTS)
		self.temp_channels: Set[int] = set()
		# load per-guild config (lobby channel id, category id)
		self._config_path = os.path.join(os.path.dirname(__file__), 'config.json')
		self.config: dict = {}
		self._load_config()

	def _load_config(self):
		try:
			with open(self._config_path, 'r', encoding='utf-8') as f:
				self.config = json.load(f)
		except FileNotFoundError:
			self.config = {}
		except Exception as e:
			print(f"Failed to load config: {e}")

	def _save_config(self):
		try:
			with open(self._config_path, 'w', encoding='utf-8') as f:
				json.dump(self.config, f, ensure_ascii=False, indent=2)
		except Exception as e:
			print(f"Failed to save config: {e}")

	async def setup_hook(self) -> None:
		# If a test guild id is provided via env `DISCORD_GUILD`,
		# copy global commands to that guild and sync there for
		# immediate availability (guild sync is instant).
		guild_id = os.environ.get('DISCORD_GUILD')
		if guild_id:
			try:
				guild_obj = discord.Object(id=int(guild_id))
				self.tree.copy_global_to(guild=guild_obj)
				await self.tree.sync(guild=guild_obj)
				print(f"Synced commands to guild {guild_id}")
				return
			except Exception as e:
				print(f"Failed to sync to guild {guild_id}: {e}")

		# Fallback to global sync (can take up to 1 hour to appear).
		await self.tree.sync()
		print("Synced global commands (may take up to an hour)")

	async def on_ready(self):
		print(f"Logged in as {self.user} (id: {self.user.id})")

	async def on_voice_state_update(self, member, before, after):
		# Auto-create a temp voice channel when a user joins a configured lobby
		if after and member.guild:
			gid = str(member.guild.id)
			guild_cfg = self.config.get(gid, {})
			lobby_id = guild_cfg.get('lobby_id')
			# Handle creation first (user joined configured lobby channel)
			if lobby_id:
				try:
					if after.channel and int(lobby_id) == after.channel.id:
						# create a new voice channel for the member
						guild = member.guild
						chan_name = f"{member.display_name}-room"
						# If a target category is configured, use it; otherwise inherit from lobby
						category = None
						cat_id = guild_cfg.get('category_id')
						if cat_id:
							category = guild.get_channel(int(cat_id))
						if category is None:
							category = after.channel.category
						# grant the creator manage_channels so they can edit
						overwrites = {member: discord.PermissionOverwrite(manage_channels=True)}
						new_chan = await guild.create_voice_channel(chan_name, category=category, overwrites=overwrites)
						# track for auto-deletion
						self.temp_channels.add(new_chan.id)
						# move the user into their new channel
						try:
							await member.move_to(new_chan)
						except Exception:
							# ignore move failure (user may have disconnected)
							pass
						return
				except Exception as e:
					print(f"Failed to auto-create temp channel: {e}")

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


class CreateButtonView(ui.View):
	def __init__(self, *, timeout: float | None = None, user_limit: int = 0):
		super().__init__(timeout=timeout)
		self.user_limit = user_limit

	@ui.button(label="임시 음성채널 생성", style=discord.ButtonStyle.primary, custom_id="create_temp_voice")
	async def create_button(self, interaction: discord.Interaction, button: ui.Button):
		guild = interaction.guild
		member = interaction.user
		if guild is None:
			await interaction.response.send_message("서버에서만 사용 가능한 버튼입니다.", ephemeral=True)
			return

		chan_name = f"temp-{member.display_name}"
		category = None
		if isinstance(interaction.channel, discord.abc.GuildChannel):
			category = interaction.channel.category

		kwargs = {}
		if self.user_limit and self.user_limit > 0:
			kwargs['user_limit'] = self.user_limit

		try:
			overwrites = {member: discord.PermissionOverwrite(manage_channels=True)}
			new_chan = await guild.create_voice_channel(chan_name, category=category, overwrites=overwrites, **kwargs)
			bot.temp_channels.add(new_chan.id)
			try:
				await member.move_to(new_chan)
			except Exception:
				pass
			await interaction.response.send_message(f"생성됨: {new_chan.mention}", ephemeral=True)
		except discord.Forbidden:
			await interaction.response.send_message("봇에게 채널 생성 권한이 없습니다.", ephemeral=True)
		except Exception as e:
			await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


@bot.tree.command(name="post_create_button", description="이 채널에 임시채널 생성 버튼을 게시합니다 (관리 권한 필요)")
async def post_create_button(interaction: discord.Interaction):
	if not interaction.user.guild_permissions.manage_channels:
		await interaction.response.send_message("이 명령을 사용하려면 채널 관리 권한이 필요합니다.", ephemeral=True)
		return

	view = CreateButtonView()
	await interaction.response.send_message("버튼을 눌러 임시 음성채널을 생성하세요:", view=view)


@bot.tree.command(name="set_lobby", description="자동 임시채널을 생성할 로비 음성채널을 지정합니다 (관리 권한 필요)")
@app_commands.describe(channel="로비로 사용할 음성 채널")
async def set_lobby(interaction: discord.Interaction, channel: discord.VoiceChannel):
	if not interaction.user.guild_permissions.manage_channels:
		await interaction.response.send_message("이 명령을 사용하려면 채널 관리 권한이 필요합니다.", ephemeral=True)
		return

	gid = str(interaction.guild.id)
	bot.config.setdefault(gid, {})
	bot.config[gid]['lobby_id'] = channel.id
	bot._save_config()
	await interaction.response.send_message(f"로비 채널이 {channel.mention} 으로 설정되었습니다.", ephemeral=True)


@bot.tree.command(name="set_category", description="자동 생성 채널의 카테고리를 지정합니다 (관리 권한 필요)")
@app_commands.describe(category="생성될 채널을 넣을 카테고리")
async def set_category(interaction: discord.Interaction, category: discord.CategoryChannel):
	if not interaction.user.guild_permissions.manage_channels:
		await interaction.response.send_message("이 명령을 사용하려면 채널 관리 권한이 필요합니다.", ephemeral=True)
		return

	gid = str(interaction.guild.id)
	bot.config.setdefault(gid, {})
	bot.config[gid]['category_id'] = category.id
	bot._save_config()
	await interaction.response.send_message(f"생성 카테고리가 {category.name} 으로 설정되었습니다.", ephemeral=True)


# Korean-named aliases for convenience
@bot.tree.command(name="자동음성지정", description="자동 임시채널을 생성할 로비 음성채널을 지정합니다 (관리 권한 필요)")
@app_commands.describe(channel="로비로 사용할 음성 채널")
async def 자동음성지정(interaction: discord.Interaction, channel: discord.VoiceChannel):
	await set_lobby(interaction, channel)


@bot.tree.command(name="카테고리지정", description="자동 생성 채널의 카테고리를 지정합니다 (관리 권한 필요)")
@app_commands.describe(category="생성될 채널을 넣을 카테고리")
async def 카테고리지정(interaction: discord.Interaction, category: discord.CategoryChannel):
	await set_category(interaction, category)


@bot.tree.command(name="임시채널버튼", description="이 채널에 임시채널 생성 버튼을 게시합니다 (관리 권한 필요)")
async def 임시채널버튼(interaction: discord.Interaction):
	await post_create_button(interaction)


if __name__ == '__main__':
	token = os.environ.get('DISCORD_TOKEN')
	if not token:
		print('DISCORD_TOKEN 환경변수가 필요합니다.')
	else:
		bot.run(token)


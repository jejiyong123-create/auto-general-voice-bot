import os
import json
import asyncio
from dotenv import load_dotenv
from aiohttp import web
import discord
from discord.ext import commands
from typing import Dict

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

guild_settings: Dict[int, dict] = {}

def load_settings():
    global guild_settings
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            guild_settings = {int(k): v for k, v in json.load(f).items()}
    except FileNotFoundError:
        guild_settings = {}


def save_settings():
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(guild_settings, f, indent=2, ensure_ascii=False)


def get_guild_settings(guild_id: int) -> dict:
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {
            "creator_channel_id": None,
            "required_role_id": None,
            "category_id": None,
        }
    return guild_settings[guild_id]


async def start_health_server():
    async def handle(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("Health server started on port 8000")


@bot.event
async def on_ready():
    load_settings()
    try:
        await bot.tree.sync()
        print("슬래시 명령어 동기화 완료")
    except Exception as e:
        print(f"슬래시 명령어 동기화 오류: {e}")
    print(f"봇 로그인: {bot.user} (ID: {bot.user.id})")


@bot.command()
async def ping(ctx):
    await ctx.send('pong')


async def main():
    if not TOKEN:
        print("DISCORD_TOKEN is not set")
        return
    asyncio.create_task(start_health_server())
    await bot.start(TOKEN)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Shutting down')

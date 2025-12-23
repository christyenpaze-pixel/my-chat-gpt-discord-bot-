import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from openai import OpenAI

# =========================
# ENVIRONMENT VARIABLES
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or OPENAI_API_KEY")

# =========================
# OPENAI CLIENT
# =========================
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# DISCORD BOT SETUP
# =========================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Cooldown: 1 request every 10 seconds per user
cooldown = commands.CooldownMapping.from_cooldown(
    1, 10, commands.BucketType.user
)

# =========================
# BOT READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# =========================
# SLASH COMMAND
# =========================
@bot.tree.command(name="ask", description="Ask ChatGPT a question")
@app_commands.describe(question="What do you want to ask?")
async def ask(interaction: discord.Interaction, question: str):

    # Cooldown check
    bucket = cooldown.get_bucket(interaction)
    retry_after = bucket.update_rate_limit()

    if retry_after:
        await interaction.response.send_message(
            f"⏳ Slow down! Try again in `{retry_after:.1f}` seconds.",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        async with interaction.channel.typing():
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful Discord assistant."},
                    {"role": "user", "content": question}
                ],
                max_tokens=500
            )

        answer = response.choices[0].message.content

        # Discord message limit safety
        if len(answer) > 1900:
            answer = answer[:1900] + "..."

        await interaction.followup.send(answer)

    except Exception as e:
        print("OpenAI error:", e)
        await interaction.followup.send(
            "❌ Error talking to OpenAI. Please try again later."
        )

# =========================
# GLOBAL ERROR HANDLER
# =========================
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Unhandled error in {event}", args, kwargs)

# =========================
# START BOT
# =========================
bot.run(DISCORD_TOKEN)

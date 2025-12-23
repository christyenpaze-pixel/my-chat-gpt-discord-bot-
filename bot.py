import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from openai import OpenAI

# =========================
# ENV VARIABLES
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Missing environment variables")

# =========================
# OPENAI CLIENT
# =========================
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Cooldown: 1 request / 10s per user
cooldown = commands.CooldownMapping.from_cooldown(
    1, 10, commands.BucketType.user
)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# =========================
# OPENAI CALL (THREAD SAFE)
# =========================
def ask_openai(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful Discord assistant."},
            {"role": "user", "content": question}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

# =========================
# SLASH COMMAND
# =========================
@bot.tree.command(name="ask", description="Ask ChatGPT a question")
@app_commands.describe(question="What do you want to ask?")
async def ask(interaction: discord.Interaction, question: str):

    bucket = cooldown.get_bucket(interaction)
    retry_after = bucket.update_rate_limit()

    if retry_after:
        await interaction.response.send_message(
            f"⏳ Slow down! Try again in `{retry_after:.1f}` seconds.",
            ephemeral=True
        )
        return

    # Respond immediately (prevents timeout)
    await interaction.response.defer(thinking=True)

    try:
        # Run OpenAI call in background thread
        answer = await asyncio.to_thread(ask_openai, question)

        if len(answer) > 1900:
            answer = answer[:1900] + "..."

        await interaction.followup.send(answer)

    except Exception as e:
        print("Error:", e)
        await interaction.followup.send(
            "❌ Error talking to OpenAI. Please try again later."
        )

# =========================
# GLOBAL ERROR SAFETY
# =========================
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Unhandled error in {event}")

# =========================
# START BOT
# =========================
bot.run(DISCORD_TOKEN)

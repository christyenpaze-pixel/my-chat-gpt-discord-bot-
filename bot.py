import time
import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
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

# =========================
# SIMPLE COOLDOWN (SLASH SAFE)
# =========================
COOLDOWN_SECONDS = 10
USER_COOLDOWNS: dict[int, float] = {}

# =========================
# ROTATING CUSTOM STATUSES
# (NOT GAME ACTIVITY)
# =========================
STATUSES = [
    "🩸 bleed-style AI",
    "💬 /ask",
    "⚡ chatcelp",
]

@tasks.loop(seconds=15)
async def rotate_status():
    try:
        status = STATUSES[int(time.time()) % len(STATUSES)]
        await bot.change_presence(
            activity=discord.CustomActivity(name=status)
        )
    except Exception as e:
        print("Status error:", e)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    rotate_status.start()
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
# SLASH COMMAND (FIXED)
# =========================
@bot.tree.command(name="ask", description="Ask ChatGPT a question")
@app_commands.describe(question="What do you want to ask?")
async def ask(interaction: discord.Interaction, question: str):

    # ✅ ALWAYS ACK FIRST
    await interaction.response.defer(thinking=True)

    try:
        user_id = interaction.user.id
        now = time.time()

        last_used = USER_COOLDOWNS.get(user_id, 0)
        if now - last_used < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - (now - last_used))
            await interaction.followup.send(
                f"⏳ Slow down! Try again in **{remaining}s**.",
                ephemeral=True
            )
            return

        USER_COOLDOWNS[user_id] = now

        # Run OpenAI safely off the event loop
        answer = await asyncio.to_thread(ask_openai, question)

        if not answer:
            raise RuntimeError("Empty OpenAI response")

        if len(answer) > 1900:
            answer = answer[:1900] + "..."

        await interaction.followup.send(answer)

    except Exception as e:
        print("Ask command error:", e)
        await interaction.followup.send(
            "❌ Error talking to OpenAI. Please try again later.",
            ephemeral=True
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

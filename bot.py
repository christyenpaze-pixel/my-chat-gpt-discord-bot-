import time
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

# =========================
# SLASH-SAFE COOLDOWN
# =========================
USER_COOLDOWNS = {}
COOLDOWN_SECONDS = 10

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"Logged in as {bot.user}")
    except Exception as e:
        print("Command sync failed:", e)

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

    try:
        user_id = interaction.user.id
        now = time.time()

        last_used = USER_COOLDOWNS.get(user_id, 0)
        if now - last_used < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - (now - last_used))
            await interaction.response.send_message(
                f"⏳ Slow down! Try again in **{remaining}s**.",
                ephemeral=True
            )
            return

        USER_COOLDOWNS[user_id] = now

        # Prevent "application did not respond"
        await interaction.response.defer(thinking=True)

        # Run OpenAI call safely
        answer = await asyncio.to_thread(ask_openai, question)

        if not answer:
            raise RuntimeError("Empty response from OpenAI")

        if len(answer) > 1900:
            answer = answer[:1900] + "..."

        await interaction.followup.send(answer)

    except Exception as e:
        print("Ask command error:", e)

        # If defer already happened, use followup
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Error talking to OpenAI. Please try again later.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
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


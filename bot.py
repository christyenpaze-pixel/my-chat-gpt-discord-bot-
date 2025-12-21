import discord
from discord.ext import commands
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def ask(ctx, *, question):
    await ctx.typing()
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful Discord bot."},
                {"role": "user", "content": question}
            ],
            max_tokens=400
        )
        await ctx.reply(response.choices[0].message.content)
    except Exception as e:
        await ctx.reply("❌ Error talking to OpenAI.")
        print(e)

bot.run(os.getenv("DISCORD_TOKEN"))

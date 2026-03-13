import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime

# -------------------
# Flask keep-alive
# -------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# -------------------
# Bot Setup
# -------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
start_time = datetime.utcnow()

# -------------------
# Guild ID for instant sync
# -------------------
GUILD_ID = 123456789012345678  # <- Replace with your server ID

# -------------------
# Settings & warnings
# -------------------
SETTINGS_FILE = "settings.json"
WARNINGS_FILE = "warnings.json"

settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {}
warnings_data = json.load(open(WARNINGS_FILE)) if os.path.exists(WARNINGS_FILE) else {}

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def save_warnings():
    with open(WARNINGS_FILE, "w") as f:
        json.dump(warnings_data, f, indent=4)

# -------------------
# Curse words
# -------------------
curse_words = ["fuck","shit","bitch","asshole","dick","cunt","pussy","whore"]

# -------------------
# Tickets
# -------------------
tickets = {}

# -------------------
# Bot Events
# -------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Curse filter
    if any(word in message.content.lower() for word in curse_words):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, that word is not allowed!", delete_after=5)
        except:
            pass
    # Chat logging
    guild_id = str(message.guild.id)
    if guild_id in settings and "chatlog_channel" in settings[guild_id]:
        log_channel = bot.get_channel(settings[guild_id]["chatlog_channel"])
        if log_channel:
            await log_channel.send(f"**{message.author}**: {message.content}")
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    guild_id = str(after.guild.id)
    if guild_id in settings and "chatlog_channel" in settings[guild_id]:
        ch = bot.get_channel(settings[guild_id]["chatlog_channel"])
        if ch:
            await ch.send(f"**{after.author}** edited a message:\nBefore: {before.content}\nAfter: {after.content}")

@bot.event
async def on_message_delete(message):
    guild_id = str(message.guild.id)
    if guild_id in settings and "chatlog_channel" in settings[guild_id]:
        ch = bot.get_channel(settings[guild_id]["chatlog_channel"])
        if ch:
            await ch.send(f"**{message.author}** deleted a message:\n{message.content}")

# -------------------
# /set commands with inline pickers
# -------------------
def register_channel_set_command(name, key, description):
    @tree.command(name=name, description=description)
    @app_commands.describe(channel="Select the channel")
    async def cmd(interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild.id)
        if guild_id not in settings:
            settings[guild_id] = {}
        settings[guild_id][key] = channel.id
        save_settings()
        await interaction.followup.send(f"{name} channel set to {channel.mention}", ephemeral=True)

register_channel_set_command("setwelcome", "welcome_channel", "Set welcome channel")
register_channel_set_command("setgoodbye", "goodbye_channel", "Set goodbye channel")
register_channel_set_command("setannouncement", "announcement_channel", "Set announcement channel")
register_channel_set_command("setchatlog", "chatlog_channel", "Set chat log channel")

# -------------------
# Moderation commands
# -------------------
@tree.command(name="ban", description="Ban a user")
@app_commands.describe(user="User to ban", reason="Reason")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    await interaction.response.defer(ephemeral=True)
    await user.ban(reason=reason)
    await interaction.followup.send(f"{user.mention} banned.", ephemeral=True)

@tree.command(name="kick", description="Kick a user")
@app_commands.describe(user="User to kick", reason="Reason")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    await interaction.response.defer(ephemeral=True)
    await user.kick(reason=reason)
    await interaction.followup.send(f"{user.mention} kicked.", ephemeral=True)

@tree.command(name="mute", description="Mute a user")
@app_commands.describe(user="User to mute")
async def mute(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role:
        await user.add_roles(role)
        await interaction.followup.send(f"{user.mention} muted.", ephemeral=True)
    else:
        await interaction.followup.send("Muted role not found.", ephemeral=True)

@tree.command(name="unmute", description="Unmute a user")
@app_commands.describe(user="User to unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role:
        await user.remove_roles(role)
        await interaction.followup.send(f"{user.mention} unmuted.", ephemeral=True)
    else:
        await interaction.followup.send("Muted role not found.", ephemeral=True)

@tree.command(name="warn", description="Warn a user")
@app_commands.describe(user="User", reason="Reason")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
    await interaction.response.defer(ephemeral=True)
    uid = str(user.id)
    if uid not in warnings_data:
        warnings_data[uid] = []
    warnings_data[uid].append(reason)
    save_warnings()
    await interaction.followup.send(f"{user.mention} warned for: {reason}", ephemeral=True)

@tree.command(name="warnings", description="Check warnings")
@app_commands.describe(user="User")
async def warnings(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    uid = str(user.id)
    if uid in warnings_data and warnings_data[uid]:
        await interaction.followup.send(f"{user.mention} warnings:\n" + "\n".join(f"{i+1}. {w}" for i,w in enumerate(warnings_data[uid])), ephemeral=True)
    else:
        await interaction.followup.send(f"{user.mention} has no warnings.", ephemeral=True)

@tree.command(name="clear", description="Clear messages")
@app_commands.describe(amount="Number of messages")
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

# -------------------
# Tickets system
# -------------------
@tree.command(name="ticket", description="Open a support ticket")
async def ticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
    tickets[interaction.user.id] = channel.id
    await channel.send(f"{interaction.user.mention}, your ticket is ready!")
    await interaction.followup.send("Ticket created!", ephemeral=True)

@tree.command(name="close", description="Close this ticket")
async def close(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.channel.id in tickets.values():
        await interaction.channel.delete()
    else:
        await interaction.followup.send("This is not a ticket channel.", ephemeral=True)

# -------------------
# Announcements
# -------------------
@tree.command(name="announcement", description="Send announcement")
@app_commands.describe(title="Title", message="Message")
async def announcement(interaction: discord.Interaction, title: str, message: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild.id)
    if guild_id in settings and "announcement_channel" in settings[guild_id]:
        ch = bot.get_channel(settings[guild_id]["announcement_channel"])
        if ch:
            embed = discord.Embed(title=title, description=message, color=discord.Color.blue())
            await ch.send(embed=embed)
            await interaction.followup.send("Announcement sent!", ephemeral=True)
            return
    await interaction.followup.send("Announcement channel not set.", ephemeral=True)

# -------------------
# Welcome/Goodbye toggles
# -------------------
@tree.command(name="welcome", description="Turn welcome messages on/off")
@app_commands.describe(option="on/off")
async def welcome(interaction: discord.Interaction, option: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]["welcome_enabled"] = option.lower() == "on"
    save_settings()
    await interaction.followup.send(f"Welcome messages turned {option.lower()}.", ephemeral=True)

@tree.command(name="goodbye", description="Turn goodbye messages on/off")
@app_commands.describe(option="on/off")
async def goodbye(interaction: discord.Interaction, option: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild.id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]["goodbye_enabled"] = option.lower() == "on"
    save_settings()
    await interaction.followup.send(f"Goodbye messages turned {option.lower()}.", ephemeral=True)

# -------------------
# Hosting/Business commands
# -------------------
@tree.command(name="order", description="Place hosting order")
async def order(interaction: discord.Interaction):
    await interaction.response.send_message("Visit https://yourpanel.com to place an order!", ephemeral=True)

@tree.command(name="apply", description="Apply for staff/support")
async def apply(interaction: discord.Interaction):
    await interaction.response.send_message("Fill out the application form: https://yourform.com", ephemeral=True)

@tree.command(name="plans", description="View hosting plans")
async def plans(interaction: discord.Interaction):
    await interaction.response.send_message("Hosting Plans:\nBasic - $5\nStandard - $10\nPremium - $20", ephemeral=True)

@tree.command(name="status", description="Check server status")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message("All servers operational ✅", ephemeral=True)

@tree.command(name="panel", description="Access hosting control panel")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("Control Panel: https://yourpanel.com", ephemeral=True)

@tree.command(name="website", description="Visit website")
async def website(interaction: discord.Interaction):
    await interaction.response.send_message("Website: https://yourwebsite.com", ephemeral=True)

@tree.command(name="support", description="Open support ticket")
async def support(interaction: discord.Interaction):
    await interaction.response.send_message("Support: https://support.yourwebsite.com", ephemeral=True)

# -------------------
# Run bot
# -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(DISCORD_TOKEN)

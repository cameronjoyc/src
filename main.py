import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import re  # Regular expression for parsing time
import random  # For coinflip and games
from discord.ui import Button, View

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="-", intents=intents, help_command=None)

# A dictionary to store temporary bans and timeouts
temp_bans = {}
timeouts = {}
warns = {}
anti_nuke_admins = []  # List to store anti-nuke admins

# Helper function to log actions
async def log_action(ctx, action, member, reason):
    log_channel = discord.utils.get(ctx.guild.text_channels, name="protector-logs")
    if log_channel:
        embed = discord.Embed(title="Moderation Action", color=discord.Color.red())
        embed.add_field(name="Action", value=action, inline=False)
        embed.add_field(name="User   ", value=member.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Actioned by: {ctx.author.display_name}")
        await log_channel.send(embed=embed)

# 1. Setup Command
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    log_channel = await ctx.guild.create_text_channel("protector-logs")
    await ctx.send(f"Log channel created: {log_channel.mention}")

    jail_channel = await ctx.guild.create_text_channel("jail")
    await ctx.send(f"Jail channel created: {jail_channel.mention}")

    jail_role = await ctx.guild.create_role(name="Jailed", color=discord.Color.from_rgb(255, 0, 0), permissions=discord.Permissions.none())
    
    for channel in ctx.guild.channels:
        await channel.set_permissions(jail_role, send_messages=False, read_messages=False)
    
    await jail_channel.set_permissions(jail_role, send_messages=True, read_messages=True)
    await jail_channel.set_permissions(ctx.guild.default_role, send_messages=False, read_messages=False)

    await ctx.send(f"Jail role created and permissions set for {jail_role.mention}.")
    await log_action(ctx, "Setup", ctx.guild, "Set up protector logs, jail channel, and jail role")

# 2. Jail Command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def jail(ctx, member: discord.Member, *, reason=None):
    jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    if not jail_role:
        jail_role = await ctx.guild.create_role(name="Jailed", color=discord.Color.from_rgb(255, 0, 0), permissions=discord.Permissions.none())
        for channel in ctx.guild.channels:
            await channel.set_permissions(jail_role, send_messages=False, read_messages=False)
        jail_channel = discord.utils.get(ctx.guild.text_channels, name="jail")
        if jail_channel:
            await jail_channel.set_permissions(jail_role, send_messages=True, read_messages=True)

    await member.add_roles(jail_role)
    reason_message = reason if reason else "No reason provided"
    await ctx.send(f"{member.mention} has been jailed for: {reason_message}")

    try:
        await member.send(f"You have been jailed in **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Jailed {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Jail", member, reason_message)

# 3. Unjail Command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unjail(ctx, member: discord.Member):
    jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    if jail_role in member.roles:
        await member.remove_roles(jail_role)
        await ctx.send(f"{member.mention} has been unjailed.")
        
        try:
            await member.send(f"You have been unjailed in **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
        except discord.Forbidden:
            await ctx.send(f"Unjailed {member.mention}, but couldn't PM them 👍")
        
        await log_action(ctx, "Unjail", member, " No reason provided")
    else:
        await ctx.send(f"{member.mention} is not jailed.")

# 4. Kick Command
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    reason_message = reason if reason else "No reason provided"
    await member.kick(reason=reason_message)
    await ctx.send(f"{member.mention} has been kicked for: {reason_message}")

    try:
        await member.send(f"You have been kicked from **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Kicked {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Kick", member, reason_message)

# 5. Ban Command
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    reason_message = reason if reason else "No reason provided"
    await member.ban(reason=reason_message)
    await ctx.send(f"{member.mention} has been banned for: {reason_message}")

    try:
        await member.send(f"You have been banned from **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Banned {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Ban", member, reason_message)

# 6. Temporary Ban Command
@bot.command()
@commands.has_permissions(ban_members=True)
async def tempban(ctx, member: discord.Member, duration: str, *, reason=None):
    reason_message = reason if reason else "No reason provided"
    await member.ban(reason=reason_message)
    await ctx.send(f"{member.mention} has been temporarily banned for: {reason_message}. Duration: {duration}")

    try:
        await member.send(f"You have been temporarily banned from **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Temporarily banned {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Temporary Ban", member, reason_message)

    duration_seconds = parse_duration(duration)
    await asyncio.sleep(duration_seconds)
    await ctx.guild.unban(member)
    await ctx.send(f"{member.mention} has been unbanned after the temporary ban.")

# Function to parse duration strings (e.g., "1h", "30m", "15s")
def parse_duration(duration: str) -> int:
    match = re.match(r'(\d+)([smh])', duration)
    if match:
        value, unit = match.groups()
        value = int(value)
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
    return 0  # Default to 0 if parsing fails

# 7. Warn Command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    reason_message = reason if reason else "No reason provided"
    if member.id not in warns:
        warns[member.id] = []
    warns[member.id].append(reason_message)
    await ctx.send(f"{member.mention} has been warned for: {reason_message}")

    try:
        await member.send(f"You have been warned in **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Warned {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Warn", member, reason_message)

# 8. Mute Command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, read_messages=True)

    await member.add_roles(mute_role)
    reason_message = reason if reason else "No reason provided"
    await ctx.send(f"{member.mention} has been muted for: {reason_message}")

    try:
        await member.send(f"You have been muted in **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Muted {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Mute", member, reason_message)

# 9. Timeout Command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def timeout(ctx, member: discord.Member, duration: str, *, reason=None):
    timeout_role = discord.utils.get(ctx.guild.roles, name="Timeout")
    if not timeout_role:
        timeout_role = await ctx.guild.create_role(name="Timeout", permissions=discord.Permissions(send_messages=False, speak=False))
        for channel in ctx.guild.channels:
            await channel.set_permissions(timeout_role, send_messages=False, read_messages=True)

    await member.add_roles(timeout_role)
    reason_message = reason if reason else "No reason provided"
    await ctx.send(f"{member.mention} has been timed out for: {reason_message}. Duration: {duration}")

    try:
        await member.send(f"You have been timed out in **{ctx.guild.name}** by moderator **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send(f"Timed out {member.mention}, but couldn't PM them 👍")

    await log_action(ctx, "Timeout", member, reason_message)

    duration_seconds = parse_duration(duration)
    await asyncio.sleep(duration_seconds)
    await member.remove_roles(timeout_role)
    await ctx.send(f"{member.mention} has been removed from timeout after the specified duration.")

# 10. Lockdown Command
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lockdown(ctx):
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("All text channels have been locked down.")

# 11. Unlockdown Command
@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlockdown(ctx):
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("All text channels have been unlocked.")

# 12. Clear Command
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
    await ctx.send(f"Cleared {amount} messages.", delete_after=5)

# 13. Userinfo Command
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"User  Info for {member}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
    embed.add_field(name="Roles", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]))
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

# 14. Serverinfo Command
@bot.command()
async def serverinfo(ctx):
    embed = discord.Embed(title=f"Server Info for {ctx.guild.name}", color=discord.Color.green())
    embed.add_field(name="ID", value=ctx.guild.id)
    embed.add_field(name="Owner", value=ctx.guild.owner)
    embed.add_field(name="Member Count", value=ctx.guild.member_count)
    embed.add_field(name="Created At", value=ctx.guild.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    embed.set_thumbnail(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)

# 15. Invite Command
@bot.command()
async def invite(ctx):
    if ctx.guild.vanity_url_code:
        vanity_invite = f"https://discord.gg/{ctx.guild.vanity_url_code}"
        await ctx.send(f"Here is your vanity invite link: {vanity_invite}")
    else:
        invite_link = await ctx.channel.create_invite(max_age=300)  # Invite link valid for 5 minutes
        await ctx.send(f"Here is your invite link: {invite_link}")

# 16. Setprefix Command
@bot.command()
@commands.has_permissions(administrator=True)
async def setprefix(ctx, prefix: str):
    bot.command_prefix = prefix
    await ctx.send(f"Command prefix has been changed to: {prefix}")

# 17. Poll Command
@bot.command()
async def poll(ctx, *, question):
    poll_message = await ctx.send(f"Poll: {question}\nReact with 👍 for Yes, 👎 for No.")
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")

# 18. Suggest Command
@bot.command()
async def suggest(ctx, *, suggestion):
    suggestion_channel = discord.utils.get(ctx.guild.text_channels, name="suggestions")
    if suggestion_channel:
        await suggestion_channel.send(f"Suggestion from {ctx.author.mention}: {suggestion}")
        await ctx.send("Your suggestion has been submitted!")
    else:
        await ctx.send("Suggestion channel not found.")

# 19. Slowmode Command
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, duration: int):
    await ctx.channel.edit(slowmode_delay=duration)
    await ctx.send(f"Slowmode has been set to {duration} seconds.")

# 20. Softban Command
@bot.command()
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.guild.unban(member)
    await ctx.send(f"{member.mention} has been softbanned for: {reason}")

# 21. Role Command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"Removed {role.name} from {member.mention}.")
    else:
        await member.add_roles(role)
        await ctx.send(f"Added {role.name} to {member.mention}.")

# 22. Help Command with Pagination
@bot.command()
async def help(ctx):
    moderation_commands = (
        "**Moderation Commands:**\n"
        "`-setup`: Sets up the bot with necessary channels and roles.\n"
        "`-jail @member [reason]`: Jails a member with an optional reason.\n"
        "`-unjail @member`: Releases a jailed member.\n"
        "`-kick @member [reason]`: Kicks a member with an optional reason.\n"
        "`-ban @member [reason]`: Bans a member with an optional reason.\n"
        "`-tempban @member [duration] [reason]`: Temporarily bans a member for a specified duration.\n"
        "`-warn @member [reason]`: Issues a warning to a member with an optional reason.\n"
        "`-mute @member [reason]`: Mutes a member with an optional reason.\n"
        "`-timeout @member [duration] [reason]`: Times out a member for a specified duration.\n"
        "`-lockdown`: Locks down all text channels.\n"
        "`-unlockdown`: Unlocks all text channels.\n"
        "`-clear [amount]`: Deletes a specified number of messages.\n"
        "`-userinfo [@member]`: Displays information about a user.\n"
        "`-serverinfo`: Displays information about the server.\n"
        "`-invite`: Provides an invite link for the bot.\n"
        "`-setprefix [prefix]`: Changes the command prefix for the bot.\n"
        "`-poll [question]`: Creates a poll with the specified question.\n"
        "`-suggest [suggestion]`: Submits a suggestion.\n"
        "`-slowmode [duration]`: Sets slowmode for the current channel.\n"
        "`-softban @member`: Soft bans a member (bans and immediately unbans).\n"
        "`-role @member [role]`: Toggles a role for a member.\n"
    )

    fun_commands = (
        "**Fun Commands:**\n"
        "`-coinflip`: Flips a coin and shows either Heads or Tails.\n"
        "`-ttt @member`: Starts a Tic-Tac-Toe game with the mentioned member.\n"
        "`-roll`: Rolls a six-sided die.\n"
        "`-meme`: Sends a random meme from a predefined list.\n"
        "`-joke`: Tells a random joke.\n"
        "`-quote`: Sends a random inspirational quote.\n"
        "`-rps @member`: Plays Rock-Paper-Scissors against another member.\n"
    )

    view = View()
    moderation_button = Button(label="moderation", style=discord.ButtonStyle.secondary)
    fun_button = Button(label="Fun", style=discord.ButtonStyle.secondary)

    async def moderation_callback(interaction):
        await interaction.response.edit_message(content=moderation_commands, view=view)

    async def fun_callback(interaction):
        await interaction.response.edit_message(content=fun_commands, view=view)

    moderation_button.callback = moderation_callback
    fun_button.callback = fun_callback

    view.add_item(moderation_button)
    view.add_item(fun_button)

    await ctx.send(content=moderation_commands, view=view)

# 23. Coinflip Command
@bot.command 
async def coinflip(ctx):
    result = "Heads" if random.choice([True, False]) else "Tails"
    await ctx.send(f"The coin landed on: {result}")

# 24. Tic-Tac-Toe Command
@bot.command()
async def ttt(ctx, member: discord.Member):
    board = [" " for _ in range(9)]
    current_player = ctx.author
    game_over = False

    def draw_board():
        return (
            f"{board[0]} | {board[1]} | {board[2]}\n"
            "---------\n"
            f"{board[3]} | {board[4]} | {board[5]}\n"
            "---------\n"
            f"{board[6]} | {board[7]} | {board[8]}"
        )

    await ctx.send(f"{current_player.mention} vs {member.mention}\n" + draw_board())

    while not game_over:
        def check(m):
            return m.author in [ctx.author, member] and m.channel == ctx.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Game timed out!")
            return

        position = int(msg.content) - 1
        if 0 <= position < 9 and board[position] == " ":
            board[position] = "X" if current_player == ctx.author else "O"
            await ctx.send(draw_board())
            if check_winner(board):
                await ctx.send(f"{current_player.mention} wins!")
                game_over = True
            elif " " not in board:
                await ctx.send("It's a draw!")
                game_over = True
            current_player = member if current_player == ctx.author else ctx.author
        else:
            await ctx.send("Invalid move! Try again.")

def check_winner(board):
    winning_combinations = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Horizontal
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Vertical
        (0, 4, 8), (2, 4, 6)               # Diagonal
    ]
    for a, b, c in winning_combinations:
        if board[a] == board[b] == board[c] != " ":
            return True
    return False

# 25. Roll Command
@bot.command()
async def roll(ctx):
    die_roll = random.randint(1, 6)
    await ctx.send(f"You rolled a {die_roll}!")

# 26. Meme Command
@bot.command()
async def meme(ctx):
    memes = [
        "https://i.imgur.com/1.jpg",
        "https://i.imgur.com/2.jpg",
        "https://i.imgur.com/3.jpg",
        "https://i.imgur.com/4.jpg",
        "https://i.imgur.com/5.jpg"
    ]
    await ctx.send(random.choice(memes))

# 27. Joke Command
@bot.command()
async def joke(ctx):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "Why don't skeletons fight each other? They don't have the guts."
    ]
    await ctx.send(random.choice(jokes))

# 28. Quote Command
@bot.command()
async def quote(ctx):
    quotes = [
        "The best way to predict the future is to invent it. - Alan Kay",
        "Life is 10% what happens to us and 90% how we react to it. - Charles R. Swindoll",
        "The only way to do great work is to love what you do. - Steve Jobs"
    ]
    await ctx.send(random.choice(quotes))

# 29. Rock-Paper-Scissors Command
@bot.command()
async def rps(ctx, member: discord.Member):
    options = ["rock", "paper", "scissors"]
    await ctx.send(f"{ctx.author.mention} vs {member.mention} - Choose your option: rock, paper, or scissors!")

    def check(m):
        return m.author in [ctx.author, member] and m.channel == ctx.channel and m.content.lower() in options

    try:
        user_choice = await bot.wait_for('message', check=check, timeout=30)
        member_choice = random.choice(options)
        await ctx.send(f"{member.mention} chose {member_choice}!")

        if user_choice.content.lower() == member_choice:
            await ctx.send("It's a tie!")
        elif (user_choice.content.lower() == "rock" and member_choice == "scissors") or \
             (user_choice.content.lower() == "paper" and member_choice == "rock") or \
             (user_choice.content.lower() == "scissors" and member_choice == "paper"):
            await ctx.send(f"{ctx.author.mention} wins!")
        else:
            await ctx.send(f"{member.mention} wins!")
    except asyncio.TimeoutError:
        await ctx.send("You took too long to respond!")

# 30. Anti-Nuke Admin Whitelist Command
@bot.command()
@commands.has_permissions(administrator=True)
async def anwhitelist(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id in anti_nuke_admins:
        anti_nuke_admins.remove(member.id)
        await ctx.send(f"{member.mention} is no longer an anti-nuke admin.")
    else:
        anti_nuke_admins.append(member.id)
        await ctx.send(f"{member.mention} has been whitelisted as an anti-nuke admin.")

# 31. List Anti-Nuke Admins Command
@bot.command()
async def anadmins(ctx):
    if not anti_nuke_admins:
        await ctx.send("No anti-nuke admins have been whitelisted.")
        return

    admin_mentions = [ctx.guild.get_member(admin_id).mention for admin_id in anti_nuke_admins if ctx.guild.get_member(admin_id)]
    await ctx.send("Anti-Nuke Admins:\n" + "\n".join(admin_mentions))

# 32. Hard Ban Command
@bot.command()
@commands.has_permissions(ban_members=True)
async def hardban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} has been hard banned.")

# Unban Command
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, member: discord.User):
    banned_users = await ctx.guild.bans()
    if member not in [b.user for b in banned_users]:
        await ctx.send(f"{member.mention} is not hard-banned.")
        return

    if ctx.author.id not in anti_nuke_admins:
        await ctx.send("You do not have permission to unban this user.")
        return

    await ctx.guild.unban(member)
    await ctx.send(f"{member.mention} has been unbanned.")

# Run the bot with your token
bot.run('MTMwNDc2MDQyNTcwMjg4NzQ5NQ.GXVig_.BNZMjBRvizIZShQo3lx1UeDE3zzVWGYvWfeBbw')  # Replace with your actual bot token

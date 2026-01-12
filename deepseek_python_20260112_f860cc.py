import discord
from discord.ext import commands
import re
from datetime import datetime
import json
import os

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
OWNER_ID = YOUR_OWNER_ID_HERE  # Replace with your Discord ID
TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Replace with your bot token
DATA_FILE = 'whitelist_data.json'  # File to store whitelist data

# Link patterns
LINK_PATTERNS = [
    r'(https?://)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+',  # Discord invites
    r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+',  # YouTube links
    r'(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/\S*)?'  # General URLs
]

# Load whitelist data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"whitelisted_users": [], "whitelisted_roles": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize data
bot.whitelist_data = load_data()

def is_allowed(user):
    """Check if user is allowed to post links"""
    # Owner can always post links
    if user.id == OWNER_ID:
        return True
    
    # Check whitelisted users
    if user.id in bot.whitelist_data["whitelisted_users"]:
        return True
    
    # Check whitelisted roles
    if hasattr(user, 'roles'):
        user_roles = [role.id for role in user.roles]
        for role_id in bot.whitelist_data["whitelisted_roles"]:
            if role_id in user_roles:
                return True
    
    return False

def contains_links(text):
    """Check if text contains any links"""
    for pattern in LINK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot Owner ID: {OWNER_ID}')
    print(f'Whitelisted Users: {len(bot.whitelist_data["whitelisted_users"])}')
    print(f'Whitelisted Roles: {len(bot.whitelist_data["whitelisted_roles"])}')
    await bot.change_presence(activity=discord.Game(name="!help - Owner/Whitelist Only"))

@bot.event
async def on_message(message):
    # Don't process bot's own messages
    if message.author.bot:
        return
    
    # Check if user is allowed to post links
    if is_allowed(message.author):
        await bot.process_commands(message)
        return
    
    # Check for links in message from non-allowed users
    if contains_links(message.content):
        try:
            # Save message content for log
            original_content = message.content
            
            # Delete the message
            await message.delete()
            
            # Create delete log embed
            embed = discord.Embed(
                title="🔗 Link Deleted",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="👤 User", value=f"{message.author.mention}\n`{message.author.name}`\nID: `{message.author.id}`", inline=False)
            
            # Show truncated message content
            if original_content:
                content_preview = original_content[:500] + "..." if len(original_content) > 500 else original_content
                embed.add_field(name="📝 Message Content", value=f"```{content_preview}```", inline=False)
            
            # Extract detected links
            detected_links = []
            for pattern in LINK_PATTERNS:
                matches = re.findall(pattern, original_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        link = ''.join(match)
                        if link and link not in detected_links:
                            detected_links.append(link)
                    elif match and match not in detected_links:
                        detected_links.append(match)
            
            if detected_links:
                embed.add_field(name="🔗 Detected Links", value="\n".join([f"• `{link}`" for link in detected_links[:3]]), inline=False)
            
            embed.add_field(name="📌 Channel", value=f"{message.channel.mention}", inline=True)
            embed.add_field(name="🛡️ Action", value="Auto-Deleted", inline=True)
            embed.add_field(name="🔒 Status", value="Not Whitelisted", inline=True)
            
            # Try to send log to channel where message was deleted
            try:
                log_message = await message.channel.send(embed=embed)
                # Delete log after 30 seconds
                await log_message.delete(delay=30)
            except:
                pass
            
            # Send warning to user (deleted after 10 seconds)
            try:
                warning = await message.channel.send(
                    f"{message.author.mention}, Only whitelisted users can post links! Use `!request` to ask for permission.",
                    delete_after=10
                )
            except:
                pass
            
            # DM the user about the deletion
            try:
                dm_embed = discord.Embed(
                    title="⚠️ Link Removed",
                    description=f"Your message in **{message.guild.name}** was deleted because it contained links.",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
                dm_embed.add_field(name="Reason", value="You are not whitelisted to post links", inline=True)
                if original_content:
                    content_preview = original_content[:300] + "..." if len(original_content) > 300 else original_content
                    dm_embed.add_field(name="Your Message", value=f"```{content_preview}```", inline=False)
                dm_embed.add_field(name="Request Access", value="Use `!request` in the server to ask for whitelist permission", inline=False)
                dm_embed.set_footer(text="Only whitelisted users can post links")
                await message.author.send(embed=dm_embed)
            except:
                pass  # User has DMs closed
            
        except discord.NotFound:
            pass  # Message already deleted
        except Exception as e:
            print(f"Error: {e}")
        
        return
    
    # Process commands for all users
    await bot.process_commands(message)

# OWNER COMMANDS

@bot.command(name='wladd')
@commands.is_owner()
async def whitelist_add(ctx, target=None):
    """Add user or role to whitelist (Owner Only)"""
    if not target:
        await ctx.send("❌ Please mention a user or role: `!wladd @user` or `!wladd @role`", delete_after=10)
        return
    
    # Try to parse as user
    try:
        user = await commands.UserConverter().convert(ctx, target)
        if user.id not in bot.whitelist_data["whitelisted_users"]:
            bot.whitelist_data["whitelisted_users"].append(user.id)
            save_data(bot.whitelist_data)
            
            embed = discord.Embed(
                title="✅ User Whitelisted",
                description=f"{user.mention} can now post links!",
                color=discord.Color.green()
            )
            embed.add_field(name="User", value=f"{user.name}#{user.discriminator}", inline=True)
            embed.add_field(name="ID", value=f"`{user.id}`", inline=True)
            embed.set_footer(text=f"Added by {ctx.author.name}")
            
            await ctx.send(embed=embed)
            
            # Notify the user
            try:
                notify_embed = discord.Embed(
                    title="🎉 Whitelist Access Granted",
                    description=f"You have been whitelisted to post links in **{ctx.guild.name}**!",
                    color=discord.Color.green()
                )
                notify_embed.add_field(name="Granted By", value=ctx.author.mention, inline=True)
                notify_embed.set_footer(text="You can now post YouTube and Discord links")
                await user.send(embed=notify_embed)
            except:
                pass
        else:
            await ctx.send(f"⚠️ {user.mention} is already whitelisted!", delete_after=5)
        return
        
    except commands.UserNotFound:
        pass
    
    # Try to parse as role
    try:
        role = await commands.RoleConverter().convert(ctx, target)
        if role.id not in bot.whitelist_data["whitelisted_roles"]:
            bot.whitelist_data["whitelisted_roles"].append(role.id)
            save_data(bot.whitelist_data)
            
            embed = discord.Embed(
                title="✅ Role Whitelisted",
                description=f"Role {role.mention} can now post links!",
                color=discord.Color.green()
            )
            embed.add_field(name="Role", value=role.name, inline=True)
            embed.add_field(name="Members", value=str(len(role.members)), inline=True)
            embed.set_footer(text=f"Added by {ctx.author.name}")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠️ Role {role.mention} is already whitelisted!", delete_after=5)
        return
        
    except commands.RoleNotFound:
        await ctx.send("❌ Could not find user or role. Please use mentions: `@username` or `@rolename`", delete_after=10)

@bot.command(name='wlremove')
@commands.is_owner()
async def whitelist_remove(ctx, target=None):
    """Remove user or role from whitelist (Owner Only)"""
    if not target:
        await ctx.send("❌ Please mention a user or role: `!wlremove @user` or `!wlremove @role`", delete_after=10)
        return
    
    # Try to parse as user
    try:
        user = await commands.UserConverter().convert(ctx, target)
        if user.id in bot.whitelist_data["whitelisted_users"]:
            bot.whitelist_data["whitelisted_users"].remove(user.id)
            save_data(bot.whitelist_data)
            
            embed = discord.Embed(
                title="❌ User Removed from Whitelist",
                description=f"{user.mention} can no longer post links.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Removed by {ctx.author.name}")
            
            await ctx.send(embed=embed)
            
            # Notify the user
            try:
                notify_embed = discord.Embed(
                    title="🔒 Whitelist Access Revoked",
                    description=f"Your whitelist access has been removed in **{ctx.guild.name}**.",
                    color=discord.Color.red()
                )
                notify_embed.add_field(name="Removed By", value=ctx.author.mention, inline=True)
                notify_embed.set_footer(text="You can no longer post links")
                await user.send(embed=notify_embed)
            except:
                pass
        else:
            await ctx.send(f"⚠️ {user.mention} is not whitelisted!", delete_after=5)
        return
        
    except commands.UserNotFound:
        pass
    
    # Try to parse as role
    try:
        role = await commands.RoleConverter().convert(ctx, target)
        if role.id in bot.whitelist_data["whitelisted_roles"]:
            bot.whitelist_data["whitelisted_roles"].remove(role.id)
            save_data(bot.whitelist_data)
            
            embed = discord.Embed(
                title="❌ Role Removed from Whitelist",
                description=f"Role {role.mention} can no longer post links.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Removed by {ctx.author.name}")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠️ Role {role.mention} is not whitelisted!", delete_after=5)
        return
        
    except commands.RoleNotFound:
        await ctx.send("❌ Could not find user or role. Please use mentions: `@username` or `@rolename`", delete_after=10)

@bot.command(name='wllist')
@commands.is_owner()
async def whitelist_list(ctx):
    """Show all whitelisted users and roles (Owner Only)"""
    embed = discord.Embed(
        title="📋 Whitelist Status",
        color=discord.Color.blue()
    )
    
    # Whitelisted users
    users_list = []
    for user_id in bot.whitelist_data["whitelisted_users"]:
        user = bot.get_user(user_id)
        if user:
            users_list.append(f"• {user.mention} (`{user.name}#{user.discriminator}`)")
        else:
            users_list.append(f"• Unknown User (`{user_id}`)")
    
    if users_list:
        embed.add_field(name="👤 Whitelisted Users", value="\n".join(users_list), inline=False)
    else:
        embed.add_field(name="👤 Whitelisted Users", value="None", inline=False)
    
    # Whitelisted roles
    roles_list = []
    for role_id in bot.whitelist_data["whitelisted_roles"]:
        role = ctx.guild.get_role(role_id)
        if role:
            roles_list.append(f"• {role.mention} (`{role.name}`) - {len(role.members)} members")
        else:
            roles_list.append(f"• Unknown Role (`{role_id}`)")
    
    if roles_list:
        embed.add_field(name="🎭 Whitelisted Roles", value="\n".join(roles_list), inline=False)
    else:
        embed.add_field(name="🎭 Whitelisted Roles", value="None", inline=False)
    
    embed.add_field(name="📊 Stats", value=f"**Total Users:** {len(users_list)}\n**Total Roles:** {len(roles_list)}", inline=False)
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    
    await ctx.send(embed=embed)

@bot.command(name='wlcheck')
@commands.is_owner()
async def whitelist_check(ctx, target=None):
    """Check if a user or role is whitelisted (Owner Only)"""
    if not target:
        # Check the command author
        user = ctx.author
        if is_allowed(user):
            status = "✅ Whitelisted"
            color = discord.Color.green()
        else:
            status = "❌ Not Whitelisted"
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="🔍 Whitelist Check",
            description=f"**User:** {user.mention}",
            color=color
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        
        # Show whitelist source
        sources = []
        if user.id == OWNER_ID:
            sources.append("👑 Bot Owner")
        if user.id in bot.whitelist_data["whitelisted_users"]:
            sources.append("👤 Direct Whitelist")
        
        # Check roles
        user_role_ids = [role.id for role in user.roles]
        whitelisted_roles = []
        for role_id in bot.whitelist_data["whitelisted_roles"]:
            if role_id in user_role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    whitelisted_roles.append(role.name)
        
        if whitelisted_roles:
            sources.append(f"🎭 Role(s): {', '.join(whitelisted_roles)}")
        
        if sources:
            embed.add_field(name="Sources", value="\n".join(sources), inline=False)
        
        await ctx.send(embed=embed)
        return
    
    # Check specific target
    # Try user first
    try:
        user = await commands.UserConverter().convert(ctx, target)
        if is_allowed(user):
            status = "✅ Whitelisted"
            color = discord.Color.green()
        else:
            status = "❌ Not Whitelisted"
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="🔍 Whitelist Check",
            description=f"**User:** {user.mention}",
            color=color
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Username", value=f"`{user.name}#{user.discriminator}`", inline=True)
        
        await ctx.send(embed=embed)
        return
        
    except commands.UserNotFound:
        pass
    
    # Try role
    try:
        role = await commands.RoleConverter().convert(ctx, target)
        if role.id in bot.whitelist_data["whitelisted_roles"]:
            status = "✅ Whitelisted"
            color = discord.Color.green()
        else:
            status = "❌ Not Whitelisted"
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="🔍 Whitelist Check",
            description=f"**Role:** {role.mention}",
            color=color
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Role Name", value=role.name, inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        
        await ctx.send(embed=embed)
        return
        
    except commands.RoleNotFound:
        await ctx.send("❌ Could not find user or role.", delete_after=5)

@bot.command(name='wldm')
@commands.is_owner()
async def whitelist_dm_all(ctx):
    """DM all whitelisted users (Owner Only)"""
    if not bot.whitelist_data["whitelisted_users"]:
        await ctx.send("❌ No whitelisted users to DM.", delete_after=5)
        return
    
    confirm = await ctx.send(
        f"⚠️ **Confirm DM Broadcast**\n"
        f"This will DM {len(bot.whitelist_data['whitelisted_users'])} whitelisted users.\n\n"
        f"React with ✅ to proceed or ❌ to cancel."
    )
    
    await confirm.add_reaction('✅')
    await confirm.add_reaction('❌')
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        if str(reaction.emoji) == '✅':
            await confirm.edit(content="📨 Sending DMs...")
            
            success = 0
            failed = 0
            
            for user_id in bot.whitelist_data["whitelisted_users"]:
                user = bot.get_user(user_id)
                if user:
                    try:
                        embed = discord.Embed(
                            title="📢 Whitelist Announcement",
                            description=f"This is a message to all whitelisted users in **{ctx.guild.name}**.",
                            color=discord.Color.blue()
                        )
                        embed.add_field(name="Reminder", value="You are whitelisted to post links in this server.", inline=False)
                        embed.add_field(name="Allowed Links", value="• YouTube videos\n• Discord invites\n• All website links", inline=False)
                        embed.set_footer(text="From server administration")
                        await user.send(embed=embed)
                        success += 1
                    except:
                        failed += 1
                else:
                    failed += 1
                
                await asyncio.sleep(1)  # Rate limit protection
            
            await confirm.edit(
                content=f"✅ DM Broadcast Complete!\n"
                       f"Success: {success} users\n"
                       f"Failed: {failed} users"
            )
        else:
            await confirm.edit(content="❌ DM broadcast cancelled.")
    
    except asyncio.TimeoutError:
        await confirm.edit(content="⏰ DM broadcast timed out.")

# PUBLIC COMMANDS

@bot.command(name='request')
async def request_whitelist(ctx, *, reason=None):
    """Request whitelist access to post links"""
    if is_allowed(ctx.author):
        await ctx.send("✅ You are already whitelisted! You can post links.", delete_after=10)
        return
    
    # Find the owner to notify
    owner = bot.get_user(OWNER_ID)
    if not owner:
        await ctx.send("❌ Could not notify owner. Please contact them directly.", delete_after=10)
        return
    
    # Send request to owner
    request_embed = discord.Embed(
        title="🔔 Whitelist Request",
        description=f"**From:** {ctx.author.mention} (`{ctx.author.name}#{ctx.author.discriminator}`)",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    request_embed.add_field(name="Server", value=ctx.guild.name, inline=True)
    request_embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
    
    if reason:
        request_embed.add_field(name="Reason", value=reason, inline=False)
    
    request_embed.add_field(name="Quick Actions", 
                           value=f"Add: `!wladd {ctx.author.mention}`\nCheck: `!wlcheck {ctx.author.mention}`", 
                           inline=False)
    request_embed.set_footer(text=f"User ID: {ctx.author.id}")
    
    try:
        await owner.send(embed=request_embed)
        
        # Confirm to user
        confirm_embed = discord.Embed(
            title="✅ Request Sent",
            description="Your whitelist request has been sent to the bot owner.",
            color=discord.Color.green()
        )
        if reason:
            confirm_embed.add_field(name="Your Reason", value=reason, inline=False)
        confirm_embed.set_footer(text="You will be notified if approved")
        
        await ctx.send(embed=confirm_embed, delete_after=30)
        
        # Send DM confirmation to user
        try:
            user_dm = discord.Embed(
                title="📨 Whitelist Request Submitted",
                description=f"Your request to post links in **{ctx.guild.name}** has been submitted.",
                color=discord.Color.blue()
            )
            await ctx.author.send(embed=user_dm)
        except:
            pass
            
    except:
        await ctx.send("❌ Failed to send request to owner. They may have DMs disabled.", delete_after=10)

@bot.command(name='mystatus')
async def my_status(ctx):
    """Check your whitelist status"""
    if is_allowed(ctx.author):
        embed = discord.Embed(
            title="✅ Whitelist Status: APPROVED",
            description="You can post links in this server!",
            color=discord.Color.green()
        )
        
        # Show what you can post
        embed.add_field(
            name="✅ Allowed Links",
            value="• YouTube videos\n• Discord invites\n• All website URLs\n• Twitch links\n• Social media links",
            inline=False
        )
        
        # Show source
        sources = []
        if ctx.author.id == OWNER_ID:
            sources.append("👑 You are the bot owner")
        if ctx.author.id in bot.whitelist_data["whitelisted_users"]:
            sources.append("👤 You are directly whitelisted")
        
        # Check roles
        user_role_ids = [role.id for role in ctx.author.roles]
        whitelisted_roles = []
        for role_id in bot.whitelist_data["whitelisted_roles"]:
            if role_id in user_role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    whitelisted_roles.append(role.name)
        
        if whitelisted_roles:
            sources.append(f"🎭 You have whitelisted role(s): {', '.join(whitelisted_roles)}")
        
        if sources:
            embed.add_field(name="Access Source", value="\n".join(sources), inline=False)
        
    else:
        embed = discord.Embed(
            title="❌ Whitelist Status: NOT APPROVED",
            description="You cannot post links in this server.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="How to Get Access",
            value="Use `!request <reason>` to ask the owner for permission.\nExample: `!request I need to share tutorial videos`",
            inline=False
        )
        embed.add_field(
            name="❌ Blocked Links",
            value="• All URLs\n• Discord invites\n• YouTube links\n• Website links",
            inline=False
        )
    
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    await ctx.send(embed=embed, delete_after=30)

@bot.command(name='help')
async def help_command(ctx):
    """Show help information"""
    if ctx.author.id == OWNER_ID:
        # Owner help
        embed = discord.Embed(
            title="🛡️ Owner Commands",
            description="Bot owner commands",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="👥 Whitelist Management",
            value="• `!wladd @user` - Add user to whitelist\n"
                  "• `!wlremove @user` - Remove user\n"
                  "• `!wllist` - Show all whitelisted\n"
                  "• `!wlcheck @user` - Check status\n"
                  "• `!wldm` - DM all whitelisted users",
            inline=False
        )
        
        embed.add_field(
            name="📊 Information",
            value="• `!mystatus` - Check your status\n"
                  "• `!help` - Show this help",
            inline=False
        )
        
        embed.set_footer(text=f"Bot Owner: {ctx.author.name}")
        
    elif is_allowed(ctx.author):
        # Whitelisted user help
        embed = discord.Embed(
            title="✅ Whitelisted User Commands",
            description="You can post links!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="✅ You Can Post",
            value="• YouTube links\n• Discord invites\n• All website URLs\n• Social media links",
            inline=False
        )
        
        embed.add_field(
            name="📊 Information",
            value="• `!mystatus` - Check your status\n"
                  "• `!request <reason>` - Request for others\n"
                  "• `!help` - Show help",
            inline=False
        )
        
        embed.set_footer(text=f"Whitelisted User: {ctx.author.name}")
        
    else:
        # Regular user help
        embed = discord.Embed(
            title="🔒 Restricted Access",
            description="You cannot post links in this server.",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="❌ Blocked Content",
            value="• All URLs and website links\n• YouTube videos\n• Discord invites\n• Social media links",
            inline=False
        )
        
        embed.add_field(
            name="📋 Available Commands",
            value="• `!request <reason>` - Request whitelist access\n"
                  "• `!mystatus` - Check your status\n"
                  "• `!help` - Show this help",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ How to Get Access",
            value="Use `!request <reason>` to ask the owner.\nExample: `!request I need to share my YouTube tutorials`",
            inline=False
        )
    
    await ctx.send(embed=embed, delete_after=30)

# MODERATION COMMANDS (Owner only)

@bot.command(name='clean')
@commands.is_owner()
async def clean_links(ctx, limit: int = 50):
    """Clean up non-whitelisted links (Owner Only)"""
    if limit > 100:
        limit = 100
    
    processing = await ctx.send(f"🧹 Cleaning up to {limit} messages...")
    
    deleted_count = 0
    async for message in ctx.channel.history(limit=limit):
        # Skip bot messages and allowed users
        if message.author.bot or is_allowed(message.author):
            continue
        
        if contains_links(message.content):
            try:
                await message.delete()
                deleted_count += 1
                await asyncio.sleep(0.5)  # Rate limit protection
            except:
                pass
    
    await processing.delete()
    
    embed = discord.Embed(
        title="🧹 Cleanup Complete",
        color=discord.Color.green() if deleted_count == 0 else discord.Color.orange()
    )
    embed.add_field(name="Messages Scanned", value=str(limit), inline=True)
    embed.add_field(name="Links Deleted", value=str(deleted_count), inline=True)
    embed.add_field(name="Cleaner", value=ctx.author.mention, inline=True)
    
    result = await ctx.send(embed=embed)
    await result.delete(delay=30)
    
    if deleted_count > 0:
        await ctx.send(f"✅ Cleaned {deleted_count} non-whitelisted links.", delete_after=10)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        if ctx.author.id == OWNER_ID:
            await ctx.send("❌ You're not registered as owner in config!", delete_after=10)
        else:
            embed = discord.Embed(
                title="⛔ Owner Only",
                description="This command is only for the bot owner.",
                color=discord.Color.red()
            )
            msg = await ctx.send(embed=embed)
            await msg.delete(delay=10)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`", delete_after=5)
    else:
        if ctx.author.id == OWNER_ID:
            await ctx.send(f"❌ Error: {str(error)[:100]}", delete_after=10)

# Run the bot
if __name__ == "__main__":
    print("=" * 50)
    print("LINK REMOVER BOT - OWNER & WHITELIST ONLY")
    print("=" * 50)
    print(f"Owner ID: {OWNER_ID}")
    print(f"Whitelisted Users: {len(bot.whitelist_data['whitelisted_users'])}")
    print(f"Whitelisted Roles: {len(bot.whitelist_data['whitelisted_roles'])}")
    print("=" * 50)
    print("Only owner and whitelisted users can post links")
    print("=" * 50)
    
    bot.run(TOKEN)
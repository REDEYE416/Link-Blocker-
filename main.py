import discord
from discord.ext import commands
import re
from datetime import datetime

# Bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration - ONLY CHANGE THESE TWO VALUES
OWNER_ID = YOUR_OWNER_ID_HERE  # Replace with your Discord ID
TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Replace with your bot token

# Link patterns
LINK_PATTERNS = [
    r'(https?://)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+',  # Discord invites
    r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+',  # YouTube links
    r'(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/\S*)?'  # General URLs
]

def is_owner(user):
    """Check if user is the bot owner"""
    return user.id == OWNER_ID

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
    await bot.change_presence(activity=discord.Game(name="!help - Owner Only"))

@bot.event
async def on_message(message):
    # Don't process bot's own messages
    if message.author.bot:
        return
    
    # Check if user is the owner
    if is_owner(message.author):
        await bot.process_commands(message)
        return
    
    # Check for links in message from non-owners
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
                    f"{message.author.mention}, Only the bot owner can post links!",
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
                if original_content:
                    content_preview = original_content[:300] + "..." if len(original_content) > 300 else original_content
                    dm_embed.add_field(name="Your Message", value=f"```{content_preview}```", inline=False)
                dm_embed.set_footer(text="Only the bot owner is allowed to post links")
                await message.author.send(embed=dm_embed)
            except:
                pass  # User has DMs closed
            
        except discord.NotFound:
            pass  # Message already deleted
        except Exception as e:
            print(f"Error: {e}")
        
        return
    
    # Process commands for non-owners (only !help will work)
    await bot.process_commands(message)

# OWNER ONLY COMMANDS

@bot.command(name='status')
@commands.is_owner()
async def bot_status(ctx):
    """Show bot status and configuration (Owner Only)"""
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green()
    )
    
    embed.add_field(name="👑 Owner", value=f"<@{OWNER_ID}>", inline=True)
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="📊 Servers", value=str(len(bot.guilds)), inline=True)
    
    # Get uptime
    delta = datetime.utcnow() - bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    embed.add_field(name="⏰ Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    
    embed.set_footer(text="Bot Owner: Only you can post links and use commands")
    await ctx.send(embed=embed)

@bot.command(name='deletemsg')
@commands.is_owner()
async def delete_message(ctx, message_id: int):
    """Delete any message by ID (Owner Only)"""
    try:
        message = await ctx.channel.fetch_message(message_id)
        
        # Don't allow deleting owner's messages
        if message.author.id == OWNER_ID:
            await ctx.send("❌ Cannot delete owner's messages!", delete_after=5)
            return
        
        original_content = message.content
        
        await message.delete()
        
        # Create delete log
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="👤 User", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=True)
        
        if original_content:
            content_preview = original_content[:300] + "..." if len(original_content) > 300 else original_content
            embed.add_field(name="📝 Content", value=f"```{content_preview}```", inline=False)
        
        embed.add_field(name="📌 Channel", value=ctx.channel.mention, inline=True)
        
        log_msg = await ctx.send(embed=embed)
        await log_msg.delete(delay=30)
        
        await ctx.send(f"✅ Message `{message_id}` deleted.", delete_after=5)
        
    except discord.NotFound:
        await ctx.send("❌ Message not found!", delete_after=5)
    except discord.Forbidden:
        await ctx.send("❌ No permission to delete that message!", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:100]}", delete_after=5)

@bot.command(name='cleanup')
@commands.is_owner()
async def cleanup_channel(ctx, limit: int = 50):
    """Clean up non-owner messages with links (Owner Only)"""
    if limit > 200:
        limit = 200
    
    processing = await ctx.send(f"🧹 Cleaning up to {limit} messages...")
    
    deleted_count = 0
    async for message in ctx.channel.history(limit=limit):
        # Skip bot messages and owner messages
        if message.author.bot or is_owner(message.author):
            continue
        
        if contains_links(message.content):
            try:
                await message.delete()
                deleted_count += 1
            except:
                pass
    
    await processing.delete()
    
    embed = discord.Embed(
        title="🧹 Cleanup Complete",
        description=f"Cleaned {ctx.channel.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="Messages Scanned", value=str(limit), inline=True)
    embed.add_field(name="Links Deleted", value=str(deleted_count), inline=True)
    embed.set_footer(text=f"Cleaned by {ctx.author.name}")
    
    result = await ctx.send(embed=embed)
    await result.delete(delay=30)
    
    await ctx.send(f"✅ Cleaned {deleted_count} messages with links.", delete_after=10)

@bot.command(name='broadcast')
@commands.is_owner()
async def broadcast_message(ctx, *, message: str):
    """Broadcast a message to all servers (Owner Only)"""
    confirm = await ctx.send(
        f"⚠️ **Confirm Broadcast**\n"
        f"Message: {message[:100]}...\n\n"
        f"React with ✅ to send to {len(bot.guilds)} servers."
    )
    
    await confirm.add_reaction('✅')
    await confirm.add_reaction('❌')
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        if str(reaction.emoji) == '✅':
            await confirm.edit(content="📢 Broadcasting...")
            
            success = 0
            failed = 0
            
            for guild in bot.guilds:
                try:
                    # Try to send to system channel or first text channel
                    channel = guild.system_channel
                    if not channel or not channel.permissions_for(guild.me).send_messages:
                        # Find first channel with send permissions
                        for ch in guild.text_channels:
                            if ch.permissions_for(guild.me).send_messages:
                                channel = ch
                                break
                    
                    if channel:
                        embed = discord.Embed(
                            title="📢 Broadcast Message",
                            description=message,
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_footer(text=f"From: {ctx.author.name}")
                        await channel.send(embed=embed)
                        success += 1
                    else:
                        failed += 1
                        
                except:
                    failed += 1
                
                await asyncio.sleep(1)  # Rate limit protection
            
            await confirm.edit(
                content=f"✅ Broadcast Complete!\n"
                       f"Success: {success} servers\n"
                       f"Failed: {failed} servers"
            )
        else:
            await confirm.edit(content="❌ Broadcast cancelled.")
    
    except asyncio.TimeoutError:
        await confirm.edit(content="⏰ Broadcast timed out.")

@bot.command(name='shutdown')
@commands.is_owner()
async def shutdown_bot(ctx):
    """Shutdown the bot (Owner Only)"""
    embed = discord.Embed(
        title="🔌 Shutting Down",
        description="Bot is shutting down...",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    
    await ctx.send(embed=embed)
    await bot.close()

# NON-OWNER ACCESSIBLE COMMANDS (Info only)

@bot.command(name='help')
async def help_command(ctx):
    """Show help information"""
    if is_owner(ctx.author):
        # Owner help
        embed = discord.Embed(
            title="🛡️ Owner Commands",
            description="Only you can use these commands",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🛠️ Moderation",
            value="• `!deletemsg <id>` - Delete any message\n"
                  "• `!cleanup <limit>` - Clean links (default: 50)\n"
                  "• `!broadcast <msg>` - Broadcast to all servers",
            inline=False
        )
        
        embed.add_field(
            name="📊 Bot Info",
            value="• `!status` - Bot status\n"
                  "• `!shutdown` - Shutdown bot",
            inline=False
        )
        
        embed.set_footer(text=f"Bot Owner: {ctx.author.name}")
        
    else:
        # Regular user help
        embed = discord.Embed(
            title="❌ Restricted Access",
            description="This bot's commands are only available to the owner.",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value="• Only the bot owner can post links\n"
                  "• Messages with links are automatically deleted\n"
                  "• Contact the server admin for assistance",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        # Send a secret message to owner, ignore others
        if ctx.author.id == OWNER_ID:
            await ctx.send("❌ You're not registered as owner in config!", delete_after=10)
        else:
            # Send public error message
            embed = discord.Embed(
                title="⛔ Access Denied",
                description="Only the bot owner can use commands!",
                color=discord.Color.red()
            )
            msg = await ctx.send(embed=embed)
            await msg.delete(delay=10)
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        if is_owner(ctx.author):
            await ctx.send(f"❌ Missing argument: {error.param.name}", delete_after=5)
    else:
        if is_owner(ctx.author):
            await ctx.send(f"❌ Error: {str(error)[:100]}", delete_after=10)

# Track bot start time
@bot.event
async def on_connect():
    bot.start_time = datetime.utcnow()

# Run the bot
if __name__ == "__main__":
    import asyncio
    
    print("=" * 50)
    print("LINK REMOVER BOT - OWNER ONLY")
    print("=" * 50)
    print(f"Configured Owner ID: {OWNER_ID}")
    print("Only the owner can post links and use commands")
    print("=" * 50)
    
    bot.run(TOKEN)

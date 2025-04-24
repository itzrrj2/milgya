import re 
from datetime import datetime, timedelta
import logging
import asyncio
import random
import string
import os
import sys
import traceback
import json
import requests
from pathlib import Path
from threading import Thread
from flask import Flask, render_template
from waitress import serve
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, MessageNotModified, UserNotParticipant
from os import environ
import time
from status import format_progress_bar  # Assuming this is a custom module
from video import (
    download_video, 
    upload_video,
    handle_video_download_failure
)  # Assuming these are custom modules
from database.database import (
    present_user, add_user, full_userbase, del_user, db_verify_status, 
    db_update_verify_status, get_user, update_user, get_download_count, 
    increment_download_count, is_premium, add_premium, remove_premium,
    is_shortlink_verified, set_shortlink_verified, update_channel_membership,
    check_channel_membership, check_all_channel_memberships
)  # Import the new database functions
from shortzy import Shortzy  # Assuming this is a custom module
from pymongo.errors import DuplicateKeyError
from web import keep_alive
from config import *
import pyrogram

def log_error(message, exception, additional_info=None):
    """Log critical errors with detailed information"""
    error_details = f"{message}: {str(exception)}"
    
    if additional_info:
        error_details += f"\nAdditional Info: {additional_info}"
    
    if hasattr(exception, '__traceback__'):
        import traceback
        traceback_str = ''.join(traceback.format_tb(exception.__traceback__))
        error_details += f"\nTraceback: {traceback_str}"
    
    error_logger.error(error_details)
    return error_details

# Configure logging
def setup_logging():
    """Set up enhanced logging with rotating file handler"""
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Log to file with 5MB max size, keeping 5 backup files
    file_handler = logging.FileHandler("bot.log")
    file_handler.setFormatter(log_formatter)
    
    # Log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set up a special error logger that logs more details for errors
    error_logger = logging.getLogger("error_logger")
    error_logger.setLevel(logging.ERROR)
    
    return root_logger, error_logger

# Initialize logging
logger, error_logger = setup_logging()

# Track bot start time for uptime calculation
START_TIME = time.time()

# Load environment variables
try:
    load_dotenv('config.env', override=True)
    logger.info("Environment variables loaded successfully")
except Exception as e:
    error_logger.error(f"Error loading environment variables: {e}")
    exit(1)

# Validate required environment variables
try:
    ADMINS = list(map(int, os.environ.get('ADMINS', '7427294551').split()))
    if not ADMINS:
        error_logger.error("ADMINS variable is missing! Exiting now")
        exit(1)
        
    api_id = os.environ.get('TELEGRAM_API', '')
    if not api_id:
        error_logger.error("TELEGRAM_API variable is missing! Exiting now")
        exit(1)

    api_hash = os.environ.get('TELEGRAM_HASH', '')
    if not api_hash:
        error_logger.error("TELEGRAM_HASH variable is missing! Exiting now")
        exit(1)
        
    bot_token = os.environ.get('BOT_TOKEN', '')
    if not bot_token:
        error_logger.error("BOT_TOKEN variable is missing! Exiting now")
        exit(1)
    dump_id = os.environ.get('DUMP_CHAT_ID', '')
    if not dump_id:
        error_logger.error("DUMP_CHAT_ID variable is missing! Exiting now")
        exit(1)
    else:
        dump_id = int(dump_id)

    fsub_id = os.environ.get('FSUB_ID', '')
    if not fsub_id:
        error_logger.error("FSUB_ID variable is missing! Exiting now")
        exit(1)
    else:
        fsub_id = int(fsub_id)

    logger.info("Required environment variables validated successfully")
except Exception as e:
    error_logger.error(f"Error validating environment variables: {e}")
    exit(1)

# Initialize MongoDB connection
try:
    mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://shresthstakeyt:pkLkVmVw2xCkdtvD@tera0.kbiwslv.mongodb.net/?retryWrites=true&w=majority&appName=tera0')
    client = MongoClient(mongo_url)
    # Test the connection
    client.admin.command('ping')
    db = client['cphdlust']
    users_collection = db['users']
    logger.info("MongoDB connection initialized successfully")
except Exception as e:
    error_logger.error(f"Error initializing MongoDB connection: {e}")
    exit(1)

# Initialize Pyrogram client
try:
    app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token, workers=100)
    logger.info("Pyrogram client initialized successfully")
except Exception as e:
    error_logger.error(f"Error initializing Pyrogram client: {e}")
    exit(1)

def extract_links(text):
    url_pattern = r'(https?://[^\s]+)'  # Regex to capture http/https URLs
    links = re.findall(url_pattern, text)
    return links

def save_user(user_id, username):
    try:
        existing_user = users_collection.find_one({'user_id': user_id})
        if existing_user is None:
            users_collection.insert_one({'user_id': user_id, 'username': username})
            logging.info(f"Saved new user {username} with ID {user_id} to the database.")
        else:
            users_collection.update_one({'user_id': user_id}, {'$set': {'username': username}})
            logging.info(f"Updated user {username} with ID {user_id} in the database.")
    except DuplicateKeyError as e:
        logging.error(f"DuplicateKeyError: {e}")
        
async def get_shortlink(url, api, link):
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link

def get_exp_time(seconds):
    periods = [('days', 86400), ('hours', 3600), ('mins', 60), ('secs', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name} '
    return result

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

async def get_verify_status(user_id):
    verify = await db_verify_status(user_id)
    return verify

async def update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link=""):
    current = await db_verify_status(user_id)
    current['verify_token'] = verify_token
    current['is_verified'] = is_verified
    current['verified_time'] = verified_time
    current['link'] = link
    await db_update_verify_status(user_id, current)

async def check_membership(client, user_id, channels=REQUIRED_CHANNELS):
    """Check if user is a member of required channels with retry mechanism"""
    memberships = {}
    MAX_RETRIES = 3
    
    for channel_name, channel_info in channels.items():
        retry_count = 0
        channel_id = channel_info["id"]
        
        while retry_count < MAX_RETRIES:
            try:
                member = await client.get_chat_member(channel_id, user_id)
                is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
                memberships[channel_name] = is_member
                # Update the database with membership status
                await update_channel_membership(user_id, channel_name, is_member)
                break  # Success, exit the retry loop
                
            except FloodWait as e:
                logging.warning(f"FloodWait error checking membership for {channel_name}: waiting {e.x} seconds")
                await asyncio.sleep(e.x)
                retry_count += 1
                
            except UserNotParticipant:
                # This is an expected exception when user is not a member
                logging.info(f"User {user_id} is not a member of {channel_name}")
                memberships[channel_name] = False
                await update_channel_membership(user_id, channel_name, False)
                break
                
            except Exception as e:
                retry_count += 1
                logging.error(f"Error checking membership for {channel_name} (attempt {retry_count}/{MAX_RETRIES}): {e}")
                await asyncio.sleep(1)  # Wait before retry
                
                if retry_count >= MAX_RETRIES:
                    # After all retries failed, set membership to False
                    logging.error(f"Failed to check membership for {channel_name} after {MAX_RETRIES} attempts")
                    memberships[channel_name] = False
                    await update_channel_membership(user_id, channel_name, False)
    
    return memberships

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    is_admin = user_id in ADMINS
    
    # Check if user is present
    if not await present_user(user_id):
        try:
            await add_user(user_id)
            logger.info(f"Added user {user_id} to the database")
        except Exception as e:
            error_logger.error(f"Failed to add user {user_id} to the database: {e}")
    
    # Check if user is premium
    db_premium_status = await is_premium(user_id)
    premium_status = True if is_admin else db_premium_status
    
    # Special start message for admins
    if is_admin and len(message.text.split()) == 1:  # Just /start without parameters
        admin_welcome = (
            f"👋 **Welcome Admin!**\n\n"
            f"You have full access to all bot features as an administrator.\n\n"
            f"**Quick Admin Commands:**\n"
            f"• `/help` - View all admin commands\n"
            f"• `/stats` - Show bot statistics\n"
            f"• `/addpremium <user_id> <months>` - Add premium user\n"
            f"• `/premiumlist` - List all premium users\n\n"
            f"**Bot Version:** {BOT_VERSION}"
        )
        
        # Admin panel buttons
        stats_button = InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
        help_button = InlineKeyboardButton("🔍 Help", callback_data="admin_help")
        user_view_button = InlineKeyboardButton("👤 User View", callback_data="user_view")
        
        await message.reply(
            admin_welcome,
            reply_markup=InlineKeyboardMarkup([
                [stats_button, help_button],
                [user_view_button]
            ])
        )
        return
    
    # Check message text for purchase
    if "purchase" in message.text:
        if premium_status:
            if is_admin:
                await message.reply(f"✅ You are an admin with unlimited access to all features!")
            else:
                user = await get_user(user_id)
                premium_expiry = datetime.fromtimestamp(user.get('premium_expiry', 0))
                days_left = (premium_expiry - datetime.now()).days
                await message.reply(f"✅ You are already a premium user with {days_left} days left. Enjoy unlimited downloads without ads!")
        else:
            # Create premium purchase message
            premium_text = (
                "🌟 **Premium Membership** 🌟\n\n"
                "Get unlimited access to all bot features without ads or limitations!\n\n"
                "**Premium Benefits:**\n"
                "✅ Unlimited Downloads\n"
                "✅ No Shortlink Verification\n"
                "✅ Priority Processing\n"
                "✅ Premium Support\n\n"
                "📊 **Pricing Plans (Telegram Stars):**\n"
                "• 1 Month: 25 Stars ⭐\n"
                "• 2 Months:50 Stars ⭐\n"
                "• Lifetime: 100 Stars ⭐\n\n"
                "Purchase premium via our payment bot to unlock all features instantly!"
            )
            
            purchase_month = InlineKeyboardButton("Purchase ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")
            three_months = InlineKeyboardButton("How to Purchase", url="https://t.me/sr_bots_premium_tutorial")
            join_support = InlineKeyboardButton("📱 Support", url="https://t.me/SR_SUPPORTxBOT")
            
            await message.reply(premium_text, reply_markup=InlineKeyboardMarkup([
                [purchase_month],
                [two_months],
                [three_months],
                [join_support]
            ]))
        return

    # Get verification status
    verify_status = await db_verify_status(user_id)
    logger.info(f"Verify status for user {user_id}: {verify_status}")

    # Check verification expiration
    if verify_status["is_verified"] and VERIFY_EXPIRE < (time.time() - verify_status["verified_time"]):
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': False})
        verify_status['is_verified'] = False
        logger.info(f"Verification expired for user {user_id}")

    # Check for token verification in the command
    text = message.text
    if "verify_" in text:
        _, token = text.split("_", 1)
        logger.info(f"Extracted token: {token}")
        if verify_status["verify_token"] != token:
            logger.warning(f"Invalid or expired token for user {user_id}")
            return await message.reply("Your token is invalid or expired. Try again by clicking /start.")
        
        # Set both verification types
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': True, 'verified_time': time.time()})
        await set_shortlink_verified(user_id, SHORTLINK_HOURS)
        
        logger.info(f"User {user_id} verified successfully")
        
        hours_text = "hour" if SHORTLINK_HOURS == 1 else "hours"
        return await message.reply(f"✅ Your token has been successfully verified! You now have {SHORTLINK_HOURS} {hours_text} of access without shortlink verification.")

    # Get download count for user
    download_count = await get_download_count(user_id)
    free_downloads_left = max(0, FREE_DOWNLOADS - download_count)
    
    # Check channel membership
    memberships = await check_membership(client, user_id)
    all_joined = all(memberships.values())
    
    # If user hasn't joined all channels
    if not all_joined:
        channels_text = ""
        buttons = []
        
        for channel_name, is_joined in memberships.items():
            if not is_joined:
                channel_info = REQUIRED_CHANNELS.get(channel_name)
                invite_link = channel_info.get("invite_link")
                channels_text += f"• {channel_name}\n"
                buttons.append([InlineKeyboardButton(f"Join {channel_name}", url=invite_link)])
        
        buttons.append([InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")])
        
        await message.reply(
            f"⚠️ **Channel Membership Required**\n\n"
            f"Please join the following channels to use this bot:\n\n"
            f"{channels_text}\n"
            f"After joining, click '✅ Check Membership' button.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    # Enhanced welcome message for all users (premium, verified, or free)
    welcome_message = (
        f"🌟 **Welcome to the Ultimate TeraBox Downloader Bot, {user_mention}!**\n\n"
        f"🚀 **Why Choose This Bot?**\n"
        f"- **Unmatched Speed**: Experience the fastest and most powerful TeraBox downloader on Telegram. ⚡\n"
        f"- **100% Free **: Verify Via Short Link And Enjoy For Free 🆓\n"
        f"- **Seamless Downloads**: Easily download TeraBox files and have them sent directly to you. 🎥📁\n"
        f"- **24/7 Availability**: Access the bot anytime, anywhere, without downtime. ⏰\n\n"
        f"🎯 **How It Works**\n"
        f"Simply send a TeraBox link, and let the bot handle the rest. It's quick, easy, and reliable! 🚀\n\n"
        f"💎 **Your Ultimate Telegram Tool**—crafted to make your experience effortless and enjoyable."
    )
    
    # Add status message based on user type
    if premium_status:
        if is_admin:
            status_message = "\n\n🔰 **Admin Status**: You have unlimited access to all features!"
        else:
            user = await get_user(user_id)
            premium_expiry = datetime.fromtimestamp(user.get('premium_expiry', 0))
            days_left = (premium_expiry - datetime.now()).days
            status_message = f"\n\n🌟 **Premium Status**: You have unlimited downloads with {days_left} days remaining"
    elif verify_status["is_verified"]:
        expiry_time = get_exp_time(VERIFY_EXPIRE - (time.time() - verify_status['verified_time']))
        status_message = f"\n\n✅ **Verified Status**: Your verification is valid for {expiry_time}"
    elif free_downloads_left > 0:
        status_message = f"\n\n🎁 **Free Downloads Left**: {free_downloads_left}"
    else:
        status_message = "\n\n⚠️ **Free Downloads Used**: Please verify to continue using the bot"
    
    welcome_message += status_message
    
    # Add buttons based on premium status
    join_button = InlineKeyboardButton("Join Channel ❤️", url=REQUIRED_CHANNELS["sr_robots"]["invite_link"])
    developer_button = InlineKeyboardButton("Developer ⚡️", url="https://t.me/sr_robots")
    profile_button = InlineKeyboardButton("My Profile 👤", callback_data="profile")
    premium_button = InlineKeyboardButton("Premium ⭐", callback_data="premium_info")
    
    buttons = []
    if premium_status:
        buttons.append([join_button, developer_button])
        buttons.append([profile_button])
    else:
        buttons.append([join_button, developer_button])
        buttons.append([profile_button, premium_button])
        
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # If verification is needed (user has used all free downloads)
    if free_downloads_left == 0 and not premium_status and not verify_status["is_verified"] and IS_VERIFY:
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        logger.info(f"Generated token: {token}")
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{BOT_USERNAME}?start=verify_{token}')
        await db_update_verify_status(user_id, {**verify_status, 'verify_token': token, 'link': link})
        
        verify_button = InlineKeyboardButton("Verify Now 🔗", url=link)
        tutorial_button = InlineKeyboardButton("How to Verify 🎥", url=TUT_VID)
        
        verification_buttons = [
            [verify_button],
            [premium_button],
            [tutorial_button],
            [join_button, developer_button]
        ]
        
        reply_markup = InlineKeyboardMarkup(verification_buttons)
    
    await message.reply_text(welcome_message, reply_markup=reply_markup)

@app.on_message(filters.command("profile"))
async def profile_command(client, message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    is_admin = user_id in ADMINS
    
    # Get premium status
    db_premium_status = await is_premium(user_id)
    premium_status = True if is_admin else db_premium_status
    
    # Get shortlink verification status
    shortlink_verified = await is_shortlink_verified(user_id)
    
    # Get download count
    download_count = user.get('download_count', 0)
    
    # Format the profile message
    if is_admin:
        status_text = f"🔰 **Admin**\n👑 Unlimited Access"
    elif premium_status:
        premium_expiry = datetime.fromtimestamp(user.get('premium_expiry', 0))
        days_left = (premium_expiry - datetime.now()).days
        hours_left = int(((premium_expiry - datetime.now()).total_seconds() % 86400) // 3600)
        
        # Format the expiration date and time remaining in a readable way
        exact_expiry = premium_expiry.strftime("%d %b %Y, %H:%M:%S")
        if days_left > 0:
            time_left = f"{days_left} days, {hours_left} hours"
        else:
            minutes_left = int(((premium_expiry - datetime.now()).total_seconds() % 3600) // 60)
            time_left = f"{hours_left} hours, {minutes_left} minutes"
            
        status_text = f"🌟 **Premium User**\n🗓️ Expires: {exact_expiry}\n⏱️ Time Remaining: {time_left}"
    elif shortlink_verified:
        shortlink_expiry = datetime.fromtimestamp(user.get('shortlink_expiry', 0))
        total_seconds_left = max(0, (shortlink_expiry - datetime.now()).total_seconds())
        hours_left = int(total_seconds_left // 3600)
        minutes_left = int((total_seconds_left % 3600) // 60)
        status_text = f"✅ **Shortlink Verified User**\n⏱️ Time Remaining: {hours_left}h {minutes_left}m"
    else:
        free_downloads_left = max(0, FREE_DOWNLOADS - download_count)
        status_text = f"⭐ **Free User**\n📥 Free Downloads Left: {free_downloads_left}"
    
    profile_text = (
        f"👤 **Your Profile**\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📊 Status: {status_text}\n"
        f"📈 Total Downloads: {download_count}\n\n"
        f"🔄 Last Updated: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"
    )
    
    # Add buttons
    premium_button = InlineKeyboardButton("Get Premium ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")
    verify_button = None
    
    if not premium_status and not shortlink_verified and not is_admin and download_count >= FREE_DOWNLOADS:
        # Generate shortlink verification
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        logging.info(f"Generated token: {token}")
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{BOT_USERNAME}?start=verify_{token}')
        verify_status = await db_verify_status(user_id)
        await db_update_verify_status(user_id, {**verify_status, 'verify_token': token, 'link': link})
        verify_button = InlineKeyboardButton("Verify Shortlink ✅", url=link)
    
    buttons = []
    if verify_button:
        buttons.append([verify_button])
    if not premium_status and not is_admin:
        buttons.append([premium_button])
    
    # Always add back button
    back_button = InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
    buttons.append([back_button])
    
    await message.reply(profile_text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)

@app.on_callback_query()
async def handle_callback(client, callback_query):
    try:
        data = callback_query.data
        user_id = callback_query.from_user.id
        is_admin = user_id in ADMINS
        
        # Admin-only callbacks
        if is_admin and data == "admin_stats":
            try:
                # Generate stats message
                total_users = users_collection.count_documents({})
                premium_users = users_collection.count_documents({"premium": True})
                verified_users = users_collection.count_documents({"verify_status.is_verified": True})
                shortlink_verified_users = users_collection.count_documents({"shortlink_verified": True})
                downloads_today = 0  # Could implement this with a date field in the future
                
                stats_text = (
                    "📊 **Bot Statistics**\n\n"
                    f"**Users:**\n"
                    f"• Total Users: `{total_users}`\n"
                    f"• Premium Users: `{premium_users}`\n"
                    f"• Verified Users: `{verified_users}`\n"
                    f"• Shortlink Verified: `{shortlink_verified_users}`\n\n"
                    f"**System:**\n"
                    f"• Bot Version: `{BOT_VERSION}`\n"
                    f"• Uptime: {get_readable_time(time.time() - START_TIME)}\n\n"
                    f"**Last Updated:** {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"
                )
                
                back_button = InlineKeyboardButton("🔙 Back", callback_data="admin_back")
                
                await callback_query.message.edit_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup([[back_button]])
                )
                await callback_query.answer("Statistics updated")
            except Exception as e:
                logging.error(f"Error in admin_stats callback: {str(e)}")
                await callback_query.answer("Error fetching statistics", show_alert=True)
            return
        
        elif is_admin and data == "admin_help":
            help_text = (
                "🔰 **Admin Commands**\n\n"
                "• `/start` - Start the bot\n"
                "• `/profile` - View your profile\n"
                "• `/stats` - Show bot statistics\n"
                "• `/check` - Check verification status\n\n"
                "**Premium Management:**\n"
                "• `/addpremium <user_id> <months>` - Add premium to a user\n"
                "• `/removepremium <user_id>` - Remove premium from a user\n"
                "• `/premiumlist` - List all premium users\n\n"
                "**Broadcasting:**\n"
                "• `/broadcast` - Send message to all users (Reply to a message)\n\n"
                "**Bot Version:** " + BOT_VERSION
            )
            
            back_button = InlineKeyboardButton("🔙 Back", callback_data="admin_back")
            
            await callback_query.message.edit_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([[back_button]])
            )
            await callback_query.answer("Help menu opened")
            return
        
        elif is_admin and data == "admin_back":
            admin_welcome = (
                f"👋 **Welcome Admin!**\n\n"
                f"You have full access to all bot features as an administrator.\n\n"
                f"**Quick Admin Commands:**\n"
                f"• `/help` - View all admin commands\n"
                f"• `/stats` - Show bot statistics\n"
                f"• `/addpremium <user_id> <months>` - Add premium user\n"
                f"• `/premiumlist` - List all premium users\n\n"
                f"**Bot Version:** {BOT_VERSION}"
            )
            
            # Admin panel buttons
            stats_button = InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
            help_button = InlineKeyboardButton("🔍 Help", callback_data="admin_help")
            user_view_button = InlineKeyboardButton("👤 User View", callback_data="user_view")
            
            await callback_query.message.edit_text(
                admin_welcome,
                reply_markup=InlineKeyboardMarkup([
                    [stats_button, help_button],
                    [user_view_button]
                ])
            )
            await callback_query.answer("Back to admin panel")
            return
        
        elif is_admin and data == "user_view":
            # Show the normal user view to the admin
            user_mention = callback_query.from_user.mention
            
            reply_message = (
                f"🌟 Welcome to the Ultimate TeraBox Downloader Bot, {user_mention}!\n\n"
                "🚀 **Why Choose This Bot?**\n"
                "- **Unmatched Speed**: Experience the fastest and most powerful TeraBox downloader on Telegram. ⚡\n"
                "- **100% Free **: Verify Via Short Link And Enjoy For Free 🆓\n"
                "- **Seamless Downloads**: Easily download TeraBox files and have them sent directly to you. 🎥📁\n"
                "- **24/7 Availability**: Access the bot anytime, anywhere, without downtime. ⏰\n\n"
                "🎯 **How It Works**\n"
                "Simply send a TeraBox link, and let the bot handle the rest. It's quick, easy, and reliable! 🚀\n\n"
                "💎 **Your Ultimate Telegram Tool**—crafted to make your experience effortless and enjoyable."
            )
            
            # Add buttons
            join_button = InlineKeyboardButton("Join Channel ❤️", url=REQUIRED_CHANNELS["sr_robots"]["invite_link"])
            developer_button = InlineKeyboardButton("Developer ⚡️", url="https://t.me/sr_robots")
            profile_button = InlineKeyboardButton("My Profile 👤", callback_data="profile")
            back_button = InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_back")
            
            await callback_query.message.edit_text(
                reply_message,
                reply_markup=InlineKeyboardMarkup([
                    [join_button, developer_button],
                    [profile_button],
                    [back_button]
                ])
            )
            await callback_query.answer("User view displayed")
            return
        
        if data == "profile":
            # Get user data
            user = await get_user(user_id)
            
            # Get premium status
            db_premium_status = await is_premium(user_id)
            premium_status = True if is_admin else db_premium_status
            
            # Get shortlink verification status
            shortlink_verified = await is_shortlink_verified(user_id)
            
            # Get download count
            download_count = user.get('download_count', 0)
            
            # Format the profile message
            if is_admin:
                status_text = f"🔰 **Admin**\n👑 Unlimited Access"
            elif premium_status:
                premium_expiry = datetime.fromtimestamp(user.get('premium_expiry', 0))
                days_left = (premium_expiry - datetime.now()).days
                hours_left = int(((premium_expiry - datetime.now()).total_seconds() % 86400) // 3600)
                
                # Format the expiration date and time remaining in a readable way
                exact_expiry = premium_expiry.strftime("%d %b %Y, %H:%M:%S")
                if days_left > 0:
                    time_left = f"{days_left} days, {hours_left} hours"
                else:
                    minutes_left = int(((premium_expiry - datetime.now()).total_seconds() % 3600) // 60)
                    time_left = f"{hours_left} hours, {minutes_left} minutes"
                    
                status_text = f"🌟 **Premium User**\n🗓️ Expires: {exact_expiry}\n⏱️ Time Remaining: {time_left}"
            elif shortlink_verified:
                shortlink_expiry = datetime.fromtimestamp(user.get('shortlink_expiry', 0))
                total_seconds_left = max(0, (shortlink_expiry - datetime.now()).total_seconds())
                hours_left = int(total_seconds_left // 3600)
                minutes_left = int((total_seconds_left % 3600) // 60)
                status_text = f"✅ **Shortlink Verified User**\n⏱️ Time Remaining: {hours_left}h {minutes_left}m"
            else:
                free_downloads_left = max(0, FREE_DOWNLOADS - download_count)
                status_text = f"⭐ **Free User**\n📥 Free Downloads Left: {free_downloads_left}"
            
            profile_text = (
                f"👤 **Your Profile**\n\n"
                f"🆔 User ID: `{user_id}`\n"
                f"📊 Status: {status_text}\n"
                f"📈 Total Downloads: {download_count}\n\n"
                f"🔄 Last Updated: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"
            )
            
            # Add buttons
            premium_button = InlineKeyboardButton("Get Premium ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")
            verify_button = None
            
            if not premium_status and not shortlink_verified and not is_admin and download_count >= FREE_DOWNLOADS:
                # Generate shortlink verification
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                logging.info(f"Generated token: {token}")
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{BOT_USERNAME}?start=verify_{token}')
                verify_status = await db_verify_status(user_id)
                await db_update_verify_status(user_id, {**verify_status, 'verify_token': token, 'link': link})
                verify_button = InlineKeyboardButton("Verify Shortlink ✅", url=link)
            
            buttons = []
            if verify_button:
                buttons.append([verify_button])
            if not premium_status and not is_admin:
                buttons.append([premium_button])
            
            # Add appropriate back button
            if is_admin:
                back_button = InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_back")
            else:
                back_button = InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
            
            buttons.append([back_button])
            
            await callback_query.message.edit_text(
                profile_text, 
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
            )
            await callback_query.answer("Profile updated")
        
        elif data == "check_membership":
            # Check channel membership
            memberships = await check_membership(client, user_id)
            all_joined = all(memberships.values())
            
            if all_joined:
                await callback_query.message.edit_text(
                    "✅ Thank you for joining all required channels!\n\n"
                    "You can now use the bot. Type /start to begin.",
                )
                await callback_query.answer("Membership verified!")
            else:
                # Update the message with current membership status
                channels_text = ""
                buttons = []
                
                for channel_name, is_joined in memberships.items():
                    status = "✅" if is_joined else "❌"
                    channels_text += f"{status} {channel_name}\n"
                    if not is_joined:
                        channel_info = REQUIRED_CHANNELS.get(channel_name)
                        invite_link = channel_info.get("invite_link")
                        buttons.append([InlineKeyboardButton(f"Join {channel_name}", url=invite_link)])
                
                buttons.append([InlineKeyboardButton("🔄 Check Again", callback_data="check_membership")])
                
                await callback_query.message.edit_text(
                    f"⚠️ **Channel Membership Required**\n\n"
                    f"Please join all the following channels to use this bot:\n\n"
                    f"{channels_text}\n"
                    f"After joining, click '🔄 Check Again' button.",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                await callback_query.answer("Please join all channels")
        
        elif data == "back_to_menu":
            # Create the main menu again
            user_mention = callback_query.from_user.mention
            db_premium_status = await is_premium(user_id)
            premium_status = True if is_admin else db_premium_status
            
            reply_message = (
                f"🌟 Welcome to the Ultimate TeraBox Downloader Bot, {user_mention}!\n\n"
                "🚀 **Why Choose This Bot?**\n"
                "- **Unmatched Speed**: Experience the fastest and most powerful TeraBox downloader on Telegram. ⚡\n"
                "- **100% Free Forever**: No hidden fees or subscriptions—completely free for everyone! 🆓\n"
                "- **Seamless Downloads**: Easily download TeraBox files and have them sent directly to you. 🎥📁\n"
                "- **24/7 Availability**: Access the bot anytime, anywhere, without downtime. ⏰\n\n"
                "🎯 **How It Works**\n"
                "Simply send a TeraBox link, and let the bot handle the rest. It's quick, easy, and reliable! 🚀\n\n"
                "💎 **Your Ultimate Telegram Tool**—crafted to make your experience effortless and enjoyable."
            )
            
            # Add buttons based on premium status
            join_button = InlineKeyboardButton("Join Channel ❤️", url=REQUIRED_CHANNELS["sr_robots"]["invite_link"])
            developer_button = InlineKeyboardButton("Developer ⚡️", url="https://t.me/sr_robots")
            profile_button = InlineKeyboardButton("My Profile 👤", callback_data="profile")
            premium_button = InlineKeyboardButton("Premium ⭐", callback_data="premium_info")
            
            buttons = []
            if is_admin:
                admin_button = InlineKeyboardButton("🔰 Admin Panel", callback_data="admin_back")
                buttons.append([join_button, developer_button])
                buttons.append([profile_button])
                buttons.append([admin_button])
            elif premium_status:
                buttons.append([join_button, developer_button])
                buttons.append([profile_button])
            else:
                buttons.append([join_button, developer_button])
                buttons.append([profile_button, premium_button])
            
            await callback_query.message.edit_text(
                reply_message,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await callback_query.answer("Back to main menu")
            
        elif data == "premium_info":
            # Show premium information
            premium_features = (
                "💎 **Premium Membership** 💎\n\n"
                "Upgrade to premium for the ultimate TeraBox download experience!\n\n"
                "✨ **Benefits:**\n"
                "• 🚫 **No Ads or Verification**: Skip all shortlinks and verification steps\n"
                "• ♾️ **Unlimited Downloads**: No download limits ever\n"
                "• ⚡ **Priority Processing**: Faster download speeds\n"
                "• 🔄 **Parallel Downloads**: Download multiple files at once\n"
                "• 🛡️ **Premium Support**: Get priority assistance\n\n"
                "📊 **Pricing Plans (Telegram Stars):**\n"
                "• 1 Month: 25 Stars ⭐\n"
                "• 2 Months: 50 Stars ⭐\n"
                "• Lifetime: 100 Stars ⭐\n\n"
                "Purchase premium via our payment bot to unlock all features instantly!"
            )
            
            # Create buttons for premium purchase
            premium_button = InlineKeyboardButton("Purchase Premium 💎", url="https://t.me/srxpremiumBOT/?start=purchase")
            tutorial_video = InlineKeyboardButton("How to Purchase", url="https://t.me/sr_bots_premium_tutorial")
            contact_button = InlineKeyboardButton("Contact Support 👨‍💻", url="https://t.me/SR_SUPPORTxBOT")
            back_button = InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
            
            await callback_query.message.edit_text(
                premium_features,
                reply_markup=InlineKeyboardMarkup([
                    [premium_button],
                    [tutorial_video],
                    [contact_button],
                    [back_button]
                ])
            )
            await callback_query.answer("Premium information")
            
        elif data.startswith("buy_premium"):
            # Direct user to purchase bot
            await callback_query.message.edit_text(
                "🔄 **Redirecting to payment bot...**\n\n"
                "You'll be redirected to our payment bot to complete your premium purchase using Telegram Stars.\n\n"
                "Please click the button below to proceed:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Go to Payment Bot 💳", url="https://t.me/srxpremiumBOT/?start=purchase")],
                    [InlineKeyboardButton("🔙 Back to Plans", callback_data="premium_info")]
                ])
            )
            await callback_query.answer("Redirecting to payment")
        
    except Exception as e:
        logging.error(f"Error in callback handler: {str(e)}")
        try:
            await callback_query.answer("An error occurred. Please try again.", show_alert=True)
        except:
            pass

@app.on_message(filters.command('broadcast') & filters.user(ADMINS))
async def broadcast_command(client, message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u></b>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code>"""
        
        await pls_wait.edit(status)
    else:
        msg = await message.reply("Please reply to a message to broadcast it.")
        await asyncio.sleep(8)
        await msg.delete()

@app.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_command(client, message):
    try:
        # Get user statistics without await on integers
        total_users = users_collection.count_documents({})
        verified_users = users_collection.count_documents({"verify_status.is_verified": True})
        premium_users = users_collection.count_documents({"premium": True})
        shortlink_verified_users = users_collection.count_documents({"shortlink_verified": True})
        unverified_users = total_users - verified_users - premium_users - shortlink_verified_users
        
        # Bot uptime calculation
        uptime = get_readable_time(time.time() - START_TIME)
        
        # Format detailed statistics
        stats_text = (
            "📊 **Bot Statistics**\n\n"
            "**Users:**\n"
            f"• Total Users: `{total_users}`\n"
            f"• Premium Users: `{premium_users}`\n"
            f"• Verified Users: `{verified_users}`\n"
            f"• Shortlink Verified: `{shortlink_verified_users}`\n"
            f"• Unverified Users: `{unverified_users}`\n\n"
            "**System:**\n"
            f"• Bot Version: `{BOT_VERSION}`\n"
            f"• Uptime: {uptime}\n\n"
            f"**Last Updated:** {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"
        )
        
        # Create buttons
        refresh_button = InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")
        admin_panel_button = InlineKeyboardButton("🔰 Admin Panel", callback_data="admin_back")
        
        await message.reply(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [refresh_button],
                [admin_panel_button]
            ])
        )
    except Exception as e:
        logging.error(f"Error generating statistics: {e}")
        await message.reply(f"❌ Error generating statistics: {str(e)}")

@app.on_message(filters.command("check"))
async def check_command(client, message):
    user_id = message.from_user.id

    verify_status = await db_verify_status(user_id)
    logging.info(f"Verify status for user {user_id}: {verify_status}")

    if verify_status['is_verified']:
        expiry_time = get_exp_time(VERIFY_EXPIRE - (time.time() - verify_status['verified_time']))
        await message.reply(f"✅ Your token has been successfully verified and is valid for {expiry_time}.")
    else:
        await message.reply("❌ Your token is either not verified or has expired. Please use /start to generate a new token and verify it. 🔄...")

async def is_user_member(client, user_id):
    try:
        member = await client.get_chat_member(fsub_id, user_id)
        logging.info(f"User {user_id} membership status: {member.status}")
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking membership status for user {user_id}: {e}")
        return False

def is_terabox_link(link):
    keywords = ["terabox", "terafileshare", "1024tera", "terasharelink", "xnxx"]
    return any(keyword in link.lower() for keyword in keywords)

valid_domains = [
    'terabox.com', 'nephobox.com', '4funbox.com', 'mirrobox.com', 'terabox.link', 
    'momerybox.com', 'teraboxapp.com', 'terafileshare.com', '1024tera.com', 'xnxx', 
    'terabox.app', 'gibibox.com', 'goaibox.com', 'terasharelink.com', 'teraboxlink.com',
    'www.terabox.app', 'terabox.fun', 'www.terabox.com', 'www.1024tera.com', 'teraboxshare.com',
    'www.mirrobox.com', 'www.nephobox.com', 'freeterabox.com', 'www.freeterabox.com', '4funbox.co'
]

def is_valid_domain(link):
    """Check if the link belongs to any valid domain."""
    return any(domain in link for domain in valid_domains)

@app.on_message(filters.text & (~filters.command("start") & ~filters.command("profile") & ~filters.command("help") & ~filters.command("stats") & ~filters.command("check") & ~filters.command("addpremium") & ~filters.command("removepremium") & ~filters.command("premiumlist") & ~filters.command("broadcast") & ~filters.command("premium") & ~filters.command("buy")))
async def handle_message(client, message: Message):
    if message.from_user is None:
        logging.warning("Received a message with no user information.")
        return  # Safely exit the handler if there's no user info

    # Check if message starts with a slash (likely a command)
    if message.text.startswith('/'):
        # This is likely a command but not one we explicitly handle
        if message.from_user.id in ADMINS:
            await message.reply(
                "❌ **Unknown command**\n\n"
                "Use `/help` to see all available admin commands."
            )
        return

    user_id = message.from_user.id
    is_admin = user_id in ADMINS
    
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            logging.error(f"Failed to add user {user_id} to the database: {e}")

    user_mention = message.from_user.mention
    
    # Check for TeraBox links
    links = extract_links(message.text)
    
    if not links:
        # If no links found
        if is_admin:
            await message.reply(
                "❌ **No valid links detected**\n\n"
                "**For admin commands, use:**\n"
                "• `/addpremium user_id months` - Add premium user\n"
                "• `/removepremium user_id` - Remove premium user\n"
                "• `/premiumlist` - List all premium users\n"
                "• `/stats` - Show bot statistics\n"
                "• `/broadcast` - Send message to all users (Reply to a message)"
            )
        else:
            await message.reply("Please send a valid TeraBox link.")
        return

    # Check if the links are valid TeraBox links
    valid_terabox_links = []
    for url in links:
        if is_terabox_link(url):
            valid_terabox_links.append(url)
        else:
            await message.reply(f"⚠️ {url} is not a valid Terabox link.")
    
    if not valid_terabox_links:
        return

    # Get download count and premium status
    download_count = await get_download_count(user_id)
    db_premium_status = await is_premium(user_id)
    
    # Admin is always treated as premium even if not set in DB
    premium_status = True if is_admin else db_premium_status
    shortlink_verified = await is_shortlink_verified(user_id)
    
    # Check channel membership - Admins also need to be members
    memberships = await check_membership(client, user_id)
    all_joined = all(memberships.values())
    
    if not all_joined:
        channels_text = ""
        buttons = []
        
        for channel_name, is_joined in memberships.items():
            if not is_joined:
                channel_info = REQUIRED_CHANNELS.get(channel_name)
                invite_link = channel_info.get("invite_link")
                channels_text += f"• {channel_name}\n"
                buttons.append([InlineKeyboardButton(f"Join {channel_name}", url=invite_link)])
        
        buttons.append([InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")])
        
        await message.reply(
            f"⚠️ **Channel Membership Required**\n\n"
            f"Please join the following channels to use this bot:\n\n"
            f"{channels_text}\n"
            f"After joining, click '✅ Check Membership' button.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    # Free downloads check - Allow first 3 downloads without verification
    has_free_downloads = download_count < FREE_DOWNLOADS
    
    # Check if user is premium or has shortlink verification or has free downloads
    verified = premium_status or shortlink_verified or is_admin or has_free_downloads
    
    # If user is not verified (no free downloads left and not premium/verified)
    if not verified:
        # Generate shortlink verification
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        logging.info(f"Generated token: {token}")
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{BOT_USERNAME}?start=verify_{token}')
        verify_status = await db_verify_status(user_id)
        await db_update_verify_status(user_id, {**verify_status, 'verify_token': token, 'link': link})
        
        free_downloads_used_message = (
            f"🔹 **Free Downloads Used!**\n\n"
            f"You've used all {FREE_DOWNLOADS} free downloads.\n\n"
            "To continue using the bot, you have two options:\n\n"
            "1️⃣ **Verify via Shortlink**\n"
            f"• Get {SHORTLINK_HOURS} hours of access\n"
            "• No limitations during verified period\n\n"
            "2️⃣ **Purchase Premium**\n"
            "• Unlimited downloads forever\n"
            "• No verification required\n"
            "• Priority processing\n\n"
            "Choose an option below to continue:"
        )
        
        verify_button = InlineKeyboardButton("Verify Now 🔗", url=link)
        premium_button = InlineKeyboardButton("Get Premium ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")
        tutorial_button = InlineKeyboardButton("How to Verify 🎥", url=TUT_VID)
        
        await message.reply_text(
            free_downloads_used_message,
            reply_markup=InlineKeyboardMarkup([
                [verify_button],
                [premium_button],
                [tutorial_button]
            ])
        )
        return
    
    # Get verification status
    verify_status = await db_verify_status(user_id)
    
    # Check verification expiration
    if verify_status["is_verified"] and VERIFY_EXPIRE < (time.time() - verify_status["verified_time"]):
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': False})
        verify_status['is_verified'] = False
        logging.info(f"Verification expired for user {user_id}")
        # Don't return here - user might still have free downloads available
    
    # Process TeraBox links one by one
    for terabox_link in valid_terabox_links:
        # Increment download count for non-premium users (admins are premium)
        if not premium_status:
            await increment_download_count(user_id)
        
        # Update download count for display
        download_count = await get_download_count(user_id)
        free_downloads_left = max(0, FREE_DOWNLOADS - download_count)
        
        # Different message for premium vs free users
        if premium_status:
            if is_admin:
                status_text = "🔰 Admin Download"
            else:
                status_text = "🌟 Premium Download"
        elif shortlink_verified:
            user = await get_user(user_id)
            shortlink_expiry = datetime.fromtimestamp(user.get('shortlink_expiry', 0))
            total_seconds_left = max(0, (shortlink_expiry - datetime.now()).total_seconds())
            hours_left = int(total_seconds_left // 3600)
            minutes_left = int((total_seconds_left % 3600) // 60)
            status_text = f"✅ Verified Download ({hours_left}h {minutes_left}m left)"
        else:
            status_text = f"⭐ Free Download ({free_downloads_left} left)"
                
        reply_msg = await message.reply_text(f"🔄 Retrieving your TeraBox video... {status_text}")

        try:
            logging.info(f"Starting download for link: {terabox_link[:30]}...")
            
            # Handle the download carefully to avoid unpacking errors
            result = await download_video(terabox_link, reply_msg, user_mention, user_id)
            
            # Check if the result is None or incomplete
            if result is None or len(result) != 3 or result[0] is None:
                logging.error("Download failed - incomplete or None result returned")
                
                # No need to get direct link here, handle_video_download_failure will do it
                await handle_video_download_failure(terabox_link, reply_msg, Exception("Download failed"))
                continue
                
            # Unpack the result only after verifying it's complete
            file_path, thumbnail_path, video_title = result
                
            logging.info(f"Successfully downloaded video: {video_title}. Starting upload...")
            await upload_video(client, file_path, thumbnail_path, video_title, reply_msg, dump_id, user_mention, user_id, message)
        except Exception as e:
            error_msg = f"Error handling message: {str(e)}"
            logging.error(error_msg)
            if hasattr(e, '__traceback__'):
                tb_str = ''.join(traceback.format_tb(e.__traceback__))
                logging.error(f"Traceback: {tb_str}")
            
            # Use the centralized error handling function from video.py
            await handle_video_download_failure(terabox_link, reply_msg, e)

@app.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium_command(client, message):
    command_text = message.text.strip()
    parts = command_text.split()
    
    # Validate command format
    if len(parts) < 3:
        return await message.reply(
            "❌ **Invalid format!**\n\n"
            "**Usage:**\n"
            "• `/addpremium user_id months`\n\n"
            "**Example:**\n"
            "• `/addpremium 123456789 1`"
        )
    
    try:
        # Extract user_id and months from command
        if '_' in command_text and len(parts) == 1:
            # Format: /addpremium_user_id_months
            cmd_parts = command_text.split('_')
            if len(cmd_parts) != 3:
                return await message.reply("❌ Invalid format. Use `/addpremium user_id months`")
            
            try:
                user_id = int(cmd_parts[1])
                months = int(cmd_parts[2])
            except ValueError:
                return await message.reply("❌ User ID and months must be numbers")
        else:
            # Format: /addpremium user_id months
            try:
                user_id = int(parts[1])
                months = int(parts[2])
            except ValueError:
                return await message.reply("❌ User ID and months must be numbers")
        
        # Validate months
        if months <= 0 or months > 12:
            return await message.reply("❌ Months should be between 1 and 12")
        
        # Add premium to user
        if not await present_user(user_id):
            await add_user(user_id)
            await message.reply(f"ℹ️ User {user_id} was not in database. Created new user.")
        
        # Add premium
        expiry_time = await add_premium(user_id, months)
        expiry_date = datetime.fromtimestamp(expiry_time).strftime("%d %b %Y, %H:%M:%S")
        
        # Send success message to admin
        await message.reply(
            f"✅ **Premium Successfully Added**\n\n"
            f"**User ID:** `{user_id}`\n"
            f"**Duration:** {months} months\n"
            f"**Expires on:** {expiry_date}"
        )
        
        # Send notification to user
        try:
            await client.send_message(
                chat_id=user_id,
                text=f"🎉 **Congratulations!**\n\n"
                     f"Premium access has been activated on your account for {months} months!\n\n"
                     f"✨ You now have unlimited downloads without shortlink verification\n"
                     f"📅 **Expires on:** {expiry_date}\n\n"
                     f"Thank you for supporting our service! ❤️"
            )
        except Exception as e:
            logging.error(f"Failed to send premium notification to user {user_id}: {e}")
            await message.reply(f"⚠️ Premium added but failed to notify user: {e}")
    
    except Exception as e:
        logging.error(f"Failed to add premium to user: {e}")
        await message.reply(f"❌ Failed to add premium: {str(e)}")

@app.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def remove_premium_command(client, message):
    command_text = message.text.strip()
    parts = command_text.split()
    
    # Validate command format
    if len(parts) < 2:
        return await message.reply(
            "❌ **Invalid format!**\n\n"
            "**Usage:**\n"
            "• `/removepremium user_id`\n\n"
            "**Example:**\n"
            "• `/removepremium 123456789`"
        )
    
    try:
        # Extract user_id from command
        if '_' in command_text and len(parts) == 1:
            # Format: /removepremium_user_id
            cmd_parts = command_text.split('_')
            if len(cmd_parts) != 2:
                return await message.reply("❌ Invalid format. Use `/removepremium user_id`")
            
            try:
                user_id = int(cmd_parts[1])
            except ValueError:
                return await message.reply("❌ User ID must be a number")
        else:
            # Format: /removepremium user_id
            try:
                user_id = int(parts[1])
            except ValueError:
                return await message.reply("❌ User ID must be a number")
        
        # Check if user exists and is premium
        if not await present_user(user_id):
            return await message.reply(f"❌ User {user_id} not found in database")
        
        user = await get_user(user_id)
        if not user.get('premium', False):
            return await message.reply(f"❌ User {user_id} is not a premium user")
        
        # Remove premium
        await remove_premium(user_id)
        
        # Send success message to admin
        await message.reply(
            f"✅ **Premium Successfully Removed**\n\n"
            f"**User ID:** `{user_id}`"
        )
        
        # Send notification to user
        try:
            await client.send_message(
                chat_id=user_id,
                text="ℹ️ Your premium access has been removed from your account.\n\n"
                     "You will now need to follow the standard verification process to continue using the bot."
            )
        except Exception as e:
            logging.error(f"Failed to send premium removal notification to user {user_id}: {e}")
            await message.reply(f"⚠️ Premium removed but failed to notify user: {e}")
    
    except Exception as e:
        logging.error(f"Failed to remove premium: {e}")
        await message.reply(f"❌ Failed to remove premium: {str(e)}")

@app.on_message(filters.command("premiumlist") & filters.user(ADMINS))
async def premium_list_command(client, message):
    try:
        processing_msg = await message.reply("🔄 **Fetching premium users...**")
        
        premium_users_list = list(users_collection.find({"premium": True}))
        
        user_count = users_collection.count_documents({"premium": True})
        if user_count == 0:
            await processing_msg.edit_text("❌ No premium users found")
            return
        
        premium_list = "🌟 **Premium Users List**\n\n"
        count = 0
        
        # Use regular for loop instead of async for
        for user in premium_users_list:
            user_id = user['_id']
            premium_expiry = user.get('premium_expiry', 0)
            expiry_date = datetime.fromtimestamp(premium_expiry).strftime("%d %b %Y, %H:%M:%S")
            
            try:
                user_info = await client.get_users(user_id)
                username = user_info.username or "No username"
                name = user_info.first_name
                premium_list += f"{count+1}. **ID:** `{user_id}`\n**Name:** {name}\n**Username:** @{username}\n**Expires:** {expiry_date}\n\n"
            except Exception:
                premium_list += f"{count+1}. **ID:** `{user_id}`\n**Expires:** {expiry_date}\n\n"
            
            count += 1
            
            # Split messages if too long
            if count % 10 == 0 or len(premium_list) > 3500:
                await processing_msg.edit_text(premium_list)
                await asyncio.sleep(1)  # Prevent rate limiting
                premium_list = "🌟 **Premium Users List (Continued)**\n\n"
                processing_msg = await message.reply("Loading more users...")
        
        if premium_list not in ["🌟 **Premium Users List**\n\n", "🌟 **Premium Users List (Continued)**\n\n"]:
            await processing_msg.edit_text(premium_list)
        
        await message.reply(f"✅ **Total Premium Users:** {count}")
    
    except Exception as e:
        error_logger.error(f"Failed to fetch premium users: {e}")
        await message.reply(f"❌ Failed to fetch premium users: {str(e)}")

@app.on_message(filters.command("help") & filters.user(ADMINS))
async def admin_help_command(client, message):
    help_text = (
        "🔰 **Admin Commands**\n\n"
        "• `/start` - Start the bot\n"
        "• `/profile` - View your profile\n"
        "• `/stats` - Show bot statistics\n"
        "• `/check` - Check verification status\n\n"
        "**Premium Management:**\n"
        "• `/addpremium <user_id> <months>` - Add premium to a user\n"
        "• `/removepremium <user_id>` - Remove premium from a user\n"
        "• `/premiumlist` - List all premium users\n\n"
        "**Broadcasting:**\n"
        "• `/broadcast` - Send message to all users (Reply to a message)\n\n"
        "**Bot Version:** " + BOT_VERSION
    )
    
    await message.reply(help_text)

@app.on_message(filters.command("premium"))
async def premium_command(client, message):
    """Handle the premium command to provide premium information"""
    try:
        user_id = message.from_user.id
        
        if not await present_user(user_id):
            try:
                await add_user(user_id)
                logger.info(f"Added user {user_id} to the database from premium command")
            except Exception as e:
                error_logger.error(f"Failed to add user {user_id} to the database: {e}")

        db_premium_status = await is_premium(user_id)
        premium_status = user_id in ADMINS or db_premium_status
        
        if premium_status:
            if user_id in ADMINS:
                await message.reply("✨ **You are an admin** with unlimited access to all premium features!")
            else:
                user = await get_user(user_id)
                premium_expiry = datetime.fromtimestamp(user.get('premium_expiry', 0))

                days_left = (premium_expiry - datetime.now()).days
                hours_left = int(((premium_expiry - datetime.now()).total_seconds() % 86400) // 3600)
                
                exact_expiry = premium_expiry.strftime("%d %b %Y, %H:%M:%S")
                
                await message.reply(
                    f"🌟 **You are a Premium User!** 🌟\n\n"
                    f"📅 **Expiry Date:** {exact_expiry}\n"
                    f"⏱️ **Time Remaining:** {days_left} days, {hours_left} hours\n\n"
                    f"Enjoy your unlimited downloads without ads or verification!\n\n"
                    f"Need help? Contact our support."
                )
        else:
            # User is not premium, show premium info
            premium_features = (
                "💎 **Premium Membership** 💎\n\n"
                "Upgrade to premium for the ultimate TeraBox download experience!\n\n"
                "✨ **Benefits:**\n"
                "• 🚫 **No Ads or Verification**: Skip all shortlinks and verification steps\n"
                "• ♾️ **Unlimited Downloads**: No download limits ever\n"
                "• ⚡ **Priority Processing**: Faster download speeds\n"
                "• 🔄 **Parallel Downloads**: Download multiple files at once\n"
                "• 🛡️ **Premium Support**: Get priority assistance\n\n"
                "📊 **Pricing Plans (Telegram Stars):**\n"
                "• 1 Month: 25 Stars ⭐\n"
                "• 2 Months: 50 Stars ⭐\n"
                "• 3 Months: 100 Stars ⭐\n\n"
                "Purchase premium via our payment bot to unlock all features instantly!"
            )
            
            # Create buttons with direct links to purchase options
            purchase_month = InlineKeyboardButton("Purchase ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")
            tutorial_video = InlineKeyboardButton("How to purchase", url="https://t.me/sr_bots_premium_tutorial")
            contact_button = InlineKeyboardButton("Contact Support 👨‍💻", url="https://t.me/SR_SUPPORTxBOT")
            
            markup = InlineKeyboardMarkup([
                [purchase_month],
                [tutorial_video],
                [contact_button]
            ])
            
            await message.reply(premium_features, reply_markup=markup)
    except Exception as e:
        error_msg = log_error("Error in premium command", e, {"user_id": message.from_user.id if message.from_user else "Unknown"})
        try:
            await message.reply("Sorry, something went wrong while processing your request. Please try again later.")
        except:
            pass

# Add error handling for common Pyrogram exceptions
async def safe_edit_message_text(message, text, reply_markup=None):
    """Safely edit a message with proper error handling"""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except MessageNotModified:
        # Message content was not modified, this is fine
        pass
    except FloodWait as e:
        logging.warning(f"FloodWait encountered: {e.x} seconds")
        await asyncio.sleep(e.x)
        await safe_edit_message_text(message, text, reply_markup)
    except Exception as e:
        logging.error(f"Error editing message: {e}")

# Add the buy command before any other command handlers
async def buy_command(client, message):
    """Handle the /buy command, providing information about purchasing premium access"""
    # Get user information
    user_id = message.from_user.id
    user_mention = f"[{message.from_user.first_name}](tg://user?id={user_id})"

    is_premium_user = await is_premium(user_id)
    
    if is_premium_user:
        user_data = await get_user(user_id)
        premium_expiry = datetime.fromtimestamp(user_data.get('premium_expiry', 0))
        
        remaining_time = premium_expiry - datetime.now()
        days = remaining_time.days
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        expiry_date_str = premium_expiry.strftime("%d %b %Y at %H:%M UTC")
        
        await message.reply(
            f"✨ **You're Already Premium!** ✨\n\n"
            f"Thank you for being a valued premium member, {user_mention}!\n\n"
            f"📆 Your subscription expires on: **{expiry_date_str}**\n"
            f"⏳ Time remaining: **{days}d {hours}h {minutes}m**\n\n"
            f"If you wish to extend your subscription, please purchase additional premium time.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Extend Premium ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")]
            ])
        )
        return
    
    # User is not premium, show pricing and payment information
    pricing_text = (
        f"💎 **Premium Subscription Plans** 💎\n\n"
        f"Upgrade to premium and enjoy:\n\n"
        f"✅ **Unlimited downloads**\n"
        f"✅ **No verification required**\n"
        f"✅ **Priority support**\n"
        f"✅ **Full speed downloads**\n"
        f"✅ **No queue waiting**\n\n"
        f"**Choose Your Plan (Telegram Stars):**\n\n"
        f"⭐ **1 Month**: 25 Stars\n"
        f"⭐ **2 Months**: 50 Stars \n"
        f"⭐ **Lifetime**: 100 Stars \n\n"
        f"To purchase, select a plan below:"
    )
    
    buttons = [
        [
            InlineKeyboardButton("Purchase ⭐", url="https://t.me/srxpremiumBOT/?start=purchase")
        ],        
        [
            InlineKeyboardButton("How to purchase", url="https://t.me/sr_bots_premium_tutorial")
        ],
        [
            InlineKeyboardButton("📞 Contact Support", url="https://t.me/SR_SUPPORTxBOT"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
        ]
    ]
    
    await message.reply(pricing_text, reply_markup=InlineKeyboardMarkup(buttons))

if __name__ == "__main__":
    try:
        logger.info(f"Starting TeraBox Downloader Bot v{BOT_VERSION}...")
        logger.info(f"Bot is being run by admins: {ADMINS}")
        
        # Register additional commands
        app.add_handler(pyrogram.handlers.MessageHandler(buy_command, filters.command("buy")))
        
        keep_alive()
        # Properly handle graceful shutdown for Pyrogram
        app.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        exit(0)
    except Exception as e:
        log_error("CRITICAL: Bot startup failed", e, additional_info={
            "version": BOT_VERSION,
            "admins": ADMINS
        })
        exit(1)

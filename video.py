import requests
import aria2p
from datetime import datetime
from status import format_progress_bar
import asyncio
import os
import time
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from requests.exceptions import RequestException
import aiofiles
from typing import Tuple, Optional, Dict, Any
import traceback
import json
from pyrogram.errors import MessageNotModified

# Aria2 configuration with error handling
try:
    aria2 = aria2p.API(
        aria2p.Client(
            host="http://localhost",
            port=6800,
            secret=""
        )
    )
except Exception as e:
    logging.error(f"Failed to initialize aria2p: {e}")
    raise SystemExit("Aria2 initialization failed")

options = {
    "max-tries": "50",
    "retry-wait": "3",
    "continue": "true",
    "max-concurrent-downloads": "5",
    "split": "5",
    "max-connection-per-server": "16",
    "min-split-size": "10M"
}

aria2.set_global_options(options)

async def get_direct_link(url: str) -> Optional[Dict[str, Any]]:
    """Try multiple APIs to get a direct download link for a TeraBox URL.
    
    Returns a dictionary with direct_link, thumb, and file_name if successful, None otherwise.
    """
    apis_to_try = [
        f"https://ashlynn.serv00.net/techcodertera.php?url={url}",
        f"https://terabox-pika.vercel.app/?url={url}"
    ]
    
    for api_url in apis_to_try:
        try:
            logging.info(f"Trying API: {api_url}")
            response = requests.get(api_url, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Check if we got a valid direct link
            if "direct_link" in data and data["direct_link"]:
                return {
                    "direct_link": data["direct_link"],
                    "thumb": data.get("thumb"),
                    "file_name": data.get("file_name")
                }
        except Exception as e:
            logging.warning(f"API {api_url} failed: {str(e)}")
            continue
    
    return None

async def download_video(url: str, reply_msg, user_mention: str, user_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    MAX_RETRIES = 3
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            await reply_msg.edit_text("🔍 **Analyzing TeraBox link...**")
            
            # Get direct download link using our helper function
            api_data = await get_direct_link(url)
            
            if not api_data or not api_data.get("direct_link"):
                raise ValueError("No direct download link found")

            fast_download_link = api_data["direct_link"]
            thumbnail_url = api_data.get("thumb")
            video_title = api_data.get("file_name", f"video_{user_id}_{int(time.time())}")
            
            await reply_msg.edit_text(f"🔍 Found: {video_title}\n\n⏳ Starting download...")
            
            # Use Aria2 for downloading instead of direct requests
            local_filename = f"temp_{user_id}_{int(time.time())}.mp4"
            
            # Setup download options
            download_options = {
                "out": local_filename,
                "header": [
                    f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    f"Referer: https://www.terabox.com/",
                    f"Accept: */*",
                    f"Accept-Encoding: gzip, deflate, br",
                    f"Connection: keep-alive"
                ]
            }
            
            # Add download to Aria2
            download = aria2.add_uris([fast_download_link], options=download_options)
            download_id = download.gid
            
            logging.info(f"Download started with aria2 (GID: {download_id})")
            
            # Monitor download progress
            start_time = datetime.now()
            last_update_time = time.time()
            
            while True:
                download = aria2.get_download(download_id)
                if download.is_complete:
                    await reply_msg.edit_text(f"✅ **Download Complete!**\n\n**File:** {video_title}\n\n🔄 Preparing to upload...")
                    break
                elif download.has_failed:
                    error_msg = f"Aria2 download failed with status: {download.status}"
                    logging.error(error_msg)
                    raise RuntimeError(error_msg)
                
                # Update progress every 2 seconds
                if time.time() - last_update_time > 2:
                    last_update_time = time.time()
                    
                    # Calculate progress
                    downloaded = download.completed_length
                    total_size = download.total_length
                    
                    if total_size > 0:
                        percentage = (downloaded / total_size) * 100
                        elapsed_time = (datetime.now() - start_time).total_seconds()
                        speed = download.download_speed
                        eta = ((total_size - downloaded) / speed) if speed > 0 else 0
                        
                        progress_text = (
                            f"⬇️ **Downloading:** {video_title}\n\n"
                            f"{format_progress_bar(percentage=percentage, done=downloaded, total_size=total_size)}\n\n"
                            f"🔄 **Progress:** {percentage:.1f}%\n"
                            f"⚡ **Speed:** {humanbytes(speed)}/s\n"
                            f"⏳ **Time Left:** {format_time(eta)}\n"
                            f"👤 **User:** {user_mention}"
                        )
                        
                        try:
                            await reply_msg.edit_text(progress_text)
                        except Exception as e:
                            logging.warning(f"Failed to update progress: {e}")
                
                # Small sleep to prevent CPU hogging
                await asyncio.sleep(1)
            
            # Verify the file exists and has content
            if os.path.exists(local_filename) and os.path.getsize(local_filename) > 1024:  # At least 1KB
                # Get fresh thumbnail each time
                thumbnail_path = await _download_thumbnail(thumbnail_url)
                return local_filename, thumbnail_path, video_title
            else:
                # File is missing or empty
                if os.path.exists(local_filename):
                    os.remove(local_filename)  # Clean up empty file
                raise ValueError(f"Downloaded file is empty or missing: {local_filename}")

        except (RequestException, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logging.error(f"Download attempt {retry_count+1} failed: {str(e)}")
            
            retry_count += 1
            if retry_count < MAX_RETRIES:
                retry_wait = 2 ** retry_count  # Exponential backoff
                # Show a generic message to the user without API details
                user_message = f"⚠️ **Processing your link...**\n\nAttempt {retry_count}/{MAX_RETRIES}\nRetrying with different method in {retry_wait} seconds..."
                await reply_msg.edit_text(user_message)
                await asyncio.sleep(retry_wait)
            else:
                logging.error(f"All download attempts failed: {str(e)}")
                # Handle the failure properly
                await handle_video_download_failure(url, reply_msg, e)
                return None, None, None

    # If we get here, all retries failed
    return None, None, None

async def _download_thumbnail(thumbnail_url: str) -> str:
    thumbnail_path = f"thumbnail_{int(time.time())}.jpg"
    try:
        # Fresh download every time
        response = requests.get(thumbnail_url, timeout=5)
        response.raise_for_status()
        with open(thumbnail_path, "wb") as thumb_file:
            thumb_file.write(response.content)
        return thumbnail_path
    except Exception as e:
        logging.warning(f"Thumbnail download failed: {e}")
        return "default_thumbnail.jpg"

async def handle_video_download_failure(url: str, reply_msg, error: Exception) -> Tuple[None, None, None]:
    """Handle failure of video download with user-friendly options.
    This function is made public so it can be called from terabox.py as well.
    """
    logging.error(f"Download failed after retries: {error}")
    
    # Create a more helpful message with multiple fallback options
    try:
        # First check if the message still exists and is editable
        try:
            # Try to get the message to see if it exists
            await reply_msg.get_chat()
        except Exception:
            # Message might be deleted or not accessible anymore
            logging.warning("Can't access the message for download failure update")
            return None, None, None
        
        current_text = reply_msg.text if hasattr(reply_msg, 'text') else ""
        
        # Only update if the message doesn't already indicate failure
        if "Failed to download" not in current_text:
            failure_message = "❌ **Download Failed**\n\n"
            failure_message += "We couldn't download this file at the moment due to one of these reasons:\n\n"
            failure_message += "• The file might be too large for our servers\n"
            failure_message += "• TeraBox server might be temporarily unavailable\n"
            failure_message += "• The file might be protected or restricted\n"
            
            # Create button row for options
            buttons = []
            
            # Get fresh direct link for this specific failure
            direct_link = None
            api_data = await get_direct_link(url)
            if api_data and api_data.get("direct_link"):
                direct_link = api_data["direct_link"]
                buttons.append([InlineKeyboardButton("📥 Direct Download", url=direct_link)])
                failure_message += "\n\n⬇️ You can try the direct download link."
            
            # Add watch online options
            buttons.append([InlineKeyboardButton("🌐 Watch Online", web_app=WebAppInfo(url=f"https://terabox-watch.netlify.app/?url={url}"))])
            buttons.append([InlineKeyboardButton("🌐 Alternative Viewer", web_app=WebAppInfo(url=f"https://terabox-watch.netlify.app/api2.html?url={url}"))])
            
            # Add retry button
            buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data=f"retry_{url}")])
            
            # Add contact support
            buttons.append([InlineKeyboardButton("📱 Contact Support", url="https://t.me/sr_supportxbot")])
            
            # Create keyboard
            keyboard = InlineKeyboardMarkup(buttons)
            
            try:
                await reply_msg.edit_text(
                    failure_message,
                    reply_markup=keyboard
                )
            except MessageNotModified:
                # Message content is already the same
                logging.warning("Message not modified during download failure handling - content already the same")
            except Exception as e:
                logging.error(f"Error updating failure message with keyboard: {e}")
                # Try simpler message without fancy formatting
                try:
                    await reply_msg.edit_text("❌ **Download Failed** - Please try again later.")
                except Exception:
                    pass
    except Exception as e:
        logging.error(f"Error in handle_video_download_failure: {e}")
        if hasattr(e, '__traceback__'):
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logging.error(f"Traceback: {tb_str}")
                
    # Return a proper none tuple to avoid unpacking errors
    return None, None, None

# Rename the function to make it public
_handle_download_failure = handle_video_download_failure

async def upload_video(client, file_path: str, thumbnail_path: str, video_title: str, 
                     reply_msg, collection_channel_id: int, user_mention: str, 
                     user_id: int, message) -> Optional[int]:
    if not os.path.exists(file_path):
        logging.error(f"Downloaded file not found at path: {file_path}")
        await reply_msg.edit_text("❌ **Error:** Downloaded file not found")
        return None

    file_size = os.path.getsize(file_path)
    logging.info(f"Starting upload of file {file_path} ({humanbytes(file_size)})")
    
    uploaded = 0
    start_time = datetime.now()
    last_update_time = time.time()

    async def progress(current: int, total: int):
        nonlocal uploaded, last_update_time
        uploaded = current
        percentage = (current / total) * 100
        elapsed_time_seconds = (datetime.now() - start_time).total_seconds()
        
        if time.time() - last_update_time > 2:
            eta = ((total - current) / current) * elapsed_time_seconds if current > 0 else 0
            speed = current / elapsed_time_seconds if elapsed_time_seconds > 0 else 0
            
            progress_text = (
                f"⬆️ **Uploading:** {video_title}\n\n"
                f"{format_progress_bar(percentage=percentage, done=current, total_size=total)}\n\n"
                f"🔄 **Progress:** {percentage:.1f}%\n"
                f"⚡ **Speed:** {humanbytes(speed)}/s\n"
                f"⏳ **Time Left:** {format_time(eta)}\n"
                f"👤 **User:** {user_mention}"
            )
            try:
                await reply_msg.edit_text(progress_text)
                last_update_time = time.time()
            except Exception as e:
                logging.warning(f"Error updating progress message: {e}")

    try:
        # Use file path directly instead of file object
        await reply_msg.edit_text(f"⬆️ **Uploading:** {video_title}\n\n⏳ Getting ready...")
        
        logging.info(f"Starting upload to chat ID: {message.chat.id}")
        
        # Simplified caption without repository mention
        caption = f"✨ **{video_title}**\n\n🎬 **Downloaded by:** {user_mention}\n📱 **User ID:** [Click here](tg://user?id={user_id})"
        
        collection_message = await client.send_video(
            chat_id=message.chat.id,
            video=file_path,  # Pass the file path as a string
            caption=caption,
            thumb=thumbnail_path,
            progress=progress,
            supports_streaming=True
        )
        logging.info(f"Successfully uploaded video to chat: {message.chat.id}")
        
        # Try to copy the message to collection channels with error handling
        try:
            # Use provided collection_channel_id instead of hardcoded
            if collection_channel_id:
                await client.copy_message(collection_channel_id, message.chat.id, collection_message.id)
                logging.info(f"Message copied to collection channel {collection_channel_id}")
            
            # Admin personal collection - only try if valid
            admin_personal_id = 7427294551  # Can be set through env var
            try:
                await client.copy_message(admin_personal_id, message.chat.id, collection_message.id)
                logging.info(f"Message copied to admin personal channel {admin_personal_id}")
            except Exception as e:
                logging.warning(f"Could not copy message to admin personal channel: {e}")
        except Exception as e:
            logging.error(f"Failed to copy message to collection channels: {e}")
            # Continue execution - don't fail the upload if we can't copy

        await reply_msg.edit_text("✅ **Upload Complete!**\n\n🎬 Your file has been uploaded successfully.")
        
        # Cleanup sequence
        try:
            sticker_message = await message.reply_sticker("CAACAgUAAxkBAAKOW2dSTurhAaxNSg0ecfPNgAK4BwACv1KpVJ4tCBs")
            await asyncio.sleep(2)
            
            await asyncio.gather(
                reply_msg.delete(),
                sticker_message.delete()
            )
        except Exception as e:
            logging.warning(f"Failed in cleanup sequence: {e}")

        # Don't delete the original message to preserve the thread
        delete_file(file_path, "video")
        delete_file(thumbnail_path, "thumbnail")
        
        return collection_message.id
    except Exception as e:
        error_type = type(e).__name__
        error_details = str(e)
        error_traceback = traceback.format_exc()
        
        # Log full error details 
        logging.error(f"Upload failed - Type: {error_type}, Details: {error_details}")
        logging.error(f"Traceback: {error_traceback}")
        
        # Show simplified error to user
        user_msg = "❌ **Upload Failed**\n\nThe server couldn't process your file. This might be due to:"
        user_msg += "\n• File size exceeding limits"
        user_msg += "\n• Temporary server issue"
        user_msg += "\n• Unsupported file format"
        user_msg += "\n\nPlease try again later or contact support."
        
        await reply_msg.edit_text(user_msg)
        return None

def humanbytes(size):
    """Convert bytes to human readable format"""
    if not size:
        return "0B"
    # Define byte units with emoji
    units = [(1<<50, "PiB"), (1<<40, "TiB"), (1<<30, "GiB"), (1<<20, "MiB"), (1<<10, "KiB"), (1, "B")]
    for factor, suffix in units:
        if size >= factor:
            return f"{size/factor:.2f} {suffix}"
    return "0B"

def format_progress_bar(percentage=0, done=0, total_size=0, barsize=18):
    """Create a fancy progress bar with emojis"""
    if percentage > 100:
        percentage = 100
    elif percentage < 0:
        percentage = 0
        
    filled_size = int(barsize * percentage / 100)
    bar = '█' * filled_size + '░' * (barsize - filled_size)
    done_str = humanbytes(done)
    total_str = humanbytes(total_size)
    
    return f"[{bar}] {done_str}/{total_str}"

def format_time(seconds):
    """Format seconds into human readable time"""
    if not seconds or seconds < 0:
        return "calculating..."
    
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    else:
        return f"{seconds//3600}h {(seconds%3600)//60}m"

def delete_file(file_path: str, file_type: str) -> None:
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"✓ Deleted {file_type} file: {file_path}")
                break
        except Exception as e:
            logging.error(f"❌ Attempt {attempt + 1} to delete {file_type} file failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
            else:
                logging.error(f"❌ Failed to delete {file_type} file after {MAX_RETRIES} attempts: {file_path}")

# Verification Admin Panel - Manage verification system
# Created for AnihubFilter Bot

import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_chats_db import db
from info import ADMINS
from utils import temp

logger = logging.getLogger(__name__)

# Temp storage for pending inputs
PENDING_INPUTS = {}

# ==================== VERIFY PANEL COMMAND ====================
# Using group=-1 to ensure this runs before other handlers
@Client.on_message(filters.command("verify_panel") & filters.private, group=-1)
async def verify_panel_cmd(client, message):
    """Admin command to open verification management panel"""
    user_id = message.from_user.id
    logger.info(f"verify_panel command received from user {user_id}")
    
    if user_id not in ADMINS:
        return await message.reply("⛔ This command is only for admins!")
    
    try:
        await send_verify_panel(client, message)
    except Exception as e:
        logger.error(f"Error in verify_panel: {e}")
        await message.reply(f"❌ Error: {e}")
    
    # Stop propagation to other handlers
    message.stop_propagation()


async def send_verify_panel(client, message, edit=False):
    """Send or edit the verification panel"""
    try:
        # Get current settings
        settings = await db.get_verify_settings()
        verified_count = await db.get_verified_users_count()
        
        status = "✅ ON" if settings.get('enabled', False) else "❌ OFF"
        shortlink_url = settings.get('shortlink_url', 'Not Set') or 'Not Set'
        shortlink_api = settings.get('shortlink_api', 'Not Set') or 'Not Set'
        # Get validity in seconds (default 24 hours = 86400 seconds)
        validity_seconds = settings.get('validity_seconds')
        if validity_seconds is None:
            validity_hours = settings.get('validity_hours', 24)
            validity_seconds = validity_hours * 3600
        
        # Convert to human-readable format
        if validity_seconds >= 3600 and validity_seconds % 3600 == 0:
            validity_value = validity_seconds // 3600
            validity_unit = "Hours"
        elif validity_seconds >= 60 and validity_seconds % 60 == 0:
            validity_value = validity_seconds // 60
            validity_unit = "Minutes"
        else:
            validity_value = validity_seconds
            validity_unit = "Seconds"
        
        # Mask API key for security
        if shortlink_api and shortlink_api != 'Not Set':
            masked_api = shortlink_api[:8] + "..." + shortlink_api[-4:] if len(shortlink_api) > 12 else "****"
        else:
            masked_api = 'Not Set'
        
        pm_search_status = "✅ ON" if settings.get('pm_search', True) else "❌ OFF"
        
        text = f"""<b>🔐 Verification Admin Panel</b>

━━━━━━━━━━━━━━━━━━━━

<b>📊 Status:</b> {status}
<b>👥 Verified Users:</b> {verified_count}
<b>⏰ Validity:</b> <code>{validity_value} {validity_unit}</code>
<b>🔗 Shortlink URL:</b> <code>{shortlink_url}</code>
<b>🔑 Shortlink API:</b> <code>{masked_api}</code>
<b>🔍 PM Search:</b> {pm_search_status}

━━━━━━━━━━━━━━━━━━━━

<i>Use the buttons below to manage verification:</i>"""

        buttons = [
            [
                InlineKeyboardButton("✅ Turn ON" if not settings.get('enabled', False) else "❌ Turn OFF", 
                                   callback_data="vp_toggle")
            ],
            [
                InlineKeyboardButton("👥 View Users", callback_data="vp_users_0"),
                InlineKeyboardButton("⏰ Set Validity", callback_data="vp_validity_menu")
            ],
            [
                InlineKeyboardButton("🔗 Set Shortlink", callback_data="vp_shortlink"),
                InlineKeyboardButton("🔑 Set API", callback_data="vp_api")
            ],
            [
                InlineKeyboardButton(f"🔍 PM Search: {'ON' if settings.get('pm_search', True) else 'OFF'}", 
                                   callback_data="vp_pm_search")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="vp_refresh"),
                InlineKeyboardButton("❌ Close", callback_data="close_data")
            ]
        ]
        
        if edit:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error sending verify panel: {e}")
        raise e


# ==================== TEXT INPUT HANDLER ====================
# List of all known commands to exclude from text input handling
KNOWN_COMMANDS = [
    "start", "help", "verify_panel", "index", "setskip", "broadcast", "grp_broadcast",
    "connect", "disconnect", "connections", "stream", "rename", "view_thumb", "del_thumb",
    "set_thumb", "set_caption", "del_caption", "see_caption", "font", "settings", "channel_info",
    "log", "delete", "delete_all", "template", "requests", "msg", "deletefiles", "shortlink",
    "setshortlinkon", "setshortlinkoff", "showshortlink", "settutorial", "removetutorial",
    "nofsub", "fsub", "give_premium", "remove_premium", "plans", "mplans", "total_requests",
    "purge_requests", "stats", "leave", "disable", "enable", "ban", "unban", "users", "chats",
    "invite", "link", "plink", "batch", "pbatch", "filter", "add", "viewfilters", "filters",
    "del", "delall", "gfilter", "addg", "viewgfilters", "gfilters", "delg", "delallg", "id",
    "info", "imdb", "search", "clone", "repo", "song", "mp3", "video", "mp4", "tts", "telegraph",
    "stickerid", "share_text", "share", "sharetext", "tgpaste", "pasty", "paste", "genpassword",
    "genpw", "openai", "lyrics", "json", "js", "written", "ae", "throw", "dart", "roll", "dice",
    "slot", "cancel"
]

@Client.on_message(filters.private & filters.text & ~filters.command(KNOWN_COMMANDS), group=-1)
async def handle_verify_input(client, message):
    """Handle text input for verification settings"""
    user_id = message.from_user.id
    if user_id not in PENDING_INPUTS:
        return  # Let other handlers process this

    
    pending = PENDING_INPUTS.pop(user_id)
    input_type = pending.get('type')
    
    if message.text.lower() == "/cancel":
        await message.reply("❌ Cancelled!")
        message.stop_propagation()
        return
    
    try:
        settings = await db.get_verify_settings()
        
        if input_type == "shortlink_url":
            settings['shortlink_url'] = message.text.strip()
            await db.update_verify_settings(settings)
            await message.reply(f"✅ Shortlink URL set to: <code>{message.text.strip()}</code>", parse_mode=enums.ParseMode.HTML)
        
        elif input_type == "shortlink_api":
            settings['shortlink_api'] = message.text.strip()
            await db.update_verify_settings(settings)
            await message.reply("✅ Shortlink API key saved successfully!")
        
        elif input_type == "validity_hours":
            try:
                hours = int(message.text.strip())
                if hours < 1 or hours > 720:
                    await message.reply("❌ Please enter a number between 1 and 720 hours!")
                    return
                # Convert hours to seconds
                validity_seconds = hours * 3600
                settings['validity_seconds'] = validity_seconds
                # Keep backward compatibility
                settings['validity_hours'] = hours
                await db.update_verify_settings(settings)
                await message.reply(f"✅ Verification validity set to <code>{hours} Hours</code>!", parse_mode=enums.ParseMode.HTML)
            except ValueError:
                await message.reply("❌ Please enter a valid number!")
        
        elif input_type == "validity_minutes":
            try:
                minutes = int(message.text.strip())
                if minutes < 1 or minutes > 43200:  # Max 30 days in minutes
                    await message.reply("❌ Please enter a number between 1 and 43200 minutes!")
                    return
                # Convert minutes to seconds
                validity_seconds = minutes * 60
                settings['validity_seconds'] = validity_seconds
                await db.update_verify_settings(settings)
                await message.reply(f"✅ Verification validity set to <code>{minutes} Minutes</code>!", parse_mode=enums.ParseMode.HTML)
            except ValueError:
                await message.reply("❌ Please enter a valid number!")
        
        elif input_type == "validity_seconds":
            try:
                seconds = int(message.text.strip())
                if seconds < 1 or seconds > 2592000:  # Max 30 days in seconds
                    await message.reply("❌ Please enter a number between 1 and 2592000 seconds!")
                    return
                settings['validity_seconds'] = seconds
                await db.update_verify_settings(settings)
                await message.reply(f"✅ Verification validity set to <code>{seconds} Seconds</code>!", parse_mode=enums.ParseMode.HTML)
            except ValueError:
                await message.reply("❌ Please enter a valid number!")
        
        message.stop_propagation()
    except Exception as e:
        logger.error(f"Error handling verify input: {e}")
        await message.reply(f"❌ Error: {e}")


# ==================== CALLBACK HANDLERS ====================
@Client.on_callback_query(filters.regex(r"^vp_"))
async def verify_panel_callback(client, query: CallbackQuery):
    """Handle verification panel callbacks"""
    if query.from_user.id not in ADMINS:
        return await query.answer("⛔ Only admins can use this!", show_alert=True)
    
    data = query.data
    
    try:
        # Toggle verification ON/OFF
        if data == "vp_toggle":
            settings = await db.get_verify_settings()
            new_status = not settings.get('enabled', False)
            settings['enabled'] = new_status
            await db.update_verify_settings(settings)
            
            status_text = "ON ✅" if new_status else "OFF ❌"
            await query.answer(f"Verification is now {status_text}", show_alert=True)
            await send_verify_panel(client, query.message, edit=True)
        
        # Refresh panel
        elif data == "vp_refresh":
            await send_verify_panel(client, query.message, edit=True)
            await query.answer("🔄 Refreshed!")
        
        # View verified users (with pagination)
        elif data.startswith("vp_users_"):
            page = int(data.split("_")[2])
            await show_verified_users(query, page)
        
        # Set shortlink URL prompt
        elif data == "vp_shortlink":
            PENDING_INPUTS[query.from_user.id] = {'type': 'shortlink_url'}
            text = """<b>🔗 Set Shortlink URL</b>

Send the shortlink domain (without https://)

<b>Example:</b> <code>atglinks.com</code>

Send /cancel to cancel."""
            
            await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
            await query.answer("📝 Send the shortlink URL now...")
        
        # Set API key prompt
        elif data == "vp_api":
            PENDING_INPUTS[query.from_user.id] = {'type': 'shortlink_api'}
            text = """<b>🔑 Set Shortlink API Key</b>

Send your shortlink API key.

Send /cancel to cancel."""
            
            await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
            await query.answer("📝 Send the API key now...")
        
        # Show validity time unit menu
        elif data == "vp_validity_menu":
            text = """<b>⏰ Set Verification Validity</b>

━━━━━━━━━━━━━━━━━━━━

Choose the time unit you want to use:

<b>⏱️ Hours</b> - For long-term validity (e.g., 1, 3, 24)
<b>⏱️ Minutes</b> - For medium-term validity (e.g., 30, 60, 120)
<b>⏱️ Seconds</b> - For short-term validity (e.g., 60, 300, 600)"""
            
            buttons = [
                [InlineKeyboardButton("⏰ Hours", callback_data="vp_validity_hours")],
                [InlineKeyboardButton("⏱️ Minutes", callback_data="vp_validity_minutes")],
                [InlineKeyboardButton("⏲️ Seconds", callback_data="vp_validity_seconds")],
                [InlineKeyboardButton("⬅️ Back", callback_data="vp_back")]
            ]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
            await query.answer()
        
        # Set validity in hours
        elif data == "vp_validity_hours":
            PENDING_INPUTS[query.from_user.id] = {'type': 'validity_hours'}
            text = """<b>⏰ Set Verification Validity (Hours)</b>

Send the number of hours (1-720)

<b>Examples:</b>
• <code>1</code> - 1 Hour
• <code>3</code> - 3 Hours
• <code>24</code> - 24 Hours
• <code>72</code> - 3 Days

Send /cancel to cancel."""
            
            await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
            await query.answer("📝 Send the validity hours now...")
        
        # Set validity in minutes
        elif data == "vp_validity_minutes":
            PENDING_INPUTS[query.from_user.id] = {'type': 'validity_minutes'}
            text = """<b>⏱️ Set Verification Validity (Minutes)</b>

Send the number of minutes (1-43200)

<b>Examples:</b>
• <code>30</code> - 30 Minutes
• <code>60</code> - 1 Hour
• <code>180</code> - 3 Hours
• <code>1440</code> - 1 Day

Send /cancel to cancel."""
            
            await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
            await query.answer("📝 Send the validity minutes now...")
        
        # Set validity in seconds
        elif data == "vp_validity_seconds":
            PENDING_INPUTS[query.from_user.id] = {'type': 'validity_seconds'}
            text = """<b>⏲️ Set Verification Validity (Seconds)</b>

Send the number of seconds (1-2592000)

<b>Examples:</b>
• <code>60</code> - 1 Minute
• <code>300</code> - 5 Minutes
• <code>3600</code> - 1 Hour
• <code>86400</code> - 1 Day

Send /cancel to cancel."""
            
            await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
            await query.answer("📝 Send the validity seconds now...")
        
        # Toggle PM Search ON/OFF
        elif data == "vp_pm_search":
            settings = await db.get_verify_settings()
            new_status = not settings.get('pm_search', True)
            settings['pm_search'] = new_status
            await db.update_verify_settings(settings)
            
            status_text = "ON ✅" if new_status else "OFF ❌"
            await query.answer(f"PM Search is now {status_text}", show_alert=True)
            await send_verify_panel(client, query.message, edit=True)
        
        # Revoke user verification
        elif data.startswith("vp_revoke_"):
            user_id = int(data.split("_")[2])
            await db.revoke_user_verification(user_id)
            await query.answer(f"✅ Revoked verification for user {user_id}", show_alert=True)
            await show_verified_users(query, 0)
        
        # Back to panel
        elif data == "vp_back":
            await send_verify_panel(client, query.message, edit=True)
        
        # Catch unhandled vp_ callbacks
        else:
            await query.answer(f"Unknown action: {data}", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in verify callback: {e}")
        await query.answer(f"Error: {e}", show_alert=True)


async def show_verified_users(query, page):
    """Show verified users with pagination"""
    try:
        users_cursor = await db.get_all_verified_users()
        users = [user async for user in users_cursor]
        
        # Get validity settings
        verify_settings = await db.get_verify_settings()
        validity_seconds = verify_settings.get('validity_seconds')
        if validity_seconds is None:
            validity_hours = verify_settings.get('validity_hours', 24)
            validity_seconds = validity_hours * 3600
        
        total_users = len(users)
        per_page = 10
        total_pages = (total_users + per_page - 1) // per_page if total_users > 0 else 1
        
        if total_users == 0:
            text = """<b>👥 Verified Users</b>

━━━━━━━━━━━━━━━━━━━━

<i>No verified users found.</i>

━━━━━━━━━━━━━━━━━━━━"""
            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="vp_back")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
            return
        
        # Get users for current page
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_users = users[start_idx:end_idx]
        
        # Import datetime for time calculations
        from datetime import datetime
        
        text = f"""<b>👥 Verified Users ({total_users} total)</b>

━━━━━━━━━━━━━━━━━━━━

"""
        
        for i, user in enumerate(page_users, start=start_idx + 1):
            username = user.get('username', 'Unknown')
            user_id = user.get('user_id', 'Unknown')
            verified_date = user.get('verified_date', '')
            
            # Calculate time remaining
            time_remaining = "Unknown"
            try:
                if verified_date:
                    if ' ' in verified_date:  # New format with timestamp
                        verified_datetime = datetime.strptime(verified_date, '%Y-%m-%d %H:%M:%S')
                    else:  # Legacy format
                        verified_datetime = datetime.strptime(verified_date, '%Y-%m-%d')
                    
                    current_time = datetime.now()
                    elapsed = current_time - verified_datetime
                    remaining_seconds = validity_seconds - elapsed.total_seconds()
                    
                    if remaining_seconds > 0:
                        if remaining_seconds >= 3600:
                            hours = int(remaining_seconds // 3600)
                            mins = int((remaining_seconds % 3600) // 60)
                            time_remaining = f"{hours}h {mins}m"
                        elif remaining_seconds >= 60:
                            mins = int(remaining_seconds // 60)
                            secs = int(remaining_seconds % 60)
                            time_remaining = f"{mins}m {secs}s"
                        else:
                            time_remaining = f"{int(remaining_seconds)}s"
                    else:
                        time_remaining = "⏰ Expired"
            except Exception as e:
                logger.error(f"Error calculating time: {e}")
                time_remaining = "Error"
            
            text += f"<b>{i}.</b> @{username} | <code>{user_id}</code>\n    ⏳ <i>{time_remaining} left</i>\n"
        
        text += f"""
━━━━━━━━━━━━━━━━━━━━

<i>Page {page + 1}/{total_pages}</i>"""

        buttons = []
        
        # Add user revoke buttons (2 per row)
        row = []
        for user in page_users:
            user_id = user.get('user_id')
            username = user.get('username', str(user_id))[:15]
            row.append(InlineKeyboardButton(f"❌ {username}", callback_data=f"vp_revoke_{user_id}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"vp_users_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"vp_users_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton("⬅️ Back to Panel", callback_data="vp_back")])
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error showing verified users: {e}")
        await query.answer(f"Error: {e}", show_alert=True)


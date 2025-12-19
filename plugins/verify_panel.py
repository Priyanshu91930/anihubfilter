# Verification Admin Panel - Manage verification system
# Created for AnihubFilter Bot

import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_chats_db import db
from info import ADMINS
from utils import temp

logger = logging.getLogger(__name__)

# ==================== VERIFY PANEL COMMAND ====================
@Client.on_message(filters.command("verify_panel") & filters.private)
async def verify_panel(client, message):
    """Admin command to open verification management panel"""
    if message.from_user.id not in ADMINS:
        return await message.reply("⛔ This command is only for admins!")
    
    # Get current settings
    settings = await db.get_verify_settings()
    verified_count = await db.get_verified_users_count()
    
    status = "✅ ON" if settings.get('enabled', False) else "❌ OFF"
    shortlink_url = settings.get('shortlink_url', 'Not Set')
    shortlink_api = settings.get('shortlink_api', 'Not Set')
    validity_hours = settings.get('validity_hours', 24)
    
    # Mask API key for security
    if shortlink_api and shortlink_api != 'Not Set':
        masked_api = shortlink_api[:8] + "..." + shortlink_api[-4:] if len(shortlink_api) > 12 else "****"
    else:
        masked_api = 'Not Set'
    
    text = f"""<b>🔐 Verification Admin Panel</b>

━━━━━━━━━━━━━━━━━━━━

<b>📊 Status:</b> {status}
<b>👥 Verified Users:</b> {verified_count}
<b>⏰ Validity:</b> <code>{validity_hours} Hours</code>
<b>🔗 Shortlink URL:</b> <code>{shortlink_url}</code>
<b>🔑 Shortlink API:</b> <code>{masked_api}</code>

━━━━━━━━━━━━━━━━━━━━

<i>Use the buttons below to manage verification:</i>"""

    buttons = [
        [
            InlineKeyboardButton("✅ Turn ON" if not settings.get('enabled', False) else "❌ Turn OFF", 
                               callback_data="verify_toggle")
        ],
        [
            InlineKeyboardButton("👥 View Users", callback_data="verify_users_0"),
            InlineKeyboardButton("⏰ Set Validity", callback_data="verify_set_validity")
        ],
        [
            InlineKeyboardButton("🔗 Set Shortlink", callback_data="verify_set_shortlink"),
            InlineKeyboardButton("🔑 Set API", callback_data="verify_set_api")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="verify_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="close_data")
        ]
    ]
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)


# ==================== CALLBACK HANDLERS ====================
@Client.on_callback_query(filters.regex(r"^verify_"))
async def verify_callback_handler(client, query: CallbackQuery):
    """Handle verification panel callbacks"""
    if query.from_user.id not in ADMINS:
        return await query.answer("⛔ Only admins can use this!", show_alert=True)
    
    data = query.data
    
    # Toggle verification ON/OFF
    if data == "verify_toggle":
        settings = await db.get_verify_settings()
        new_status = not settings.get('enabled', False)
        settings['enabled'] = new_status
        await db.update_verify_settings(settings)
        
        status_text = "ON ✅" if new_status else "OFF ❌"
        await query.answer(f"Verification is now {status_text}", show_alert=True)
        
        # Refresh the panel
        await refresh_verify_panel(query)
    
    # Refresh panel
    elif data == "verify_refresh":
        await refresh_verify_panel(query)
        await query.answer("🔄 Refreshed!")
    
    # View verified users (with pagination)
    elif data.startswith("verify_users_"):
        page = int(data.split("_")[2])
        await show_verified_users(query, page)
    
    # Set shortlink URL prompt
    elif data == "verify_set_shortlink":
        text = """<b>🔗 Set Shortlink URL</b>

Send the shortlink domain (without https://)

<b>Example:</b> <code>atglinks.com</code>

<b>Popular shorteners:</b>
• atglinks.com
• adrinolinks.in
• mdiskshortner.link
• tnlink.in

Send /cancel to cancel."""
        
        await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
        
        # Wait for user response
        try:
            response = await client.ask(
                query.message.chat.id, 
                text, 
                filters=filters.text,
                timeout=60
            )
            
            if response.text.lower() == "/cancel":
                await response.reply("❌ Cancelled!")
                await refresh_verify_panel_message(client, query.message)
                return
            
            # Save the shortlink URL
            settings = await db.get_verify_settings()
            settings['shortlink_url'] = response.text.strip()
            await db.update_verify_settings(settings)
            
            await response.reply(f"✅ Shortlink URL set to: <code>{response.text.strip()}</code>", parse_mode=enums.ParseMode.HTML)
            await refresh_verify_panel_message(client, query.message)
            
        except Exception as e:
            await query.message.reply(f"⏰ Timeout or error: {e}")
            await refresh_verify_panel_message(client, query.message)
    
    # Set API key prompt
    elif data == "verify_set_api":
        text = """<b>🔑 Set Shortlink API Key</b>

Send your shortlink API key.

<i>You can get this from your shortener dashboard.</i>

Send /cancel to cancel."""
        
        await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
        
        try:
            response = await client.ask(
                query.message.chat.id, 
                text, 
                filters=filters.text,
                timeout=60
            )
            
            if response.text.lower() == "/cancel":
                await response.reply("❌ Cancelled!")
                await refresh_verify_panel_message(client, query.message)
                return
            
            # Save the API key
            settings = await db.get_verify_settings()
            settings['shortlink_api'] = response.text.strip()
            await db.update_verify_settings(settings)
            
            await response.reply("✅ Shortlink API key saved successfully!")
            await refresh_verify_panel_message(client, query.message)
            
        except Exception as e:
            await query.message.reply(f"⏰ Timeout or error: {e}")
            await refresh_verify_panel_message(client, query.message)
    
    # Set validity hours
    elif data == "verify_set_validity":
        text = """<b>⏰ Set Verification Validity</b>

Send the number of hours for verification validity.

<b>Examples:</b>
• <code>24</code> for 24 hours (1 day)
• <code>48</code> for 48 hours (2 days)
• <code>72</code> for 72 hours (3 days)

Send /cancel to cancel."""
        
        await query.message.edit_text(text, parse_mode=enums.ParseMode.HTML)
        
        try:
            response = await client.ask(
                query.message.chat.id, 
                text, 
                filters=filters.text,
                timeout=60
            )
            
            if response.text.lower() == "/cancel":
                await response.reply("❌ Cancelled!")
                await refresh_verify_panel_message(client, query.message)
                return
            
            # Validate and save validity hours
            try:
                hours = int(response.text.strip())
                if hours < 1 or hours > 720:  # Max 30 days
                    await response.reply("❌ Please enter a number between 1 and 720 hours!")
                    await refresh_verify_panel_message(client, query.message)
                    return
                    
                settings = await db.get_verify_settings()
                settings['validity_hours'] = hours
                await db.update_verify_settings(settings)
                
                await response.reply(f"✅ Verification validity set to <code>{hours} hours</code>!", parse_mode=enums.ParseMode.HTML)
                await refresh_verify_panel_message(client, query.message)
            except ValueError:
                await response.reply("❌ Please enter a valid number!")
                await refresh_verify_panel_message(client, query.message)
            
        except Exception as e:
            await query.message.reply(f"⏰ Timeout or error: {e}")
            await refresh_verify_panel_message(client, query.message)
    
    # Revoke user verification
    elif data.startswith("verify_revoke_"):
        user_id = int(data.split("_")[2])
        await db.revoke_user_verification(user_id)
        await query.answer(f"✅ Revoked verification for user {user_id}", show_alert=True)
        # Go back to users list
        await show_verified_users(query, 0)
    
    # Back to panel
    elif data == "verify_back":
        await refresh_verify_panel(query)


async def refresh_verify_panel(query):
    """Refresh the verification panel"""
    settings = await db.get_verify_settings()
    verified_count = await db.get_verified_users_count()
    
    status = "✅ ON" if settings.get('enabled', False) else "❌ OFF"
    shortlink_url = settings.get('shortlink_url', 'Not Set') or 'Not Set'
    shortlink_api = settings.get('shortlink_api', 'Not Set') or 'Not Set'
    validity_hours = settings.get('validity_hours', 24)
    
    if shortlink_api and shortlink_api != 'Not Set':
        masked_api = shortlink_api[:8] + "..." + shortlink_api[-4:] if len(shortlink_api) > 12 else "****"
    else:
        masked_api = 'Not Set'
    
    text = f"""<b>🔐 Verification Admin Panel</b>

━━━━━━━━━━━━━━━━━━━━

<b>📊 Status:</b> {status}
<b>👥 Verified Users:</b> {verified_count}
<b>⏰ Validity:</b> <code>{validity_hours} Hours</code>
<b>🔗 Shortlink URL:</b> <code>{shortlink_url}</code>
<b>🔑 Shortlink API:</b> <code>{masked_api}</code>

━━━━━━━━━━━━━━━━━━━━

<i>Use the buttons below to manage verification:</i>"""

    buttons = [
        [
            InlineKeyboardButton("✅ Turn ON" if not settings.get('enabled', False) else "❌ Turn OFF", 
                               callback_data="verify_toggle")
        ],
        [
            InlineKeyboardButton("👥 View Users", callback_data="verify_users_0"),
            InlineKeyboardButton("⏰ Set Validity", callback_data="verify_set_validity")
        ],
        [
            InlineKeyboardButton("🔗 Set Shortlink", callback_data="verify_set_shortlink"),
            InlineKeyboardButton("🔑 Set API", callback_data="verify_set_api")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="verify_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="close_data")
        ]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)


async def refresh_verify_panel_message(client, message):
    """Refresh the verification panel (for message object)"""
    settings = await db.get_verify_settings()
    verified_count = await db.get_verified_users_count()
    
    status = "✅ ON" if settings.get('enabled', False) else "❌ OFF"
    shortlink_url = settings.get('shortlink_url', 'Not Set') or 'Not Set'
    shortlink_api = settings.get('shortlink_api', 'Not Set') or 'Not Set'
    validity_hours = settings.get('validity_hours', 24)
    
    if shortlink_api and shortlink_api != 'Not Set':
        masked_api = shortlink_api[:8] + "..." + shortlink_api[-4:] if len(shortlink_api) > 12 else "****"
    else:
        masked_api = 'Not Set'
    
    text = f"""<b>🔐 Verification Admin Panel</b>

━━━━━━━━━━━━━━━━━━━━

<b>📊 Status:</b> {status}
<b>👥 Verified Users:</b> {verified_count}
<b>⏰ Validity:</b> <code>{validity_hours} Hours</code>
<b>🔗 Shortlink URL:</b> <code>{shortlink_url}</code>
<b>🔑 Shortlink API:</b> <code>{masked_api}</code>

━━━━━━━━━━━━━━━━━━━━

<i>Use the buttons below to manage verification:</i>"""

    buttons = [
        [
            InlineKeyboardButton("✅ Turn ON" if not settings.get('enabled', False) else "❌ Turn OFF", 
                               callback_data="verify_toggle")
        ],
        [
            InlineKeyboardButton("👥 View Users", callback_data="verify_users_0"),
            InlineKeyboardButton("⏰ Set Validity", callback_data="verify_set_validity")
        ],
        [
            InlineKeyboardButton("🔗 Set Shortlink", callback_data="verify_set_shortlink"),
            InlineKeyboardButton("🔑 Set API", callback_data="verify_set_api")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="verify_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="close_data")
        ]
    ]
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)


async def show_verified_users(query, page):
    """Show verified users with pagination"""
    users_cursor = await db.get_all_verified_users()
    users = [user async for user in users_cursor]
    
    total_users = len(users)
    per_page = 10
    total_pages = (total_users + per_page - 1) // per_page if total_users > 0 else 1
    
    if total_users == 0:
        text = """<b>👥 Verified Users</b>

━━━━━━━━━━━━━━━━━━━━

<i>No verified users found.</i>

━━━━━━━━━━━━━━━━━━━━"""
        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="verify_back")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return
    
    # Get users for current page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_users = users[start_idx:end_idx]
    
    text = f"""<b>👥 Verified Users ({total_users} total)</b>

━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, user in enumerate(page_users, start=start_idx + 1):
        username = user.get('username', 'Unknown')
        user_id = user.get('user_id', 'Unknown')
        verified_date = user.get('verified_date', 'Unknown')
        text += f"<b>{i}.</b> @{username} | <code>{user_id}</code>\n"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━

<i>Page {page + 1}/{total_pages}</i>
<i>Click on a user below to revoke:</i>"""

    buttons = []
    
    # Add user revoke buttons (2 per row)
    row = []
    for user in page_users:
        user_id = user.get('user_id')
        username = user.get('username', str(user_id))[:15]
        row.append(InlineKeyboardButton(f"❌ {username}", callback_data=f"verify_revoke_{user_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"verify_users_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"verify_users_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("⬅️ Back to Panel", callback_data="verify_back")])
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)

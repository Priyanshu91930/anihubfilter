# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, asyncio, os, re, random, pytz, aiohttp, requests, string, json, http.client
from info import *
from imdb import Cinemagoer 
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from pyrogram.errors import *
from typing import Union
from Script import script
from datetime import datetime, date
from typing import List
from database.users_chats_db import db
from database.join_reqs import JoinReqs
from bs4 import BeautifulSoup
from shortzy import Shortzy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
join_db = JoinReqs
BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))")

imdb = Cinemagoer() 
TOKENS = {}
VERIFIED = {}
BANNED = {}
SECOND_SHORTENER = {}
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

# temp db for banned 
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    BOT = None
    CURRENT=int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    GETALL = {}
    SHORT = {}
    SETTINGS = {}
    IMDB_CAP = {}
    VERIFY_MSG = {}  # Store verification message IDs for deletion after user searches again


async def pub_is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append(
                [InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)]
            )
        except Exception as e:
            pass
    return btn

async def is_subscribed(bot, query):
    if REQUEST_TO_JOIN_MODE == True and join_db().isActive():
        try:
            user = await join_db().get_user(query.from_user.id)
            if user and user["user_id"] == query.from_user.id:
                return True
            else:
                try:
                    user_data = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
                except UserNotParticipant:
                    pass
                except Exception as e:
                    logger.exception(e)
                else:
                    if user_data.status != enums.ChatMemberStatus.BANNED:
                        return True
        except Exception as e:
            logger.exception(e)
            return False
    else:
        try:
            user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
        except UserNotParticipant:
            pass
        except Exception as e:
            logger.exception(e)
        else:
            if user.status != enums.ChatMemberStatus.BANNED:
                return True
        return False

async def get_poster(query, bulk=False, id=False, file=None):
    """Fetch movie/series data and poster from TMDb API"""
    TMDB_API_KEY = "0e4f90e7d4208541a1d49bb73c1fc1d3"  # Free public TMDb API key
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
    
    try:
        if not id:
            query = (query.strip()).lower()
            title = query
            year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
            if year:
                year = year[0]
                title = (query.replace(year, "")).strip()
            elif file is not None:
                year_match = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
                if year_match:
                    year = year_match[0]
            else:
                year = None
            
            # Remove season/episode patterns for TMDb search (s03, s01e05, season 3, etc.)
            # This ensures TMDb can find the show even when user includes season info
            title = re.sub(r'\bs\d{1,2}(e\d{1,2})?\b', '', title, flags=re.IGNORECASE)  # Remove s03, s01e05
            title = re.sub(r'\bseason\s*\d{1,2}\b', '', title, flags=re.IGNORECASE)  # Remove season 3
            title = re.sub(r'\bepisode\s*\d{1,3}\b', '', title, flags=re.IGNORECASE)  # Remove episode 5
            title = re.sub(r'\s+', ' ', title).strip()  # Clean up extra spaces
            
            print(f"[DEBUG get_poster] Searching TMDb for title: '{title}'{f' year: {year}' if year else ''}")
            
            # Search TMDb for the movie/series
            search_url = f"{TMDB_BASE_URL}/search/multi"
            params = {
                "api_key": TMDB_API_KEY,
                "query": title,
                "include_adult": "false"
            }
            # Note: /search/multi doesn't support year parameter, we'll filter results instead
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params) as response:
                    if response.status != 200:
                        print(f"[DEBUG get_poster] TMDb API error: {response.status}")
                        return None
                    data = await response.json()
            
            results = data.get("results", [])
            print(f"[DEBUG get_poster] TMDb search results count: {len(results)}")
            
            if not results:
                print(f"[DEBUG get_poster] No results found for '{title}'")
                return None
            
            if bulk:
                return results[:10]
            
            # Get the first result (most relevant)
            item = results[0]
            tmdb_id = item.get("id")
            media_type = item.get("media_type", "movie")
            print(f"[DEBUG get_poster] Using first result - ID: {tmdb_id}, Type: {media_type}")
            
            # Fetch detailed info
            if media_type == "tv":
                detail_url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
            else:
                detail_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
            
            params = {
                "api_key": TMDB_API_KEY,
                "append_to_response": "credits,videos"
            }
            
            print(f"[DEBUG get_poster] Fetching details from: {detail_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(detail_url, params=params) as response:
                    if response.status != 200:
                        print(f"[DEBUG get_poster] TMDb details API error: {response.status}")
                        return None
                    movie = await response.json()
                    print(f"[DEBUG get_poster] Details fetched successfully")
        else:
            # If ID is provided
            detail_url = f"{TMDB_BASE_URL}/movie/{query}"
            params = {"api_key": TMDB_API_KEY, "append_to_response": "credits,videos"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(detail_url, params=params) as response:
                    if response.status != 200:
                        return None
                    movie = await response.json()
        
        # Extract poster URL - use poster (portrait) as requested
        poster_path = movie.get("poster_path") or movie.get("backdrop_path")
        poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None
        
        print(f"[DEBUG get_poster] Got movie: {movie.get('title') or movie.get('name')}")
        print(f"[DEBUG get_poster] Poster URL: {poster_url if poster_url else 'No poster'}")
        
        # Extract cast
        credits = movie.get("credits", {})
        cast_list = credits.get("cast", [])[:5]
        cast = ", ".join([person.get("name", "") for person in cast_list]) if cast_list else "N/A"
        
        # Extract crew
        crew = credits.get("crew", [])
        director = ", ".join([person.get("name") for person in crew if person.get("job") == "Director"][:3]) or "N/A"
        writer = ", ".join([person.get("name") for person in crew if person.get("job") in ["Writer", "Screenplay"]][:3]) or "N/A"
        producer = ", ".join([person.get("name") for person in crew if person.get("job") == "Producer"][:3]) or "N/A"
        
        # Build response
        title = movie.get("title") or movie.get("name", "N/A")
        release_date = movie.get("release_date") or movie.get("first_air_date", "N/A")
        
        return {
            'title': title,
            'votes': movie.get("vote_count", "N/A"),
            "aka": ", ".join(movie.get("alternative_titles", {}).get("titles", []))[:100] if movie.get("alternative_titles") else "N/A",
            "seasons": movie.get("number_of_seasons", "N/A"),
            "box_office": "N/A",
            'localized_title': movie.get("original_title") or movie.get("original_name", title),
            'kind': "tv series" if media_type == "tv" or movie.get("number_of_seasons") else "movie",
            "imdb_id": movie.get("imdb_id", "N/A"),
            "cast": cast,
            "runtime": f"{movie.get('runtime', 'N/A')} min" if movie.get('runtime') else "N/A",
            "countries": ", ".join([c.get("name", "") for c in movie.get("production_countries", [])])[:100] or "N/A",
            "certificates": "N/A",
            "languages": ", ".join([l.get("english_name", "") for l in movie.get("spoken_languages", [])])[:100] or "N/A",
            "director": director,
            "writer": writer,
            "producer": producer,
            "composer": "N/A",
            "cinematographer": "N/A",
            "music_team": "N/A",
            "distributors": "N/A",
            'release_date': release_date,
            'year': release_date.split("-")[0] if release_date and "-" in release_date else "N/A",
            'genres': ", ".join([g.get("name", "") for g in movie.get("genres", [])])[:100] or "N/A",
            'poster': poster_url,
            'plot': movie.get("overview", "N/A")[:800],
            'rating': str(movie.get("vote_average", "N/A")),
            'url': f'https://www.themoviedb.org/{"tv" if media_type == "tv" else "movie"}/{movie.get("id", "")}'
        }
    
    except Exception as e:
        print(f"[DEBUG get_poster] Exception: {e}")
        import traceback
        traceback.print_exc()
        return None


async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def broadcast_messages_group(chat_id, message):
    try:
        kd = await message.copy(chat_id=chat_id)
        try:
            await kd.pin()
        except:
            pass
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages_group(chat_id, message)
    except Exception as e:
        return False, "Error"
    
async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
        }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all( 'h3' )
    return [title.getText() for title in titles]

async def get_settings(group_id):
    settings = await db.get_settings(group_id)
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current.update({key: value})
    await db.update_settings(group_id, current)
    
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]  

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
           
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time

def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1  # ignore first char -> is some kind of quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)

    # 1 to avoid starting quote, and counter is exclusive so avoids ending
    key = remove_escapes(text[1:counter].strip())
    # index will be in range, or `else` would have been executed and returned
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))

def gfilterparser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'



async def get_clone_shortlink(link, url, api):
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link
                           
async def get_shortlink(chat_id, link):
    settings = await get_settings(chat_id) #fetching settings for group
    if 'shortlink' in settings.keys():
        URL = settings['shortlink']
        API = settings['shortlink_api']
    else:
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL.startswith("shorturllink") or URL.startswith("terabox.in") or URL.startswith("urlshorten.in"):
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL == "api.shareus.io":
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link
    
async def get_tutorial(chat_id):
    settings = await get_settings(chat_id) #fetching settings for group
    return settings['tutorial']
        
async def get_verify_shorted_link(link, url, api):
    API = api
    URL = url
    if URL == "api.shareus.io":
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link
        
async def check_token(bot, userid, token):
    user = await bot.get_users(int(userid))
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    if user.id in TOKENS.keys():
        TKN = TOKENS[user.id]
        if token in TKN.keys():
            is_used = TKN[token]
            if is_used == True:
                return False
            else:
                return True
    else:
        return False

async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    link = f"{link}verify-{user.id}-{token}"
    
    # Get shortlink URL and API from database settings (set via admin panel)
    verify_settings = await db.get_verify_settings()
    shortlink_url = verify_settings.get('shortlink_url') or VERIFY_SHORTLINK_URL
    shortlink_api = verify_settings.get('shortlink_api') or VERIFY_SHORTLINK_API
    
    if not shortlink_url or not shortlink_api:
        return link  # Return original link if shortlink not configured
    
    shortened_verify_url = await get_verify_shorted_link(link, shortlink_url, shortlink_api)
    if VERIFY_SECOND_SHORTNER == True:
        snd_link = await get_verify_shorted_link(shortened_verify_url, VERIFY_SND_SHORTLINK_URL, VERIFY_SND_SHORTLINK_API)
        return str(snd_link)
    else:
        return str(shortened_verify_url)

async def verify_user(bot, userid, token):
    user = await bot.get_users(int(userid))
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    TOKENS[user.id] = {token: True}
    
    # Store full datetime with timestamp, not just date
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    verified_datetime_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # Store in memory
    VERIFIED[user.id] = verified_datetime_str
    
    # Also store in database for admin panel
    username = user.username if user.username else user.first_name
    await db.add_verified_user(user.id, username, verified_datetime_str)

async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    
    # First check if verification is enabled from database
    verify_settings = await db.get_verify_settings()
    if not verify_settings.get('enabled', False):
        return True  # If verification is disabled, everyone is "verified"
    
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    
    # Use validity_seconds if available, otherwise convert validity_hours to seconds
    validity_seconds = verify_settings.get('validity_seconds')
    if validity_seconds is None:
        validity_hours = verify_settings.get('validity_hours', 24)
        validity_seconds = validity_hours * 3600
    
    # Check in-memory VERIFIED dict first (for performance)
    if user.id in VERIFIED.keys():
        verified_str = VERIFIED[user.id]
        
        # Handle both formats: "YYYY-MM-DD HH:MM:SS" (new) and "YYYY-MM-DD" (legacy)
        try:
            if ' ' in verified_str:  # New format with timestamp
                verified_datetime = datetime.strptime(verified_str, '%Y-%m-%d %H:%M:%S')
                current_time = datetime.now()
                time_diff = current_time - verified_datetime
                
                # Check if still valid based on validity seconds
                if time_diff.total_seconds() < validity_seconds:
                    return True
                else:
                    # Expired! Clean up from memory and database
                    del VERIFIED[user.id]
                    await db.revoke_user_verification(user.id)
                    return False
            else:  # Legacy format (just date) - THIS SHOULDN'T BE USED ANYMORE
                # For legacy date-only format, convert to datetime and check expiry properly
                verified_datetime = datetime.strptime(verified_str, '%Y-%m-%d')
                current_time = datetime.now()
                time_diff = current_time - verified_datetime
                
                # Check if still valid based on validity seconds
                if time_diff.total_seconds() < validity_seconds:
                    return True
                else:
                    # Expired! Clean up from memory and database
                    del VERIFIED[user.id]
                    await db.revoke_user_verification(user.id)
                    return False
        except:
            return False
    
    # If not in memory, check database (important for bot restarts)
    verified_users = await db.get_verified_users()
    for verified_user in verified_users:
        if verified_user['user_id'] == user.id:
            # Found in database, check if still valid
            verified_str = verified_user['verified_date']
            
            # Handle both formats
            try:
                if ' ' in verified_str:  # New format with timestamp
                    verified_datetime = datetime.strptime(verified_str, '%Y-%m-%d %H:%M:%S')
                else:  # Legacy format - assume midnight
                    verified_datetime = datetime.strptime(verified_str, '%Y-%m-%d')
                
                current_time = datetime.now()
                time_diff = current_time - verified_datetime
                
                # Check if verification is still valid based on validity_seconds
                if time_diff.total_seconds() < validity_seconds:
                    # Still valid! Add back to in-memory dict for faster future checks
                    VERIFIED[user.id] = verified_user['verified_date']
                    return True
                else:
                    # Expired! Remove from database
                    await db.revoke_user_verification(user.id)
                    return False
            except:
                # If parsing fails, consider not verified
                return False
    
    # Not verified at all
    return False  
    
async def send_all(bot, userid, files, ident, chat_id, user_name, query):
    # Check verification first  
    verify_status = await check_verification(bot, userid)
    if not verify_status:
        # User needs to verify
        try:
            verify_url = await get_token(bot, userid, f"https://telegram.me/{temp.U_NAME}?start=")
            btn = [[InlineKeyboardButton("✅ Click Here To Verify", url=verify_url)]]
            await bot.send_message(
                chat_id=userid,
                text="<b>🔐 You Need To Verify First!\n\n✅ Click the button below to verify and get your files.\n\n⏰ After verification, click on the file button again.</b>",
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML
            )
            await query.answer("⚠️ Please verify first to get files!", show_alert=True)
            return
        except Exception as e:
            logger.error(f"Error sending verify message: {e}")
            await query.answer("⚠️ Please verify first! Send /start to the bot.", show_alert=True)
            return
    
    settings = await get_settings(chat_id)
    if 'is_shortlink' in settings.keys():
        ENABLE_SHORTLINK = settings['is_shortlink']
    else:
        await save_group_settings(message.chat.id, 'is_shortlink', False)
        ENABLE_SHORTLINK = False
    try:
        if ENABLE_SHORTLINK:
            for file in files:
                title = file["file_name"]
                size = get_size(file["file_size"])
                if not await db.has_premium_access(userid) and SHORTLINK_MODE == True:
                    await bot.send_message(chat_id=userid, text=f"<b>Hᴇʏ ᴛʜᴇʀᴇ {user_name} 👋🏽 \n\n✅ Sᴇᴄᴜʀᴇ ʟɪɴᴋ ᴛᴏ ʏᴏᴜʀ ғɪʟᴇ ʜᴀs sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴇᴇɴ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴅᴏᴡɴʟᴏᴀᴅ ʙᴜᴛᴛᴏɴ\n\n🗃️ Fɪʟᴇ Nᴀᴍᴇ : {title}\n🔖 Fɪʟᴇ Sɪᴢᴇ : {size}</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Dᴏᴡɴʟᴏᴀᴅ 📥", url=await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}"))]]))
        else:
            for file in files:
                f_caption = file["caption"]
                title = file["file_name"].replace("@VJ_Bots", "@anihubyt25").replace("@Tech_VJ", "@anihubyt25")
                size = get_size(file["file_size"])
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption = CUSTOM_FILE_CAPTION.format(
                            file_name='' if title is None else title,
                            file_size='' if size is None else size,
                            file_caption='' if f_caption is None else f_caption
                        )
                    except Exception as e:
                        print(e)
                        f_caption = f_caption
                if f_caption is None:
                    f_caption = f"{title}"
                await bot.send_cached_media(
                    chat_id=userid,
                    file_id=file["file_id"],
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False,
                    reply_markup=InlineKeyboardMarkup(
                        [[
                            InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK),
                            InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                        ],[
                            InlineKeyboardButton("Bᴏᴛ Oᴡɴᴇʀ", url=OWNER_LNK)
                        ]]
                    )
                )
    except UserIsBlocked:
        await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
    except PeerIdInvalid:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
    except Exception as e:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
        
async def get_cap(settings, remaining_seconds, files, query, total_results, search):
    if settings["imdb"]:
        IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
        if IMDB_CAP:
            cap = IMDB_CAP
            cap+="\n\n<b>📁 Files Found:</b>\n\n"
            for file in files:
                cap += f"<b>📄 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
        else:
            imdb = await get_poster(search, file=(files[0])["file_name"]) if settings["imdb"] else None
            if imdb:
                TEMPLATE = script.IMDB_TEMPLATE_TXT
                cap = TEMPLATE.format(
                    qurey=search,
                    title=imdb['title'],
                    votes=imdb['votes'],
                    aka=imdb["aka"],
                    seasons=imdb["seasons"],
                    box_office=imdb['box_office'],
                    localized_title=imdb['localized_title'],
                    kind=imdb['kind'],
                    imdb_id=imdb["imdb_id"],
                    cast=imdb["cast"],
                    runtime=imdb["runtime"],
                    countries=imdb["countries"],
                    certificates=imdb["certificates"],
                    languages=imdb["languages"],
                    director=imdb["director"],
                    writer=imdb["writer"],
                    producer=imdb["producer"],
                    composer=imdb["composer"],
                    cinematographer=imdb["cinematographer"],
                    music_team=imdb["music_team"],
                    distributors=imdb["distributors"],
                    release_date=imdb['release_date'],
                    year=imdb['year'],
                    genres=imdb['genres'],
                    poster=imdb['poster'],
                    plot=imdb['plot'],
                    rating=imdb['rating'],
                    url=imdb['url'],
                    **locals()
                )
                cap+="\n\n<b>📁 Files Found:</b>\n\n"
                for file in files:
                    cap += f"<b>📄 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
            else:
                cap = f"<b>🔍 Results for:</b> <code>{search}</code>\n\n<b>👤 Requested by:</b> {query.from_user.mention}\n<b>⚡ Found in:</b> {remaining_seconds} seconds\n<b>💬 Group:</b> {query.message.chat.title}\n\n━━━━━━━━━━━━━━━━━━━━\n\n⏳ <i>Auto-delete in 5 minutes</i>\n\n"
                cap+="<b>📁 Files Found:</b>\n\n"
                for file in files:
                    cap += f"<b>📄 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
    else:
        cap = f"<b>🔍 Results for:</b> <code>{search}</code>\n\n<b>👤 Requested by:</b> {query.from_user.mention}\n<b>⚡ Found in:</b> {remaining_seconds} seconds\n<b>💬 Group:</b> {query.message.chat.title}\n\n━━━━━━━━━━━━━━━━━━━━\n\n⏳ <i>Auto-delete in 5 minutes</i>\n\n"
        cap+="<b>📁 Files Found:</b>\n\n"
        for file in files:
            cap += f"<b>📄 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
    return cap


async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:]
        if value:
            value = int(value)
        return value, unit
    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0


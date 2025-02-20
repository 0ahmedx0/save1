#safe_repo


import math
import time , re
from pyrogram import enums
from config import CHANNEL_ID, OWNER_ID 
from safe_repo.core import script
from safe_repo.core.mongo.plans_db import premium_users
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import cv2
from pyrogram.errors import FloodWait, InviteHashInvalid, InviteHashExpired, UserAlreadyParticipant, UserNotParticipant
from datetime import datetime as dt
import asyncio, subprocess, re, os, time


def sanitize_filename(filename):
    """
    Cleans up a filename by removing or replacing invalid characters.
    """
    # Replace invalid characters with underscores
    return re.sub(r'[^\w\-_.]', '_', filename)
def get_safe_timestamp(duration):
    """Returns a safe timestamp to capture a thumbnail."""
    return max(5, min(duration - 5, duration / 2))

async def chk_user(message, user_id):
    user = await premium_users()
    if user_id in user or user_id in OWNER_ID:
        return 0
    else:
        return 0



async def gen_link(app,chat_id):
   link = await app.export_chat_invite_link(chat_id)
   return link

async def subscribe(app, message):
   update_channel = CHANNEL_ID
   url = await gen_link(app, update_channel)
   if update_channel:
      try:
         user = await app.get_chat_member(update_channel, message.from_user.id)
         if user.status == "kicked":
            return 0
      except UserNotParticipant:
         await message.reply_photo(photo="https://graph.org/file/d44f024a08ded19452152.jpg",caption=script.FORCE_MSG.format(message.from_user.mention), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Now...", url=f"{url}")]]))
         return 0
      except Exception:
         return 0



async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""

        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1

        unit = ts[index:].lstrip()

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




PROGRESS_BAR = """\n
**__Completed__** : {1}/{2}
**__Bytes__** : {0}%
**__Speed__** : {3}/s
**__Time__** : {4}
"""


async def progress_bar(current, total, ud_type, message, start):

    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        # if round(current / total * 100, 0) % 5 == 0:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "{0}{1}".format(
            ''.join(["🟢" for i in range(math.floor(percentage / 10))]),
            ''.join(["🔴" for i in range(10 - math.floor(percentage / 10))]))
            
        tmp = progress + PROGRESS_BAR.format( 
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            # elapsed_time if elapsed_time != '' else "0 s",
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text="{}\n\n{}".format(ud_type, tmp),)             
                
        except:
            pass

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2] 



def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)




async def userbot_join(userbot, invite_link):
    try:
        await userbot.join_chat(invite_link)
        return "Successfully joined the Channel"
    except UserAlreadyParticipant:
        return "User is already a participant."
    except (InviteHashInvalid, InviteHashExpired):
        return "Could not join. Maybe your link is expired or Invalid."
    except FloodWait:
        return "Too many requests, try again later."
    except Exception as e:
        print(e)
        return "Could not join, try joining manually."
    


def get_link(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex,string)   
    try:
        link = [x[0] for x in url][0]
        if link:
            return link
        else:
            return False
    except Exception:
        return False


def video_metadata(file):
    default_values = {'width': 1, 'height': 1, 'duration': 1}
    try:
        vcap = cv2.VideoCapture(file)
        if not vcap.isOpened():
            return default_values  # Return defaults if video cannot be opened

        width = round(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = round(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = vcap.get(cv2.CAP_PROP_FPS)
        frame_count = vcap.get(cv2.CAP_PROP_FRAME_COUNT)

        if fps <= 0:
            return default_values  # Return defaults if FPS value is zero or negative

        duration = round(frame_count / fps)
        if duration <= 0:
            return default_values  # Return defaults if duration is zero or negative

        vcap.release()
        return {'width': width, 'height': height, 'duration': duration}

    except Exception as e:
        print(f"Error in video_metadata: {e}")
        return default_values
    
def hhmmss(seconds):
    return time.strftime('%H:%M:%S',time.gmtime(seconds))

async def screenshot(video, duration, sender):
    # Check if the video file exists
    if not os.path.isfile(video):
        print(f"Video file not found: {video}")
        return None

    # Generate a unique thumbnail path for each part
    safe_timestamp = get_safe_timestamp(duration)  # Calculate a safe timestamp
    time_stamp = hhmmss(safe_timestamp)  # Convert to HH:MM:SS format
    out = f"{sender}_thumb_{time_stamp}.jpg"
    out = sanitize_filename(out)  # Sanitize the filename

    # FFmpeg command to capture the thumbnail
    cmd = [
        "ffmpeg",
        "-ss", f"{time_stamp}",  # Capture at the middle of the video
        "-i", f"{video}",
        "-vf", "scale=1280:720",  # Ensure consistent resolution (16:9 aspect ratio)
        "-frames:v", "1",
        "-y",  # Overwrite output file if it exists
        f"{out}"
    ]

    # Execute the FFmpeg command
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    # Check for errors
    if stderr:
        print(f"FFmpeg error: {stderr.decode()}")
        return None

    # Check if the thumbnail was created successfully
    if os.path.isfile(out):
        print(f"Thumbnail saved at: {out}")
        return out
    else:
        print(f"Failed to capture thumbnail for {video}")
        return Noneس

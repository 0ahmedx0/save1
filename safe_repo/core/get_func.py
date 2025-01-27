
#safe_repo

import asyncio
import time
import os
import subprocess
import requests
from safe_repo import app 
from safe_repo import sex as gf # Assuming 'sex' is where your Pyrogram 'app' client is defined
import pymongo
from pyrogram import filters
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
from safe_repo.core.func import progress_bar, video_metadata, screenshot
from safe_repo.core.mongo import db
from pyrogram.types import Message
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP
import cv2
from telethon import events, Button
import re

# Dictionary to store Futures for pending split requests
response_futures = {}
pending_split_requests[sender] = file # Store file path for potential split
response_futures[sender] = asyncio.Future() # Create a Future for this user

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None


# Pyrogram Message Handler for /sp command replies
@app.on_message(filters.command("sp") & filters.reply) # Filter for /sp command as reply
async def split_command_handler_response(client, message):
    user_id = message.from_user.id
    if user_id in response_futures: # Check if user is waiting for a response
        future = response_futures[user_id]
        if not future.done():
            try:
                parts = int(message.text.split()[1])
                future.set_result(parts) # Set the number of parts as the Future's result
            except (ValueError, IndexError):
                future.set_result(None) # Set None if command is invalid
            del response_futures[user_id] # Clean up the Future
            return


async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    edit = ""
    chat = ""
    round_message = False
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]
    msg_id = int(msg_link.split("/")[-1]) + int(i)


    if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
        if 't.me/b/' not in msg_link:
            chat = int('-100' + str(msg_link.split("/")[-2]))
        else:
            chat = msg_link.split("/")[-2]
        file = ""
        try:
            chatx = message.chat.id
            msg = await userbot.get_messages(chat, msg_id)
            caption = None

            if msg.service is not None:
                return None
            if msg.empty is not None:
                return None
            if msg.media:
                if msg.media == MessageMediaType.WEB_PAGE:
                    target_chat_id = user_chat_ids.get(chatx, chatx)
                    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
                    safe_repo = await app.send_message(sender, msg.text.markdown)
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception as e:
                            await safe_repo.pin()
                    await safe_repo.copy(LOG_GROUP)
                    await edit.delete()
                    return
            if not msg.media:
                if msg.text:
                    target_chat_id = user_chat_ids.get(chatx, chatx)
                    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
                    safe_repo = await app.send_message(sender, msg.text.markdown)
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception as e:
                            await safe_repo.pin()
                    await safe_repo.copy(LOG_GROUP)
                    await edit.delete()
                    return

            edit = await app.edit_message_text(sender, edit_id, "Trying to Download...")
            file = await userbot.download_media(
                msg,
                progress=progress_bar,
                progress_args=("**__Downloading: __**\n",edit,time.time()))

            custom_rename_tag = get_user_rename_preference(chatx)
            last_dot_index = str(file).rfind('.')
            if last_dot_index != -1 and last_dot_index != 0:
                safe_repo_ext = str(file)[last_dot_index + 1:]
                if safe_repo_ext.isalpha() and len(safe_repo_ext) <= 4:
                    if safe_repo_ext.lower() == 'mov':
                        original_file_name = str(file)[:last_dot_index]
                        file_extension = 'mp4'
                    else:
                        original_file_name = str(file)[:last_dot_index]
                        file_extension = safe_repo_ext
                else:
                    original_file_name = str(file)
                    file_extension = 'mp4'
            else:
                original_file_name = str(file)
                file_extension = 'mp4'

            delete_words = load_delete_words(chatx)
            for word in delete_words:
                original_file_name = original_file_name.replace(word, "")
            video_file_name = original_file_name + " " + custom_rename_tag
            new_file_name = original_file_name + " " + custom_rename_tag + "." + file_extension
            os.rename(file, new_file_name)
            file = new_file_name

            # CODES are hidden

            await edit.edit('File downloaded, processing...')
            split_message = await app.send_message(sender, "Do you want to split this video? Send `/sp <number_of_parts>` as a reply to this message within 5 seconds to split, otherwise it will be uploaded as a single file.")
           
            try:
                parts = await asyncio.wait_for(response_futures[sender], timeout=5.0) # Wait for the Future to get a result with timeout
                if parts and isinstance(parts, int) and parts > 1:
                    split_part_counts[sender] = parts
                    await app.delete_messages(sender, split_message.id)
                    await edit.edit(f'Splitting video into {parts} parts...')
                    await split_video(file, parts, edit, sender, msg, caption, chatx, target_chat_id, LOG_GROUP) # Call split and upload function
                    del pending_split_requests[sender]
                    del split_part_counts[sender]
                    del response_futures[sender] # Clean up Future
                    return # Exit function after split and upload
                else:
                    await app.send_message(sender, "Invalid split command or timeout. Uploading as single file.") # Inform user about invalid parts
            except asyncio.TimeoutError:
                await app.send_message(sender, "Timeout reached. Uploading as single file.") # Inform user about timeout
            except asyncio.CancelledError: # Handle cancellation if needed
                pass # Task was cancelled, handle if necessary
            except Exception as e:
                await app.send_message(sender, f"Error processing split request: {e}. Uploading as single file.") # Inform user about error

            finally:
                if sender in response_futures:
                    del response_futures[sender] # Ensure Future is removed even on error/timeout

            await edit.edit('Trying to Uplaod ...')

            if msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:

                metadata = video_metadata(file)
                width= metadata['width']
                height= metadata['height']
                duration= metadata['duration']

                if duration <= 300:
                    safe_repo = await app.send_video(chat_id=sender, video=file, caption=caption, height=height, width=width, duration=duration, thumb=None, progress=progress_bar, progress_args=('**UPLOADING:**\n', edit, time.time()))
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception as e:
                            await safe_repo.pin()
                    await safe_repo.copy(LOG_GROUP)
                    await edit.delete()
                    return

                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}" if custom_caption else f"{original_caption}"
                lines = final_caption.split('\n')
                processed_lines = []
                for line in lines:
                    for word in delete_words:
                        line = line.replace(word, '')
                    if line.strip():
                        processed_lines.append(line.strip())
                final_caption = '\n'.join(processed_lines)
                replacements = load_replacement_words(sender)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"

                target_chat_id = user_chat_ids.get(chatx, chatx)

                thumb_path = await screenshot(file, duration, chatx)
                try:
                    safe_repo = await app.send_video(
                        chat_id=target_chat_id,
                        video=file,
                        caption=caption,
                        supports_streaming=True,
                        height=height,
                        width=width,
                        duration=duration,
                        thumb=thumb_path,
                        progress=progress_bar,
                        progress_args=(
                        '**__Uploading...__**\n',
                        edit,
                        time.time()
                        )
                       )
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception as e:
                            await safe_repo.pin()
                    await safe_repo.copy(LOG_GROUP)
                except:
                    await app.edit_message_text(sender, edit_id, "The bot is not an admin in the specified chat...")

                os.remove(file)

            elif msg.media == MessageMediaType.PHOTO:
                await edit.edit("**`Uploading photo...`")
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}" if custom_caption else f"{original_caption}"
                lines = final_caption.split('\n')
                processed_lines = []
                for line in lines:
                    for word in delete_words:
                        line = line.replace(word, '')
                    if line.strip():
                        processed_lines.append(line.strip())
                final_caption = '\n'.join(processed_lines)
                replacements = load_replacement_words(sender)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"

                target_chat_id = user_chat_ids.get(sender, sender)
                safe_repo = await app.send_photo(chat_id=target_chat_id, photo=file, caption=caption)
                if msg.pinned_message:
                    try:
                        await safe_repo.pin(both_sides=True)
                    except Exception as e:
                        await safe_repo.pin()
                await safe_repo.copy(LOG_GROUP)
            else:
                thumb_path = thumbnail(chatx)
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}" if custom_caption else f"{original_caption}"
                lines = final_caption.split('\n')
                processed_lines = []
                for line in lines:
                    for word in delete_words:
                        line = line.replace(word, '')
                    if line.strip():
                        processed_lines.append(line.strip())
                final_caption = '\n'.join(processed_lines)
                replacements = load_replacement_words(chatx)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"

                target_chat_id = user_chat_ids.get(chatx, chatx)
                try:
                    safe_repo = await app.send_document(
                        chat_id=target_chat_id,
                        document=file,
                        caption=caption,
                        thumb=thumb_path,
                        progress=progress_bar,
                        progress_args=(
                        '**`Uploading...`**\n',
                        edit,
                        time.time()
                        )
                    )
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception as e:
                            await safe_repo.pin()

                    await safe_repo.copy(LOG_GROUP)
                except:
                    await app.edit_message_text(sender, edit_id, "The bot is not an admin in the specified chat.")

                os.remove(file)

            await edit.delete()

        except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
            await app.edit_message_text(sender, edit_id, "Have you joined the channel?")
            return
        except Exception as e:
            await app.edit_message_text(sender, edit_id, f'Failed to save: `{msg_link}`\n\nError: {str(e)}')

    else:
        edit = await app.edit_message_text(sender, edit_id, "Cloning...")
        try:
            chat = msg_link.split("/")[-2]
            await copy_message_with_chat_id(app, sender, chat, msg_id)
            await edit.delete()
        except Exception as e:
            await app.edit_message_text(sender, edit_id, f'Failed to save: `{msg_link}`\n\nError: {str(e)}')


async def copy_message_with_chat_id(client, sender, chat_id, message_id):
    # Get the user's set chat ID, if available; otherwise, use the original sender ID
    target_chat_id = user_chat_ids.get(sender, sender)

    try:
        # Fetch the message using get_message
        msg = await client.get_messages(chat_id, message_id)

        # Modify the caption based on user's custom caption preference
        custom_caption = get_user_caption_preference(sender)
        original_caption = msg.caption if msg.caption else ''
        final_caption = f"{original_caption}" if custom_caption else f"{original_caption}"

        delete_words = load_delete_words(sender)
        for word in delete_words:
            final_caption = final_caption.replace(word, '  ')

        replacements = load_replacement_words(sender)
        for word, replace_word in replacements.items():
            final_caption = final_caption.replace(word, replace_word)

        caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"

        if msg.media:
            if msg.media == MessageMediaType.VIDEO:
                result = await client.send_video(target_chat_id, msg.video.file_id, caption=caption)
            elif msg.media == MessageMediaType.DOCUMENT:
                result = await client.send_document(target_chat_id, msg.document.file_id, caption=caption)
            elif msg.media == MessageMediaType.PHOTO:
                result = await client.send_photo(target_chat_id, msg.photo.file_id, caption=caption)
            else:
                # Use copy_message for any other media types
                result = await client.copy_message(target_chat_id, chat_id, message_id)
        else:
            # Use copy_message if there is no media
            result = await client.copy_message(target_chat_id, chat_id, message_id)

        # Attempt to copy the result to the LOG_GROUP
        try:
            await result.copy(LOG_GROUP)
        except Exception:
            pass

        if msg.pinned_message:
            try:
                await result.pin(both_sides=True)
            except Exception as e:
                await result.pin()

    except Exception as e:
        error_message = f"Error occurred while sending message to chat ID {target_chat_id}: {str(e)}"
        await client.send_message(sender, error_message)
        await client.send_message(sender, f"Make Bot admin in your Channel - {target_chat_id} and restart the process after /cancel")


async def split_video(file_path, parts, edit, sender, msg, caption, chatx, target_chat_id, log_group):
    metadata = video_metadata(file_path)
    duration = metadata['duration']
    split_duration = duration / parts
    output_path = os.path.splitext(file_path)[0] # Path without extension
    split_files = []

    for i in range(parts):
        start_time = i * split_duration
        end_time = (i + 1) * split_duration
        output_file = f"{output_path}_part{i+1}.mp4"
        split_files.append(output_file)
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c", "copy",
            output_file
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            await app.send_message(sender, f"Error splitting video part {i+1}: {stderr.decode()}")
            return

    await edit.edit('Uploading video parts...')
    thumb_path = await screenshot(file_path, duration, chatx) # Use original file for thumb for simplicity

    for part_file in split_files:
        try:
            metadata = video_metadata(part_file)
            width= metadata['width']
            height= metadata['height']
            duration= metadata['duration']

            safe_repo = await app.send_video(
                chat_id=target_chat_id,
                video=part_file,
                caption=f"{caption} (Part {split_files.index(part_file) + 1}/{parts})", # Add part number to caption
                supports_streaming=True,
                height=height,
                width=width,
                duration=duration,
                thumb=thumb_path,
                progress=progress_bar,
                progress_args=(
                    f'**__Uploading part {split_files.index(part_file) + 1}/{parts}...__**\n',
                    edit,
                    time.time()
                )
            )
            if msg.pinned_message:
                try:
                    await safe_repo.pin(both_sides=True)
                except Exception as e:
                    await safe_repo.pin()
            await safe_repo.copy(log_group)
        except Exception as e:
            await app.send_message(sender, f"Error uploading part {split_files.index(part_file) + 1}: {e}")
            continue # Continue to next part even if one fails

    await edit.delete()
    os.remove(file_path) # Delete original file after successful split and upload
    for part_file in split_files: # Delete split parts
        os.remove(part_file)
    await app.send_message(sender, "Video split and uploaded successfully in parts.")


# -------------- FFMPEG CODES ---------------

# ------------------------ Button Mode Editz FOR SETTINGS ----------------------------

# MongoDB database name and collection name
DB_NAME = "smart_users"
COLLECTION_NAME = "super_user"

# Establish a connection to MongoDB
mongo_client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

def load_authorized_users():
    """
    Load authorized user IDs from the MongoDB collection
    """
    authorized_users = set()
    for user_doc in collection.find():
        if "user_id" in user_doc:
            authorized_users.add(user_doc["user_id"])
    return authorized_users

def save_authorized_users(authorized_users):
    """
    Save authorized user IDs to the MongoDB collection
    """
    collection.delete_many({})
    for user_id in authorized_users:
        collection.insert_one({"user_id": user_id})

SUPER_USERS = load_authorized_users()

# Define a dictionary to store user chat IDs
user_chat_ids = {}

# MongoDB database name and collection name
MDB_NAME = "logins"
MCOLLECTION_NAME = "stringsession"

# Establish a connection to MongoDB
m_client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
mdb = m_client[MDB_NAME]
mcollection = mdb[MCOLLECTION_NAME]

def load_delete_words(user_id):
    """
    Load delete words for a specific user from MongoDB
    """
    try:
        words_data = collection.find_one({"_id": user_id})
        if words_data:
            return set(words_data.get("delete_words", []))
        else:
            return set()
    except Exception as e:
        print(f"Error loading delete words: {e}")
        return set()

def save_delete_words(user_id, delete_words):
    """
    Save delete words for a specific user to MongoDB
    """
    try:
        collection.update_one(
            {"_id": user_id},
            {"$set": {"delete_words": list(delete_words)}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving delete words: {e}")

def load_replacement_words(user_id):
    try:
        words_data = collection.find_one({"_id": user_id})
        if words_data:
            return words_data.get("replacement_words", {})
        else:
            return {}
    except Exception as e:
        print(f"Error loading replacement words: {e}")
        return {}

def save_replacement_words(user_id, replacements):
    try:
        collection.update_one(
            {"_id": user_id},
            {"$set": {"replacement_words": replacements}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving replacement words: {e}")

# Initialize the dictionary to store user preferences for renaming
user_rename_preferences = {}

# Initialize the dictionary to store user caption
user_caption_preferences = {}

# Function to load user session from MongoDB
def load_user_session(sender_id):
    user_data = collection.find_one({"user_id": sender_id})
    if user_data:
        return user_data.get("session")
    else:
        return None  # Or handle accordingly if session doesn't exist

# Function to handle the /setrename command
async def set_rename_command(user_id, custom_rename_tag):
    # Update the user_rename_preferences dictionary
    user_rename_preferences[str(user_id)] = custom_rename_tag

# Function to get the user's custom renaming preference
def get_user_rename_preference(user_id):
    # Retrieve the user's custom renaming tag if set, or default to 'safe_repo'
    return user_rename_preferences.get(str(user_id), 'safe_repo')

# Function to set custom caption preference
async def set_caption_command(user_id, custom_caption):
    # Update the user_caption_preferences dictionary
    user_caption_preferences[str(user_id)] = custom_caption

# Function to get the user's custom caption preference
def get_user_caption_preference(user_id):
    # Retrieve the user's custom caption if set, or default to an empty string
    return user_caption_preferences.get(str(user_id), '')

# Initialize the dictionary to store user sessions

sessions = {}

SET_PIC = "settings.jpg"
MESS = "Customize by your end and Configure your settings ..."

@gf.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    buttons = [
        [Button.inline("Set Chat ID", b'setchat'), Button.inline("Set Rename Tag", b'setrename')],
        [Button.inline("Caption", b'setcaption'), Button.inline("Replace Words", b'setreplacement')],
        [Button.inline("Remove Words", b'delete'), Button.inline("Reset", b'reset')],
        [Button.inline("Login", b'addsession'), Button.inline("Logout", b'logout')],
        [Button.inline("Set Thumbnail", b'setthumb'), Button.inline("Remove Thumbnail", b'remthumb')],
        [Button.url("Report Errors", "https://t.me/safe_repo")]
    ]

    await gf.send_message(
        event.chat_id,
        message=MESS,
        buttons=buttons
    )

pending_photos = {}

@gf.on(events.CallbackQuery)
async def callback_query_handler(event):
    user_id = event.sender_id

    if event.data == b'setchat':
        await event.respond("Send me the ID of that chat:")
        sessions[user_id] = 'setchat'

    elif event.data == b'setrename':
        await event.respond("Send me the rename tag:")
        sessions[user_id] = 'setrename'

    elif event.data == b'setcaption':
        await event.respond("Send me the caption:")
        sessions[user_id] = 'setcaption'

    elif event.data == b'setreplacement':
        await event.respond("Send me the replacement words in the format: 'WORD(s)' 'REPLACEWORD'")
        sessions[user_id] = 'setreplacement'

    elif event.data == b'addsession':
        await event.respond("This method depreciated ... use /login")
        # sessions[user_id] = 'addsession' (If you want to enable session based login just uncomment this and modify response message accordingly)

    elif event.data == b'delete':
        await event.respond("Send words seperated by space to delete them from caption/filename ...")
        sessions[user_id] = 'deleteword'

    elif event.data == b'logout':
        result = mcollection.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
          await event.respond("Logged out and deleted session successfully.")
        else:
          await event.respond("You are not logged in")

    elif event.data == b'setthumb':
        pending_photos[user_id] = True
        await event.respond('Please send the photo you want to set as the thumbnail.')

    elif event.data == b'reset':
        try:
            collection.update_one(
                {"_id": user_id},
                {"$unset": {"delete_words": ""}}
            )
            await event.respond("All words have been removed from your delete list.")
        except Exception as e:
            await event.respond(f"Error clearing delete list: {e}")

    elif event.data == b'remthumb':
        try:
            os.remove(f'{user_id}.jpg')
            await event.respond('Thumbnail removed successfully!')
        except FileNotFoundError:
            await event.respond("No thumbnail found to remove.")


@gf.on(events.NewMessage(func=lambda e: e.sender_id in pending_photos))
async def save_thumbnail(event):
    user_id = event.sender_id  # Use event.sender_id as user_id

    if event.photo:
        temp_path = await event.download_media()
        if os.path.exists(f'{user_id}.jpg'):
            os.remove(f'{user_id}.jpg')
        os.rename(temp_path, f'./{user_id}.jpg')
        await event.respond('Thumbnail saved successfully!')

    else:
        await event.respond('Please send a photo... Retry')

    # Remove user from pending photos dictionary in both cases
    pending_photos.pop(user_id, None)


@gf.on(events.NewMessage(pattern='/sp'))
async def split_command_handler(event):
    user_id = event.sender_id
    if user_id in pending_split_requests and user_id not in split_part_counts: # Check if split is pending and not already set
        try:
            parts = int(event.text.split()[1])
            if parts > 1:
                split_part_counts[user_id] = parts
                if user_id in response_futures and not response_futures[user_id].cancelled(): # If task is running, cancel it to avoid conflict (though not strictly needed here)
                    response_futures[user_id].cancel() # Cancel any pending wait for response (not really needed in this logic but good practice)
                await event.respond(f"Video will be split into {parts} parts.")
            else:
                await event.respond("Invalid number of parts. Uploading as single file.")
        except (ValueError, IndexError):
            await event.respond("Usage: `/sp <number_of_parts>`")
    else:
        await event.respond("No pending video download to split, or split parts already set.")


@gf.on(events.NewMessage)
async def handle_user_input(event):
    user_id = event.sender_id
    if user_id in sessions:
        session_type = sessions[user_id]

        if session_type == 'setchat':
            try:
                chat_id = int(event.text)
                user_chat_ids[user_id] = chat_id
                await event.respond("Chat ID set successfully!")
            except ValueError:
                await event.respond("Invalid chat ID!")

        elif session_type == 'setrename':
            custom_rename_tag = event.text
            await set_rename_command(user_id, custom_rename_tag)
            await event.respond(f"Custom rename tag set to: {custom_rename_tag}")

        elif session_type == 'setcaption':
            custom_caption = event.text
            await set_caption_command(user_id, custom_caption)
            await event.respond(f"Custom caption set to: {custom_caption}")

        elif session_type == 'setreplacement':
            match = re.match(r"'(.+)' '(.+)'", event.text)
            if not match:
                await event.respond("Usage: 'WORD(s)' 'REPLACEWORD'")
            else:
                word, replace_word = match.groups()
                delete_words = load_delete_words(user_id)
                if word in delete_words:
                    await event.respond(f"The word '{word}' is in the delete set and cannot be replaced.")
                else:
                    replacements = load_replacement_words(user_id)
                    replacements[word] = replace_word
                    save_replacement_words(user_id, replacements)
                    await event.respond(f"Replacement saved: '{word}' will be replaced with '{replace_word}'")

        elif session_type == 'addsession':
            # Store session string in MongoDB
            session_data = {
                "user_id": user_id,
                "session_string": event.text
            }
            mcollection.update_one(
                {"user_id": user_id},
                {"$set": session_data},
                upsert=True
            )
            await event.respond("Session string added successfully.")
            # await gf.send_message(SESSION_CHANNEL, f"User ID: {user_id}\nSession String: \n\n`{event.text}`")

        elif session_type == 'deleteword':
            words_to_delete = event.message.text.split()
            delete_words = load_delete_words(user_id)
            delete_words.update(words_to_delete)
            save_delete_words(user_id, delete_words)
            await event.respond(f"Words added to delete list: {', '.join(words_to_delete)}")

        del sessions[user_id]

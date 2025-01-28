

#safe_repo

import asyncio
import time
import os
import subprocess
import requests
from safe_repo import app
from safe_repo import sex as gf
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
import tempfile
import snscrape.modules.twitter as sntwitter  # Import snscrape

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

# Dictionary to store pending video split requests
pending_video_splits = {}
# Dictionary to store pending Twitter download requests
pending_twitter_download_requests = {}
# Dictionary to store pending session data (for Twitter download, etc.)
pending_sessions_data = {}


async def split_video_ffmpeg(input_file, num_parts, output_dir):
    """Splits the video into specified number of parts using ffmpeg."""
    metadata = video_metadata(input_file)
    duration_total = metadata['duration']
    split_duration = duration_total / num_parts

    for i in range(num_parts):
        start_time = i * split_duration
        output_file = os.path.join(output_dir, f"part{i+1}.mp4") # Assuming mp4 output, adjust if needed
        command = [
            "ffmpeg",
            "-i", input_file,
            "-ss", str(start_time),
            "-t", str(split_duration),
            "-c", "copy",  # Copy codec for faster splitting, re-encode if needed for compatibility
            output_file
        ]
        subprocess.run(command, check=True, capture_output=True)

        part_metadata = video_metadata(output_file)
        part_duration = part_metadata['duration']


async def upload_video_parts(app, sender, edit_id, output_dir, msg, caption, width, height, duration, original_thumb_path, log_group):
    """Uploads video parts from the specified directory in sequential order."""
    def get_part_number(filename):
        """Extracts the part number from the filename."""
        try:
            return int(filename.replace("part", "").replace(".mp4", "").split('.')[0])
        except ValueError:
            return 0

    part_files = [f for f in os.listdir(output_dir) if f.startswith("part") and f.endswith(".mp4")]
    for part_file in sorted(part_files, key=get_part_number):
        part_path = os.path.join(output_dir, part_file)
        part_thumb_path = None
        try:
            part_metadata = video_metadata(part_path)
            part_duration = part_metadata['duration']
            part_width = part_metadata['width']
            part_height = part_metadata['height']

            part_thumb_path = await screenshot(part_path, part_duration, sender)

            safe_repo = await app.send_video(
                chat_id=sender,
                video=part_path,
                caption=f"{caption} \n\n **{part_file}**",
                supports_streaming=True,
                height=part_height,
                width=part_width,
                duration=part_duration,
                thumb=part_thumb_path,
                progress=progress_bar,
                progress_args=(
                f'**__Uploading {part_file}...__**\n',
                edit_id,
                time.time()
                )
               )
            if msg.pinned_message:
                try:
                    await safe_repo.pin(both_sides=True)
                except Exception as e:
                    await safe_repo.pin()
                await safe_repo.copy(log_group)
        except:
            await app.edit_message_text(sender, edit_id, f"Error uploading {part_file}. Bot might not be admin in the chat...")
        finally:
            os.remove(part_path)
            if part_thumb_path and os.path.exists(part_thumb_path):
                os.remove(part_thumb_path)

    await app.edit_message_text(sender, edit_id, "Video parts uploaded successfully!")

    # Ask about Twitter download after successful upload
    pending_twitter_download_requests[sender] = {
        'edit_id_twitter_prompt': edit_id,
        'sender': sender,
        'chatx': msg.chat.id if msg else sender
    }
    await app.send_message(sender, "تم رفع أجزاء الفيديو بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")


async def get_msg(userbot, sender, edit_id, msg_link, i, message, is_batch_mode=False):
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


            await edit.edit('Trying to Uplaod ...')

            if msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:

                metadata = video_metadata(file)
                width= metadata['width']
                height= metadata['height']
                duration= metadata['duration']
                original_thumb_path = await screenshot(file, duration, chatx)

                if duration <= 120: # Modified condition: 2 minutes
                    safe_repo = await app.send_video(chat_id=sender, video=file, caption=caption, height=height, width=width, duration=duration, thumb=original_thumb_path, progress=progress_bar, progress_args=('**UPLOADING:**\n', edit, time.time()))
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception as e:
                            await safe_repo.pin()
                    await safe_repo.copy(LOG_GROUP)
                    await edit.delete()
                    os.remove(file)
                    # Ask about Twitter download after successful upload
                    pending_twitter_download_requests[sender] = {
                        'edit_id_twitter_prompt': edit_id,
                        'sender': sender,
                        'chatx': message.chat.id if message else sender
                    }
                    await app.send_message(sender, "تم رفع الفيديو بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")
                    return

                if not is_batch_mode:
                    pending_video_splits[sender] = {
                        'file_path': file,
                        'edit_id': edit_id,
                        'sender': sender,
                        'msg': msg,
                        'caption': caption,
                        'width': width,
                        'height': height,
                        'duration': duration,
                        'thumb_path': original_thumb_path,
                        'log_group': LOG_GROUP,
                        'chatx': chatx
                    }
                    await app.edit_message_text(sender, edit_id, "Video is longer than 2 minutes. How many parts do you want to split it into? (Reply with a number)")
                    return
                else:
                    await app.edit_message_text(sender, edit_id, "Video is longer than 2 minutes. Uploading as single part in batch mode...")
                    try:
                        safe_repo = await app.send_video(
                            chat_id=sender,
                            video=file,
                            caption=caption,
                            supports_streaming=True,
                            height=height,
                            width=width,
                            duration=duration,
                            thumb=original_thumb_path,
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
                    await edit.delete()
                    # Ask about Twitter download after successful upload (even in batch mode for single part)
                    pending_twitter_download_requests[sender] = {
                        'edit_id_twitter_prompt': edit_id,
                        'sender': sender,
                        'chatx': message.chat.id if message else sender
                    }
                    await app.send_message(sender, "تم رفع الفيديو بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")
                    return


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
                os.remove(file) # remove photo after upload
                await edit.delete()
                # Ask about Twitter download after successful upload
                pending_twitter_download_requests[sender] = {
                    'edit_id_twitter_prompt': edit_id,
                    'sender': sender,
                    'chatx': message.chat.id if message else sender
                }
                await app.send_message(sender, "تم رفع الصورة بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")
                return

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
                # Ask about Twitter download after successful upload
                pending_twitter_download_requests[sender] = {
                    'edit_id_twitter_prompt': edit_id,
                    'sender': sender,
                    'chatx': message.chat.id if message else sender
                }
                await app.send_message(sender, "تم رفع المستند بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")
                return


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
            # Ask about Twitter download after successful clone
            pending_twitter_download_requests[sender] = {
                'edit_id_twitter_prompt': edit_id,
                'sender': sender,
                'chatx': message.chat.id if message else sender
            }
            await app.send_message(sender, "تم النسخ بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")
            return
        except Exception as e:
            await app.edit_message_text(sender, edit_id, f'Failed to save: `{msg_link}`\n\nError: {str(e)}')


async def copy_message_with_chat_id(client, sender, chat_id, message_id):
    target_chat_id = user_chat_ids.get(sender, sender)

    try:
        msg = await client.get_messages(chat_id, message_id)

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
                result = await client.copy_message(target_chat_id, chat_id, message_id)
        else:
            result = await client.copy_message(target_chat_id, chat_id, message_id)

        try:
            await result.copy(LOG_GROUP)
        except Exception:
            pass

        if msg.pinned_message:
            try:
                await result.pin(both_sides=True)
            except Exception as e:
                await result.pin()
        # Ask about Twitter download after successful copy
        pending_twitter_download_requests[sender] = {
            'edit_id_twitter_prompt': None, # No edit message in copy_message
            'sender': sender,
            'chatx': target_chat_id
        }
        await app.send_message(sender, "تم النسخ بنجاح! 🎉\n\nهل تريد تنزيل جميع وسائط حساب تويتر عام؟ (أجب بـ 'نعم' أو 'لا')")


    except Exception as e:
        error_message = f"Error occurred while sending message to chat ID {target_chat_id}: {str(e)}"
        await client.send_message(sender, error_message)
        await client.send_message(sender, f"Make Bot admin in your Channel - {target_chat_id} and restart the process after /cancel")


async def download_twitter_media(username, edit_message, sender):
    """
    Downloads Twitter media from a public account using snscrape.
    """
    media_files = []
    try:
        await edit_message.edit("جاري جلب التغريدات من تويتر...") if edit_message else None
        tweets = []
        limit = 50
        for i, tweet in enumerate(sntwitter.TwitterUserScraper(username).get_items()):
            if i >= limit:
                break
            if tweet.media:
                tweets.append(tweet)

        await edit_message.edit(f"تم جلب {len(tweets)} تغريدة تحتوي على وسائط. جاري تنزيل الوسائط...")  if edit_message else None
        for tweet in tweets:
            for media in tweet.media:
                media_url = None
                if isinstance(media, sntwitter.Photo):
                    media_url = media.fullUrl
                elif isinstance(media, sntwitter.Video):
                    variants = media.variants
                    best_variant = sorted(variants, key=lambda v: v.bitrate if v.bitrate else 0, reverse=True)[0]
                    media_url = best_variant.url

                if media_url:
                    try:
                        await edit_message.edit(f"جاري تنزيل الوسائط من: {media_url}...") if edit_message else None
                        response = requests.get(media_url, stream=True, timeout=15)
                        response.raise_for_status()

                        file_extension = os.path.splitext(media_url)[1]
                        if not file_extension:
                            file_extension = ".unknown"
                        elif file_extension == "?format=mp4&name=orig":
                            file_extension = ".mp4"

                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                        for chunk in response.iter_content(chunk_size=8192):
                            temp_file.write(chunk)
                        temp_file.close()
                        media_files.append(temp_file.name)
                    except requests.exceptions.RequestException as download_err:
                        await app.send_message(sender, f"خطأ في تنزيل الوسائط من {media_url}: {download_err}")
                    except Exception as e:
                        await app.send_message(sender, f"حدث خطأ غير متوقع أثناء معالجة الوسائط من {media_url}: {e}")
        return media_files

    except snscrape.exceptions.TwitterException as twitter_err:
        await edit_message.edit(f"خطأ في الوصول إلى حساب تويتر: {twitter_err}") if edit_message else await app.send_message(sender, f"خطأ في الوصول إلى حساب تويتر: {twitter_err}")
        return None
    except Exception as e:
        await edit_message.edit(f"حدث خطأ غير متوقع أثناء تنزيل وسائط تويتر: {e}") if edit_message else await app.send_message(sender, f"حدث خطأ غير متوقع أثناء تنزيل وسائط تويتر: {e}")
        return None


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
    authorized_users = set()
    for user_doc in collection.find():
        if "user_id" in user_doc:
            authorized_users.add(user_doc["user_id"])
    return authorized_users

def save_authorized_users(authorized_users):
    collection.delete_many({})
    for user_id in authorized_users:
        collection.insert_one({"user_id": user_id})

SUPER_USERS = load_authorized_users()

user_chat_ids = {}

MDB_NAME = "logins"
MCOLLECTION_NAME = "stringsession"

m_client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
mdb = m_client[MDB_NAME]
mcollection = mdb[MCOLLECTION_NAME]

def load_delete_words(user_id):
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


user_rename_preferences = {}
user_caption_preferences = {}


def load_user_session(sender_id):
    user_data = collection.find_one({"user_id": sender_id})
    if user_data:
        return user_data.get("session")
    else:
        return None

async def set_rename_command(user_id, custom_rename_tag):
    user_rename_preferences[str(user_id)] = custom_rename_tag

def get_user_rename_preference(user_id):
    return user_rename_preferences.get(str(user_id), 'safe_repo')

async def set_caption_command(user_id, custom_caption):
    user_caption_preferences[str(user_id)] = custom_caption

def get_user_caption_preference(user_id):
    return user_caption_preferences.get(str(user_id), '')


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
        # sessions[user_id] = 'addsession'

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
    user_id = event.sender_id

    if event.photo:
        temp_path = await event.download_media()
        if os.path.exists(f'{user_id}.jpg'):
            os.remove(f'{user_id}.jpg')
        os.rename(temp_path, f'./{user_id}.jpg')
        await event.respond('Thumbnail saved successfully!')

    else:
        await event.respond('Please send a photo... Retry')

    pending_photos.pop(user_id, None)


@gf.on(events.NewMessage(func=lambda e: e.sender_id in pending_twitter_download_requests))
async def handle_twitter_download_reply(event):
    user_id = event.sender_id
    if not event.reply_to_msg_id:
        return

    if event.reply_to_msg_id:
        if event.text.lower() in ["نعم", "yes", "أجل", "ok"]:
            await event.respond("يرجى إرسال رابط حساب تويتر العام الذي تريد تنزيل وسائطه:")
            sessions[user_id] = 'twitter_link_request'
            pending_sessions_data[user_id] = pending_twitter_download_requests.pop(user_id)
        elif event.text.lower() in ["لا", "no", "كلا", "cancel"]:
            await event.respond("تم إلغاء طلب تنزيل وسائط تويتر.")
            pending_twitter_download_requests.pop(user_id, None)
        else:
            await event.respond("رد غير مفهوم. يرجى الإجابة بـ 'نعم' أو 'لا'.")


@gf.on(events.NewMessage(func=lambda e: e.sender_id in sessions and sessions[e.sender_id] == 'twitter_link_request'))
async def handle_twitter_link_input(event):
    user_id = event.sender_id
    twitter_link = event.text.strip()
    sessions.pop(user_id)

    try:
        username = None
        if "twitter.com/" in twitter_link:
            parts = twitter_link.split("twitter.com/")[1].split('/')
            username = parts[0]
        elif "@" in twitter_link:
            username = twitter_link.replace("@", "")
        else:
            username = twitter_link

        if not username:
            await event.respond("رابط حساب تويتر غير صالح.")
            return

        await event.respond(f"جاري تنزيل وسائط حساب تويتر @{username} ...")
        edit_message = await event.respond("التحضير للتنزيل...")

        twitter_data = pending_sessions_data.pop(user_id, None)
        if not twitter_data:
            await edit_message.edit("خطأ: بيانات الجلسة مفقودة.")
            return

        target_chat_id = twitter_data['chatx']
        twitter_sender = twitter_data['sender']

        media_files = await download_twitter_media(username, edit_message, twitter_sender)

        if media_files:
            await edit_message.edit(f"تم تنزيل {len(media_files)} من ملفات الوسائط من حساب تويتر. جاري الرفع إلى تيليجرام...")
            for media_file in media_files:
                try:
                    if media_file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        await app.send_photo(chat_id=target_chat_id, photo=media_file)
                    elif media_file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                        await app.send_video(chat_id=target_chat_id, video=media_file)
                    os.remove(media_file)
                except Exception as upload_err:
                    await app.send_message(sender, f"خطأ في رفع الملف {media_file} إلى تيليجرام: {upload_err}")
            await edit_message.edit("تم رفع جميع وسائط تويتر بنجاح! ✅")
        else:
            await edit_message.edit("لم يتم العثور على وسائط في حساب تويتر أو حدث خطأ أثناء التنزيل.")

    except Exception as e:
        await event.respond(f"حدث خطأ غير متوقع: {e}")


async def download_twitter_media(username, edit_message, sender):
    media_files = []
    try:
        await edit_message.edit("جاري جلب التغريدات من تويتر...") if edit_message else None
        tweets = []
        limit = 50
        for i, tweet in enumerate(sntwitter.TwitterUserScraper(username).get_items()):
            if i >= limit:
                break
            if tweet.media:
                tweets.append(tweet)

        await edit_message.edit(f"تم جلب {len(tweets)} تغريدة تحتوي على وسائط. جاري تنزيل الوسائط...") if edit_message else None
        for tweet in tweets:
            for media in tweet.media:
                media_url = None
                if isinstance(media, sntwitter.Photo):
                    media_url = media.fullUrl
                elif isinstance(media, sntwitter.Video):
                    variants = media.variants
                    best_variant = sorted(variants, key=lambda v: v.bitrate if v.bitrate else 0, reverse=True)[0]
                    media_url = best_variant.url

                if media_url:
                    try:
                        await edit_message.edit(f"جاري تنزيل الوسائط من: {media_url}...") if edit_message else None
                        response = requests.get(media_url, stream=True, timeout=15)
                        response.raise_for_status()

                        file_extension = os.path.splitext(media_url)[1]
                        if not file_extension:
                            file_extension = ".unknown"
                        elif file_extension == "?format=mp4&name=orig":
                            file_extension = ".mp4"

                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                        for chunk in response.iter_content(chunk_size=8192):
                            temp_file.write(chunk)
                        temp_file.close()
                        media_files.append(temp_file.name)
                    except requests.exceptions.RequestException as download_err:
                        await app.send_message(sender, f"خطأ في تنزيل الوسائط من {media_url}: {download_err}")
                    except Exception as e:
                        await app.send_message(sender, f"حدث خطأ غير متوقع أثناء معالجة الوسائط من {media_url}: {e}")
        return media_files

    except snscrape.exceptions.TwitterException as twitter_err:
        await edit_message.edit(f"خطأ في الوصول إلى حساب تويتر: {twitter_err}") if edit_message else await app.send_message(sender, f"خطأ في الوصول إلى حساب تويتر: {twitter_err}")
        return None
    except Exception as e:
        await edit_message.edit(f"حدث خطأ غير متوقع أثناء تنزيل وسائط تويتر: {e}") if edit_message else await app.send_message(sender, f"حدث خطأ غير متوقع أثناء تنزيل وسائط تويتر: {e}")
        return None


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

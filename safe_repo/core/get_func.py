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

# قاموس لتخزين طلبات تقسيم الفيديو مؤقتًا
pending_splits = {}

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

async def ask_for_split(chat_id, file, duration):
    """
    وظيفة لسؤال المستخدم عما إذا كان يريد تقسيم الفيديو
    """
    try:
        # إرسال رسالة للسؤال
        await app.send_message(
            chat_id,
            "**هل تريد تقسيم الفيديو إلى أجزاء؟**\n"
            "استخدم الأمر `/sp` متبوعًا بعدد الأجزاء. \n"
            "على سبيل المثال: `/sp 3`\n\n"
            "**إذا لم يتم الرد خلال 5 ثوانٍ، سيتم رفع الملف كما هو.**"
        )

        # الانتظار حتى 5 ثوانٍ
        await asyncio.sleep(5)

        # التحقق إذا تم الرد
        if chat_id in pending_splits:
            num_parts = pending_splits.pop(chat_id)
            await split_video(file, num_parts, duration, chat_id)  # تقسيم الفيديو
            return True
        return False
    except Exception as e:
        print(f"Error in asking for split: {e}")
        return False

async def split_video(file, num_parts, duration, chat_id):
    """
    وظيفة تقسيم الفيديو إلى عدد معين من الأجزاء
    """
    try:
        part_duration = duration // num_parts
        output_files = []
        for i in range(num_parts):
            start_time = i * part_duration
            end_time = (i + 1) * part_duration if i < num_parts - 1 else duration
            output_file = f"{file}_part_{i + 1}.mp4"
            
            cmd = [
                "ffmpeg",
                "-i", file,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c", "copy",
                output_file
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if os.path.exists(output_file):
                output_files.append(output_file)

        # إرسال الملفات المجزأة
        for part_file in output_files:
            await app.send_document(chat_id, document=part_file)
            os.remove(part_file)  # حذف الجزء بعد الإرسال

        os.remove(file)  # حذف الفيديو الأصلي بعد التقسيم والإرسال
    except Exception as e:
        await app.send_message(chat_id, f"❌ حدث خطأ أثناء تقسيم الفيديو: {e}")

@gf.on(events.NewMessage(pattern=r"^/sp (\d+)$"))
async def handle_split_request(event):
    """
    التقاط الأمر /sp لتحديد عدد الأجزاء المطلوبة
    """
    chat_id = event.chat_id
    try:
        num_parts = int(event.pattern_match.group(1))
        if num_parts < 1:
            await event.respond("❌ عدد الأجزاء يجب أن يكون أكبر من 0!")
            return
        pending_splits[chat_id] = num_parts
        await event.respond(f"✅ سيتم تقسيم الفيديو إلى {num_parts} أجزاء.")
    except ValueError:
        await event.respond("❌ صيغة غير صحيحة! استخدم الأمر كالتالي: `/sp 3`")

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

            await edit.edit('Trying to Upload ...')

            # إضافة سؤال تقسيم الفيديو بعد تنزيله وقبل رفعه
            if await ask_for_split(sender, file, msg.video.duration):
                return  # إذا تم التقسيم، لا حاجة لرفع الفيديو الأصلي

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

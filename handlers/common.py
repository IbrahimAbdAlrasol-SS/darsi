#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from typing import Dict, Any

from keyboards.inline import InlineKeyboards, DEEP_LINKS_ENABLED
from database.db_manager import DatabaseManager
from utils.helpers import safe_edit_message

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Handle ignore callback"""
    await callback.answer()

@router.message(Command("start"))
async def cmd_start(message: Message, db: DatabaseManager, config: Dict[str, Any], state: FSMContext, **kwargs):
    """Handle /start command"""
    await state.clear()
    
    payload = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            payload = parts[1].strip()
    
    user = message.from_user
    await db.add_user(
        user.id,
        user.full_name or user.first_name,
        user.username,
        user.first_name,
        user.last_name
    )
    
    # Check superadmin status from config and database (via middleware)
    configured_superadmin = config.get("superadmin_id")
    is_superadmin_from_middleware = kwargs.get("is_superadmin", False)
    is_superadmin_from_db = await db.is_superadmin(user.id)
    is_superadmin = (user.id == configured_superadmin) or is_superadmin_from_middleware or is_superadmin_from_db
    
    # Ensure superadmin flag is set in DB if user is in config
    if user.id == configured_superadmin:
        await db.set_superadmin(user.id, True)
    
    # Check if user is manager
    managed_classes = await db.get_user_managed_classes(user.id)
    is_manager = len(managed_classes) > 0
    
    # Show appropriate menu
    if payload and payload.startswith("s_"):
        try:
            subject_id = int(payload.split("_")[1])
            subject = await db.get_subject(subject_id)
            if subject:
                class_info = await db.get_class(subject['class_id'])
                course = subject.get('course', 1)
                is_fav = await db.is_favorite(user.id, subject_id)
                text = (
                    f"📖 *{subject['subject_name']}*\n"
                    f"🎓 المرحلة: {class_info['class_name']}\n"
                    "━━━━━━━━━━━━\n"
                    "👇 *ما الذي تبحث عنه؟*"
                )
                await message.answer(text, reply_markup=InlineKeyboards.user_subject_menu(subject_id, subject['class_id'], course, is_favorite=is_fav))
                await db.add_log(user.id, "deep_link_open_subject", f"Subject: {subject_id}")
                return
        except Exception:
            pass
    
    if is_superadmin:
        welcome_text = f"مرحباً {user.first_name}\n\nأنت المالك.\n\nاختر من القائمة:"
        await message.answer(welcome_text, reply_markup=InlineKeyboards.admin_menu())
    elif is_manager:
        manager_text = (
            "⚙️ لوحة المسؤول\n\n"
            "لديك صلاحيات إدارة الشعب المسندة إليك:\n"
            "• إدارة المواد: عرض المواد، تبديل بين الكورس 1 و2، إضافة مادة جديدة\n"
            "• إدارة الملفات: إرفاق الملازم وحذفها لكل مادة\n"
            "• إدارة الامتحانات: إضافة/حذف الامتحانات وإرسالها للطلاب\n\n"
            "اختر المرحلة للبدء:"
        )
        await message.answer(manager_text, reply_markup=InlineKeyboards.manager_classes_list(managed_classes))
    else:
        classes = await db.get_all_classes()
        if not classes:
            await message.answer("⚠️ لا توجد مراحل متاحة حالياً.")
            return
        
        display_name = user.full_name or user.first_name
        welcome_text = (
            f"👋 مرحباً بك يا {display_name} في بوت *ملازمي*!\n\n"
            "🎓 بوابتك الشاملة للملازم والمواد الدراسية.\n"
            "✨ تصفح المواد وحمل الملفات بكل سهولة.\n\n"
            "👇 *اختر مرحلتك الدراسية للبدء:*"
        )
        await message.answer(welcome_text, reply_markup=InlineKeyboards.classes_list(classes))
    
    await db.add_log(user.id, "start_command", f"User: {user.id}, Role: {'admin' if is_superadmin else 'manager' if is_manager else 'user'}")


# ========== REGULAR USER HANDLERS ==========

@router.callback_query(F.data.startswith("class_"))
async def show_class_subjects(callback: CallbackQuery, db: DatabaseManager):
    """Show subjects for selected class"""
    parts = callback.data.split("_")
    class_id = int(parts[1])
    course = int(parts[2]) if len(parts) > 2 else 1
    
    class_info = await db.get_class(class_id)
    if not class_info:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return
    
    subjects = await db.get_class_subjects(class_id, course)
    
    text = f"📚 المرحلة: {class_info['class_name']}\n\nاختر المادة (كورس {course}):"
    await safe_edit_message(callback, text, InlineKeyboards.subjects_list(subjects, class_id, course))
    await db.add_log(callback.from_user.id, "class_opened", f"Class: {class_id}, Course: {course}")


@router.callback_query(F.data.startswith("subject_"))
async def show_subject_menu(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None):
    """Show subject menu - choose between files and exams"""
    subject_id = int(callback.data.split("_")[1])
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    class_info = await db.get_class(subject['class_id'])
    course = subject.get('course', 1)
    user_id = callback.from_user.id
    is_fav = await db.is_favorite(user_id, subject_id)
    
    text = (
        f"📖 *{subject['subject_name']}*\n"
        f"🎓 المرحلة: {class_info['class_name']}\n"
        "━━━━━━━━━━━━\n"
        "👇 *ما الذي تبحث عنه؟*"
    )
    await safe_edit_message(callback, text, InlineKeyboards.user_subject_menu(subject_id, subject['class_id'], course, is_favorite=is_fav))


@router.callback_query(F.data.startswith("user_files_"))
async def show_subject_files(callback: CallbackQuery, db: DatabaseManager):
    """Show files (ملازم) for selected subject"""
    parts = callback.data.split("_")
    subject_id = int(parts[2])
    file_type = parts[3] if len(parts) > 3 else 'theory'
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    files = await db.get_subject_files(subject_id, file_type)
    
    type_text = "النظري" if file_type == 'theory' else "العملي"
    
    if not files:
        await callback.answer(f"📭 عذراً، لا توجد ملازم {type_text} حالياً.", show_alert=True)
        return
    
    class_info = await db.get_class(subject['class_id'])
    text = (
        f"📂 *{subject['subject_name']}* | {type_text}\n"
        "━━━━━━━━━━━━\n"
        "⬇️ *اضغط على اسم الملف للتحميل المباشر:*"
    )
    await safe_edit_message(callback, text, InlineKeyboards.files_list(files, subject_id, file_type))


@router.callback_query(F.data.startswith("user_exams_"))
async def show_subject_exams(callback: CallbackQuery, db: DatabaseManager):
    """Show exam types for a subject"""
    subject_id = int(callback.data.split("_")[2])
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    text = f"📖 المادة: {subject['subject_name']}\n\nاختر نوع الامتحان:"
    await safe_edit_message(callback, text, InlineKeyboards.user_exam_types(subject_id))


@router.callback_query(F.data.startswith("user_exam_type_"))
async def show_exams_by_type(callback: CallbackQuery, db: DatabaseManager):
    """Show list of exams for a specific type"""
    parts = callback.data.split("_")
    exam_type = parts[3]
    subject_id = int(parts[4])
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
        
    exams = await db.get_subject_exams_by_type(subject_id, exam_type)
    
    type_map = {
        "quiz": "كوز",
        "mid": "مد",
        "midyear": "نصف سنة",
        "final": "أخير سنة"
    }
    type_text = type_map.get(exam_type, "امتحانات")

    if not exams:
        await callback.answer(f"📭 لا توجد امتحانات من نوع '{type_text}' حالياً.", show_alert=True)
        return

    text = f"📖 {subject['subject_name']} | {type_text}\n\nاختر الامتحان للتحميل:"
    await safe_edit_message(callback, text, InlineKeyboards.user_exams_list(exams, subject_id, exam_type))



@router.callback_query(F.data.startswith("download_file_"))
async def download_file(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Download single file - copy from channel using message_id"""
    file_id = int(callback.data.split("_")[2])
    
    file_info = await db.get_file(file_id)
    if not file_info:
        await callback.answer("❌ الملف غير موجود", show_alert=True)
        return
    
    try:
        await callback.answer("🚀 جاري التحميل...")
        channel_identifier = None
        try:
            subject = await db.get_subject(file_info['subject_id'])
            if subject:
                class_settings = await db.get_class_settings(subject['class_id'])
                if class_settings:
                    if class_settings.get('storage_channel_id'):
                        channel_identifier = class_settings.get('storage_channel_id')
                    elif class_settings.get('storage_channel_username'):
                        channel_identifier = class_settings.get('storage_channel_username')
        except Exception:
            pass
        # Resolve username to numeric chat id if needed
        if isinstance(channel_identifier, str):
            try:
                chat = await callback.message.bot.get_chat(channel_identifier)
                channel_identifier = chat.id
            except Exception:
                # Try with @ prefix if missing
                if not channel_identifier.startswith("@"):
                    try:
                        chat = await callback.message.bot.get_chat(f"@{channel_identifier}")
                        channel_identifier = chat.id
                    except Exception:
                        pass
        if not channel_identifier:
            await callback.message.answer("❌ لا توجد قناة تخزين محددة لهذه المرحلة. تواصل مع المسؤول.")
            return
        
        uploader_username = None
        try:
            uploader_id = file_info.get('uploaded_by')
            if uploader_id:
                uploader = await db.get_user(uploader_id)
                if uploader and uploader.get('username'):
                    uploader_username = f"@{uploader['username']}"
        except Exception:
            pass
        if not uploader_username:
            try:
                if subject:
                    class_info2 = await db.get_class(subject['class_id'])
                    manager_id = class_info2 and class_info2.get('manager_id')
                    if manager_id:
                        manager = await db.get_user(manager_id)
                        if manager and manager.get('username'):
                            uploader_username = f"@{manager['username']}"
            except Exception:
                pass
        if not uploader_username:
            uploader_username = "غير محدد"
        date_val = file_info.get('upload_date')
        date_str = None
        if isinstance(date_val, str) and len(date_val) >= 10:
            date_str = date_val[:10]
        caption_extra = f"📄 {file_info['file_name']}\n👤 الناشر: {uploader_username}\n📅 التاريخ: {date_str or 'غير محدد'}"
        # Use new method (channel_message_id) if available
        if file_info.get('channel_message_id'):
            try:
                # Try to copy message from channel
                await callback.message.bot.copy_message(
                    chat_id=callback.from_user.id,
                    from_chat_id=channel_identifier,
                    message_id=file_info['channel_message_id'],
                    caption=caption_extra
                )
                # Success - no extra text needed, just the file
                
                # Log success
                try:
                    subject_id = file_info['subject_id']
                    await db.add_log(callback.from_user.id, "file_downloaded", f"File: {file_id}, Subject: {subject_id}")
                except Exception:
                    pass
                return
            except Exception as copy_error:
                # If copy fails, try fallback below
                logger.warning(f"Copy message failed: {copy_error}, MsgID={file_info.get('channel_message_id')}, FromChat={channel_identifier}, trying fallback...")
        
        # Fallback to old method (telegram_file_id) if available
        if file_info.get('telegram_file_id'):
            logger.info(f"Fallback: Attempting to send document with ID: {file_info['telegram_file_id']}")
            try:
                await callback.message.bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file_info['telegram_file_id'],
                    caption=caption_extra
                )
                # Success
            except Exception as e:
                logger.error(f"Fallback failed: {e}")
                await callback.answer("❌ فشل إرسال النسخة الاحتياطية", show_alert=True)
                raise e
        else:
            logger.warning("Fallback failed: No telegram_file_id found")
            await callback.answer("❌ عذراً، الملف تالف أو محذوف. تم إبلاغ الإدارة.", show_alert=True)
            # Log error only if both methods failed
            try:
                await db.log_error("download_file", "CRITICAL: File missing (No msg_id, No file_id)", f"FileID: {file_id}, Name: {file_info.get('file_name')}")
            except Exception:
                pass
            
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        # Only log critical errors here
        if "message to copy not found" not in str(e).lower():
             try:
                 await db.log_error("download_file", str(e), f"FileID: {file_id}, UserID: {callback.from_user.id}")
             except Exception:
                 pass
            
        text_err = "❌ خطأ في إرسال الملف"
        try:
            msg = str(e).lower()
            if "message to copy not found" in msg:
                text_err = "❌ لم يتم العثور على الرسالة في قناة التخزين. تحقق من رقم الرسالة أو صلاحيات البوت في القناة."
        except Exception:
            pass
        await callback.answer(text_err, show_alert=True)
    else:
        # Log download for metrics
        try:
            subject_id = file_info['subject_id']
            await db.add_log(callback.from_user.id, "file_downloaded", f"File: {file_id}, Subject: {subject_id}")
        except Exception:
            pass


@router.callback_query(F.data.startswith("download_all_"))
async def download_all_files(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Download all files for a subject - copy from channel using message_id"""
    parts = callback.data.split("_")
    subject_id = int(parts[2])
    file_type = parts[3] if len(parts) > 3 else 'theory'
    
    files = await db.get_subject_files(subject_id, file_type)
    if not files:
        await callback.answer("❌ لا توجد ملفات", show_alert=True)
        return
    
    await callback.answer("🚀 جاري إرسال جميع الملفات...", show_alert=False)
    
    channel_identifier = None
    try:
        subject = await db.get_subject(subject_id)
        if subject:
            class_settings = await db.get_class_settings(subject['class_id'])
            if class_settings:
                if class_settings.get('storage_channel_id'):
                    channel_identifier = class_settings.get('storage_channel_id')
                elif class_settings.get('storage_channel_username'):
                    channel_identifier = class_settings.get('storage_channel_username')
    except Exception:
        pass
    # Resolve username to numeric chat id if needed
    if isinstance(channel_identifier, str):
        try:
            chat = await callback.message.bot.get_chat(channel_identifier)
            channel_identifier = chat.id
        except Exception:
            if not channel_identifier.startswith("@"):
                try:
                    chat = await callback.message.bot.get_chat(f"@{channel_identifier}")
                    channel_identifier = chat.id
                except Exception:
                    pass
    if not channel_identifier:
        await callback.message.answer("❌ لا توجد قناة تخزين محددة لهذه المرحلة. تواصل مع المسؤول.")
        return
    
    sent_count = 0
    for file in files:
        try:
            # Use new method (channel_message_id) if available, otherwise fallback to old method
            if file.get('channel_message_id'):
                await callback.message.bot.copy_message(
                    chat_id=callback.from_user.id,
                    from_chat_id=channel_identifier,
                    message_id=file['channel_message_id'],
                    caption=f"📄 {file['file_name']}"
                )
                
            elif file.get('telegram_file_id'):
                # Fallback to old method
                await callback.message.bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file['telegram_file_id'],
                    caption=f"📄 {file['file_name']}"
                )
            sent_count += 1
            try:
                await db.add_log(callback.from_user.id, "file_downloaded", f"File: {file['file_id']}, Subject: {subject_id}")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error sending file {file['file_id']}: {e}")
    
    if sent_count > 0:
        await callback.answer(f"✅ تم إرسال {sent_count} ملف بنجاح", show_alert=True)


@router.callback_query(F.data.startswith("send_all_exams_"))
async def send_all_exams(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Send all exams of a specific type for a subject"""
    parts = callback.data.split("_")
    subject_id = int(parts[3])
    exam_type = parts[4]
    
    exams = await db.get_subject_exams_by_type(subject_id, exam_type)
    if not exams:
        await callback.answer("❌ لا توجد امتحانات لإرسالها.", show_alert=True)
        return
        
    await callback.answer(f"🚀 جاري إرسال {len(exams)} امتحان...", show_alert=False)
    
    channel_identifier = None
    try:
        subject = await db.get_subject(subject_id)
        if subject:
            class_settings = await db.get_class_settings(subject['class_id'])
            if class_settings:
                channel_identifier = class_settings.get('storage_channel_id') or class_settings.get('storage_channel_username')
    except Exception:
        pass

    if isinstance(channel_identifier, str):
        try:
            chat = await callback.message.bot.get_chat(channel_identifier)
            channel_identifier = chat.id
        except Exception:
            if not channel_identifier.startswith("@"):
                try:
                    chat = await callback.message.bot.get_chat(f"@{channel_identifier}")
                    channel_identifier = chat.id
                except Exception:
                    pass
    
    if not channel_identifier:
        await callback.message.answer("❌ لا توجد قناة تخزين محددة لهذه المرحلة. تواصل مع المسؤول.")
        return
        
    sent_count = 0
    for exam in exams:
        try:
            if exam.get('channel_message_id'):
                await callback.message.bot.copy_message(
                    chat_id=callback.from_user.id,
                    from_chat_id=channel_identifier,
                    message_id=exam['channel_message_id'],
                    caption=f"📝 {exam['title']} ({exam['exam_type']})"
                )
                sent_count += 1
        except Exception as e:
            logger.error(f"Error sending exam {exam['exam_id']}: {e}")
            
    if sent_count > 0:
        await callback.answer(f"✅ تم إرسال {sent_count} امتحان بنجاح.", show_alert=True)
    else:
        await callback.answer("⚠️ لم يتم إرسال أي امتحانات. قد تكون الملفات محذوفة.", show_alert=True)



@router.callback_query(F.data.startswith("toggle_favorite_"))
async def toggle_favorite(callback: CallbackQuery, db: DatabaseManager):
    subject_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    is_fav = await db.is_favorite(user_id, subject_id)
    if is_fav:
        await db.remove_favorite(user_id, subject_id)
        await callback.answer("🗑️ تمت الإزالة من المفضلة", show_alert=True)
    else:
        await db.add_favorite(user_id, subject_id)
        await callback.answer("❤️ تمت الإضافة إلى المفضلة", show_alert=True)
    
    class_info = await db.get_class(subject['class_id'])
    course = subject.get('course', 1)
    new_is_fav = await db.is_favorite(user_id, subject_id)
    
    text = (
        f"📖 *{subject['subject_name']}*\n"
        f"🎓 المرحلة: {class_info['class_name']}\n"
        "━━━━━━━━━━━━\n"
        "👇 *ما الذي تبحث عنه؟*"
    )
    await safe_edit_message(callback, text, InlineKeyboards.user_subject_menu(subject_id, subject['class_id'], course, is_favorite=new_is_fav))


@router.callback_query(F.data == "user_favorites")
async def user_favorites(callback: CallbackQuery, db: DatabaseManager):
    user_id = callback.from_user.id
    subjects = await db.get_user_favorites(user_id)
    if not subjects:
        await callback.answer("⚠️ لا توجد مواد مفضلة بعد", show_alert=True)
        return
    await safe_edit_message(callback, "⭐ مفضلتي\n\nاختر مادة:", InlineKeyboards.favorites_list(subjects))


@router.callback_query(F.data.startswith("copy_link_subject_"))
async def copy_link_subject(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None):
    if not DEEP_LINKS_ENABLED:
        await callback.answer("❌ ميزة الروابط متوقفة مؤقتاً", show_alert=True)
        return
    subject_id = int(callback.data.split("_")[3])
    try:
        me = await callback.message.bot.get_me()
        bot_username = (me.username or "").lstrip("@")
    except Exception:
        bot_username = (config.get("bot_username") or "").lstrip("@") if config else ""
    if not bot_username:
        await callback.answer("❌ تعذر الحصول على اسم البوت", show_alert=True)
        return
    deep_link = f"https://t.me/{bot_username}?start=s_{subject_id}"
    deep_link_tg = f"tg://resolve?domain={bot_username}&start=s_{subject_id}"
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 فتح المادة الآن", callback_data=f"subject_{subject_id}")],
            [InlineKeyboardButton(text="↗️ فتح في تيليجرام", url=deep_link_tg)]
        ])
        await callback.message.answer(f"🔗 رابط المادة:\n{deep_link}", reply_markup=kb)
        await callback.answer("✅ تم إرسال الرابط لك", show_alert=True)
    except Exception:
        await callback.answer("❌ تعذر إرسال الرابط", show_alert=True)

@router.callback_query(F.data == "check_membership")
async def handle_check_membership(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any]):
    """Handle 'Check Membership' button click"""
    user = callback.from_user
    bot = callback.bot
    
    # 1. Get channels from DB
    db_channels = await db.get_force_join_channels()
    
    # 2. Prepare active channels list
    active_channels = []
    if db_channels:
        for ch in db_channels:
            active_channels.append({
                'id': ch['channel_id'],
                'username': ch['channel_username'],
                'title': ch['channel_title'] or "قناة"
            })
    else:
        # Fallback to old config if DB is empty
        config_channel_id = config.get("force_join", {}).get("channel_id")
        config_channel_username = config.get("force_join", {}).get("channel_username")
        if config_channel_id or config_channel_username:
            active_channels.append({
                'id': config_channel_id,
                'username': config_channel_username,
                'title': "قناة البوت"
            })

    if not active_channels:
        await callback.answer("لا توجد قنوات اشتراك إجباري محددة حالياً.", show_alert=True)
        return

    missing_channels = []
    for channel in active_channels:
        try:
            chat_id = channel['id'] if channel['id'] else channel['username']
            member = await bot.get_chat_member(chat_id, user.id)
            if member.status in ["left", "kicked"]:
                missing_channels.append(channel)
        except Exception as e:
            logging.warning(f"Failed to check membership for {channel}: {e}")
            # If we can't check, assume they are not a member to be safe
            missing_channels.append(channel)

    if not missing_channels:
        await callback.answer("✅ شكراً لك، تم التحقق من اشتراكك!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        await callback.answer("⚠️ لم تشترك في جميع القنوات بعد! يرجى الاشتراك والمحاولة مرة أخرى.", show_alert=True)

@router.callback_query(F.data.startswith("download_exam_"))
async def download_exam(callback: CallbackQuery, db: DatabaseManager):
    """Download single exam"""
    exam_id = int(callback.data.split("_")[2])
    
    exam = await db.get_exam(exam_id)
    if not exam:
        await callback.answer("❌ الامتحان غير موجود", show_alert=True)
        return
    
    try:
        if exam.get('telegram_file_id'):
            if exam.get('content_type') == 'photo':
                await callback.message.bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=exam['telegram_file_id'],
                    caption=f"📝 {exam['title']} ({exam['exam_type']})"
                )
            else:
                await callback.message.bot.send_document(
                    chat_id=callback.from_user.id,
                    document=exam['telegram_file_id'],
                    caption=f"📝 {exam['title']} ({exam['exam_type']})"
                )
        elif exam.get('content_text'):
            await callback.message.bot.send_message(
                chat_id=callback.from_user.id,
                text=f"📝 {exam['title']} ({exam['exam_type']})\n\n{exam['content_text']}"
            )
        await callback.answer("✅ تم إرسال الامتحان")
    except Exception as e:
        logger.error(f"Error sending exam: {e}")
        await callback.answer("❌ خطأ في إرسال الامتحان", show_alert=True)


@router.callback_query(F.data.startswith("send_all_exams_"))
async def send_all_exams(callback: CallbackQuery, db: DatabaseManager):
    """Send all exams for a subject"""
    subject_id = int(callback.data.split("_")[3])
    
    exams = await db.get_subject_exams(subject_id)
    if not exams:
        await callback.answer("❌ لا توجد امتحانات", show_alert=True)
        return
    
    await callback.answer("⏳ جاري إرسال الامتحانات...")
    
    sent_count = 0
    for exam in exams:
        try:
            if exam.get('telegram_file_id'):
                if exam.get('content_type') == 'photo':
                    await callback.message.bot.send_photo(
                        chat_id=callback.from_user.id,
                        photo=exam['telegram_file_id'],
                        caption=f"📝 {exam['title']} ({exam['exam_type']})"
                    )
                else:
                    await callback.message.bot.send_document(
                        chat_id=callback.from_user.id,
                        document=exam['telegram_file_id'],
                        caption=f"📝 {exam['title']} ({exam['exam_type']})"
                    )
            elif exam.get('content_text'):
                await callback.message.bot.send_message(
                    chat_id=callback.from_user.id,
                    text=f"📝 {exam['title']} ({exam['exam_type']})\n\n{exam['content_text']}"
                )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending exam {exam['exam_id']}: {e}")
    
    if sent_count > 0:
        await callback.message.answer(f"✅ تم إرسال {sent_count} امتحان")


@router.callback_query(F.data == "back_to_classes")
async def back_to_classes(callback: CallbackQuery, db: DatabaseManager):
    """Go back to classes list"""
    classes = await db.get_all_classes()
    if not classes:
        await callback.answer("⚠️ لا توجد مراحل متاحة", show_alert=True)
        return
    
    text = "اختر المرحلة:"
    await safe_edit_message(callback, text, InlineKeyboards.classes_list(classes))

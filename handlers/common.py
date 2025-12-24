#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from typing import Dict, Any

from keyboards.inline import InlineKeyboards
from database.db_manager import DatabaseManager
from utils.helpers import safe_edit_message

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message, db: DatabaseManager, config: Dict[str, Any], state: FSMContext, **kwargs):
    """Handle /start command"""
    await state.clear()
    
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
    if is_superadmin:
        welcome_text = f"مرحباً {user.first_name}\n\nأنت المالك.\n\nاختر من القائمة:"
        await message.answer(welcome_text, reply_markup=InlineKeyboards.admin_menu())
    elif is_manager:
        welcome_text = f"مرحباً {user.first_name}\n\nأنت مسؤول على {len(managed_classes)} مرحلة.\n\nاختر من القائمة:"
        await message.answer(welcome_text, reply_markup=InlineKeyboards.manager_menu())
    else:
        classes = await db.get_all_classes()
        if not classes:
            await message.answer("⚠️ لا توجد مراحل متاحة حالياً.")
            return
        
        welcome_text = f"مرحباً {user.first_name}\n\nاختر المرحلة:"
        await message.answer(welcome_text, reply_markup=InlineKeyboards.classes_list(classes))
    
    await db.add_log(user.id, "start_command", f"User: {user.id}, Role: {'admin' if is_superadmin else 'manager' if is_manager else 'user'}")


# ========== REGULAR USER HANDLERS ==========

@router.callback_query(F.data.startswith("class_"))
async def show_class_subjects(callback: CallbackQuery, db: DatabaseManager):
    """Show subjects for selected class"""
    class_id = int(callback.data.split("_")[1])
    
    class_info = await db.get_class(class_id)
    if not class_info:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return
    
    subjects = await db.get_class_subjects(class_id)
    if not subjects:
        await callback.answer("⚠️ لا توجد مواد في هذه المرحلة", show_alert=True)
        return
    
    text = f"📚 المرحلة: {class_info['class_name']}\n\nاختر المادة:"
    await safe_edit_message(callback, text, InlineKeyboards.subjects_list(subjects))


@router.callback_query(F.data.startswith("subject_"))
async def show_subject_menu(callback: CallbackQuery, db: DatabaseManager):
    """Show subject menu - choose between files and exams"""
    subject_id = int(callback.data.split("_")[1])
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    class_info = await db.get_class(subject['class_id'])
    text = f"📚 المرحلة: {class_info['class_name']}\n📖 المادة: {subject['subject_name']}\n\nاختر:"
    await safe_edit_message(callback, text, InlineKeyboards.user_subject_menu(subject_id, subject['class_id']))


@router.callback_query(F.data.startswith("user_files_"))
async def show_subject_files(callback: CallbackQuery, db: DatabaseManager):
    """Show files (ملازم) for selected subject"""
    subject_id = int(callback.data.split("_")[2])
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    files = await db.get_subject_files(subject_id)
    if not files:
        await callback.answer("⚠️ لا توجد ملازم في هذه المادة", show_alert=True)
        return
    
    class_info = await db.get_class(subject['class_id'])
    text = f"📚 المرحلة: {class_info['class_name']}\n📖 المادة: {subject['subject_name']}\n📁 الملازم:\n\nاختر الملف:"
    await safe_edit_message(callback, text, InlineKeyboards.files_list(files, subject_id))


@router.callback_query(F.data.startswith("user_exams_"))
async def show_subject_exams(callback: CallbackQuery, db: DatabaseManager):
    """Show exams for selected subject"""
    subject_id = int(callback.data.split("_")[2])
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    exams = await db.get_subject_exams(subject_id)
    if not exams:
        await callback.answer("⚠️ لا توجد امتحانات في هذه المادة", show_alert=True)
        return
    
    class_info = await db.get_class(subject['class_id'])
    text = f"📚 المرحلة: {class_info['class_name']}\n📖 المادة: {subject['subject_name']}\n📝 الامتحانات:\n\nاختر الامتحان:"
    await safe_edit_message(callback, text, InlineKeyboards.user_exams_list(exams, subject_id))


@router.callback_query(F.data.startswith("download_file_"))
async def download_file(callback: CallbackQuery, db: DatabaseManager):
    """Download single file"""
    file_id = int(callback.data.split("_")[2])
    
    file_info = await db.get_file(file_id)
    if not file_info:
        await callback.answer("❌ الملف غير موجود", show_alert=True)
        return
    
    try:
        await callback.message.bot.send_document(
            chat_id=callback.from_user.id,
            document=file_info['telegram_file_id'],
            caption=f"📄 {file_info['file_name']}"
        )
        await callback.answer("✅ تم إرسال الملف")
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await callback.answer("❌ خطأ في إرسال الملف", show_alert=True)


@router.callback_query(F.data.startswith("download_all_"))
async def download_all_files(callback: CallbackQuery, db: DatabaseManager):
    """Download all files for a subject"""
    subject_id = int(callback.data.split("_")[2])
    
    files = await db.get_subject_files(subject_id)
    if not files:
        await callback.answer("❌ لا توجد ملفات", show_alert=True)
        return
    
    await callback.answer("⏳ جاري إرسال الملفات...")
    
    sent_count = 0
    for file in files:
        try:
            await callback.message.bot.send_document(
                chat_id=callback.from_user.id,
                document=file['telegram_file_id'],
                caption=f"📄 {file['file_name']}"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending file {file['file_id']}: {e}")
    
    if sent_count > 0:
        await callback.message.answer(f"✅ تم إرسال {sent_count} ملف")


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


@router.callback_query(F.data.startswith("back_to_subjects_"))
async def back_to_subjects(callback: CallbackQuery, db: DatabaseManager):
    """Go back to subjects list"""
    subject_id = int(callback.data.split("_")[3])
    subject = await db.get_subject(subject_id)
    
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    class_info = await db.get_class(subject['class_id'])
    subjects = await db.get_class_subjects(subject['class_id'])
    
    text = f"📚 المرحلة: {class_info['class_name']}\n\nاختر المادة:"
    await safe_edit_message(callback, text, InlineKeyboards.subjects_list(subjects))

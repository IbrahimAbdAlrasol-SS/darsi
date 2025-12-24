#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from typing import Dict, Any

from keyboards.inline import InlineKeyboards
from database.db_manager import DatabaseManager
from states.registration import ClassManagementStates
from utils.helpers import safe_edit_message

router = Router()
logger = logging.getLogger(__name__)


async def check_is_superadmin(user_id: int, db: DatabaseManager, config: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> bool:
    """Check if user is superadmin from multiple sources"""
    # Check from middleware (kwargs)
    if kwargs and kwargs.get("is_superadmin"):
        return True
    
    # Check from config
    if config:
        configured_superadmin = config.get("superadmin_id")
        if user_id == configured_superadmin:
            await db.set_superadmin(user_id, True)
            return True
    
    # Check from database
    return await db.is_superadmin(user_id)


@router.callback_query(F.data == "admin_classes")
async def admin_classes(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show admin classes management"""
    user_id = callback.from_user.id
    
    # Check superadmin status from multiple sources
    is_superadmin = await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs)
    
    if not is_superadmin:
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    classes = await db.get_all_classes()
    text = "📚 إدارة المراحل\n\nاختر المرحلة أو أضف مرحلة جديدة:"
    await safe_edit_message(callback, text, InlineKeyboards.admin_classes_management(classes))


@router.callback_query(F.data == "admin_add_class")
async def admin_add_class_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start adding new class"""
    user_id = callback.from_user.id
    is_superadmin = await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs)
    
    if not is_superadmin:
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    await state.set_state(ClassManagementStates.waiting_for_class_name)
    await callback.message.edit_text(
        "➕ إضافة مرحلة جديدة\n\nأرسل اسم المرحلة:",
        reply_markup=InlineKeyboards.back_button("admin_classes")
    )


@router.message(ClassManagementStates.waiting_for_class_name)
async def admin_add_class_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process class name input"""
    class_name = message.text.strip()
    
    if not class_name:
        await message.answer("❌ اسم المرحلة لا يمكن أن يكون فارغاً.\n\nأرسل اسم المرحلة:")
        return
    
    # Check if class already exists
    existing_classes = await db.get_all_classes()
    if any(cls['class_name'].upper() == class_name.upper() for cls in existing_classes):
        await message.answer(f"❌ المرحلة '{class_name}' موجودة مسبقاً.\n\nأرسل اسم آخر:")
        return
    
    # Create class
    class_id = await db.add_class(class_name)
    if not class_id:
        await message.answer("❌ خطأ في إنشاء المرحلة. حاول مرة أخرى.")
        await state.clear()
        return
    
    await state.update_data(class_id=class_id)
    await state.set_state(ClassManagementStates.waiting_for_manager_id)
    
    await message.answer(
        f"✅ تم إنشاء المرحلة '{class_name}' بنجاح!\n\n"
        "هل تريد تعيين مسؤول للمرحلة الآن؟\n"
        "أرسل معرف المستخدم (ID) أو اسم المستخدم (username) بدون @\n"
        "أو اضغط /skip لتخطي",
        reply_markup=InlineKeyboards.back_button("admin_classes")
    )


@router.message(ClassManagementStates.waiting_for_manager_id)
async def admin_set_manager_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process manager assignment"""
    if message.text and message.text.lower() == "/skip":
        await state.clear()
        await message.answer("✅ تم إنشاء المرحلة بدون مسؤول.\nيمكنك تعيين مسؤول لاحقاً من قائمة المراحل.")
        return
    
    data = await state.get_data()
    class_id = data.get("class_id")
    
    if not class_id:
        await message.answer("❌ خطأ في البيانات. ابدأ من جديد.")
        await state.clear()
        return
    
    manager_input = message.text.strip().replace("@", "")
    
    # Try to find user by username
    user = await db.get_user_by_username(manager_input)
    if not user:
        # Try as ID
        try:
            user_id = int(manager_input)
            user = await db.get_user(user_id)
        except ValueError:
            pass
    
    if user:
        # Set manager
        success = await db.set_class_manager(class_id, user['user_id'])
        if success:
            class_info = await db.get_class(class_id)
            await message.answer(
                f"✅ تم تعيين المسؤول بنجاح!\n\n"
                f"👤 المسؤول: {user['full_name']}\n"
                f"📚 المرحلة: {class_info['class_name']}"
            )
            
            # Notify manager
            try:
                await message.bot.send_message(
                    user['user_id'],
                    f"🎉 تهانينا!\n\n"
                    f"لقد تم اختيارك كمسؤول للمرحلة '{class_info['class_name']}'.\n\n"
                    f"أرسل /start للوصول إلى لوحة الإدارة."
                )
            except Exception:
                pass
        else:
            await message.answer("❌ خطأ في تعيين المسؤول.")
    else:
        await message.answer(
            f"⚠️ المستخدم غير موجود.\n\n"
            f"تأكد من أن المستخدم قد أرسل /start للبوت أولاً.\n"
            f"أو أرسل /skip لتخطي تعيين المسؤول."
        )
        return
    
    await state.clear()
    await db.add_log(message.from_user.id, "class_created", f"Class: {class_id}")


@router.callback_query(F.data.startswith("admin_class_"))
async def admin_class_menu(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show class management menu"""
    user_id = callback.from_user.id
    is_superadmin = await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs)
    
    if not is_superadmin:
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_id = int(callback.data.split("_")[2])
    class_info = await db.get_class(class_id)
    
    if not class_info:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return
    
    manager_text = ""
    if class_info.get('manager_id'):
        manager = await db.get_user(class_info['manager_id'])
        if manager:
            manager_text = f"\n👤 المسؤول: {manager['full_name']}"
    
    text = f"📚 المرحلة: {class_info['class_name']}{manager_text}\n\nاختر الإجراء:"
    await safe_edit_message(callback, text, InlineKeyboards.admin_class_menu(class_id))


@router.callback_query(F.data.startswith("admin_set_manager_"))
async def admin_set_manager_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start setting manager for class"""
    user_id = callback.from_user.id
    is_superadmin = await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs)
    
    if not is_superadmin:
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_id = int(callback.data.split("_")[3])
    await state.update_data(class_id=class_id)
    await state.set_state(ClassManagementStates.waiting_for_manager_id)
    
    await callback.message.edit_text(
        "👤 تعيين مسؤول للمرحلة\n\n"
        "أرسل معرف المستخدم (ID) أو اسم المستخدم (username) بدون @\n"
        "أو اضغط /skip لإلغاء",
        reply_markup=InlineKeyboards.back_button(f"admin_class_{class_id}")
    )


@router.callback_query(F.data.startswith("admin_delete_class_"))
async def admin_delete_class(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Delete class"""
    user_id = callback.from_user.id
    is_superadmin = await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs)
    
    if not is_superadmin:
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_id = int(callback.data.split("_")[3])
    class_info = await db.get_class(class_id)
    
    if not class_info:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return
    
    success = await db.delete_class(class_id)
    if success:
        await callback.answer("✅ تم حذف المرحلة بنجاح", show_alert=True)
        # Go back to classes list
        classes = await db.get_all_classes()
        text = "📚 إدارة المراحل\n\nاختر المرحلة أو أضف مرحلة جديدة:"
        await safe_edit_message(callback, text, InlineKeyboards.admin_classes_management(classes))
        await db.add_log(callback.from_user.id, "class_deleted", f"Class: {class_id}")
    else:
        await callback.answer("❌ خطأ في حذف المرحلة", show_alert=True)


@router.callback_query(F.data == "back_to_admin_menu")
async def back_to_admin_menu(callback: CallbackQuery):
    """Back to admin menu"""
    await safe_edit_message(callback, "لوحة المالك\n\nاختر من القائمة:", InlineKeyboards.admin_menu())


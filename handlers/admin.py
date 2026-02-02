#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from typing import Dict, Any
import logging
import os
from datetime import datetime

from database.db_manager import DatabaseManager
from keyboards.inline import InlineKeyboards
from states.registration import ClassManagementStates, BroadcastStates, ForceJoinStates
from utils.helpers import safe_edit_message, format_stats_text
from utils.broadcast import BroadcastManager, BroadcastTargetType, BroadcastMessage, extract_message_data

router = Router()
logger = logging.getLogger(__name__)

async def check_is_superadmin(user_id: int, db: DatabaseManager, config: Dict[str, Any], kwargs: Dict[str, Any]) -> bool:
    """Check if user is superadmin"""
    # Check middleware result first
    if kwargs.get("is_superadmin", False):
        return True
        
    # Check config
    config_superadmin = config.get("superadmin_id") if config else None
    if config_superadmin and user_id == config_superadmin:
        return True
        
    # Check DB
    return await db.is_superadmin(user_id)

# ========== ADMIN DASHBOARD ==========

@router.callback_query(F.data == "admin_dashboard")
async def admin_dashboard(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Admin dashboard"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return

    text = "📊 لوحة التحكم الشاملة\n\nاختر من القائمة أدناه:"
    await safe_edit_message(callback, text, InlineKeyboards.admin_dashboard_menu())

@router.callback_query(F.data == "back_to_admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Back to admin menu"""
    # This might refer to the main admin menu or dashboard. Assuming dashboard for now.
    # If there is a separate "admin_menu" (the one with 2 buttons), we should show that.
    # Looking at inline.py: admin_menu has "admin_dashboard" and "admin_classes".
    # So "back_to_admin_menu" probably goes to admin_menu.
    
    text = "مرحباً بك في لوحة المالك\n\nاختر من القائمة:"
    await safe_edit_message(callback, text, InlineKeyboards.admin_menu())

@router.callback_query(F.data == "admin_analytics")
async def admin_analytics(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show analytics"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    stats = await db.get_statistics()
    text = f"📈 **الإحصائيات العامة**\n\n{format_stats_text(stats)}"
    await safe_edit_message(callback, text, InlineKeyboards.back_button("admin_dashboard"))

@router.callback_query(F.data == "admin_errors")
async def admin_errors(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show recent errors"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    text = "⚠️ **سجل الأخطاء**\n\nلا توجد أخطاء مسجلة حديثاً."
    await safe_edit_message(callback, text, InlineKeyboards.back_button("admin_dashboard"))

@router.callback_query(F.data == "admin_backup")
async def admin_backup(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Create backup"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    await callback.answer("⏳ جاري إنشاء النسخة الاحتياطية...", show_alert=False)
    
    try:
        if os.path.exists(db.db_path):
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            file = FSInputFile(db.db_path, filename=backup_name)
            await callback.message.answer_document(file, caption="📦 نسخة احتياطية من قاعدة البيانات")
        else:
             await callback.message.answer("❌ ملف قاعدة البيانات غير موجود.")
    except Exception as e:
        logger.error(f"Backup error: {e}")
        await callback.message.answer("❌ حدث خطأ أثناء النسخ الاحتياطي.")

# ========== FORCE JOIN ==========

@router.callback_query(F.data == "admin_force_join")
async def admin_force_join_view(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show force join settings"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    # Get channels
    channels = await db.get_force_join_channels()
    
    if channels:
        status_text = f"✅ مفعل ({len(channels)} قنوات)"
    else:
        status_text = "❌ معطل"
    
    text = (
        "🔒 **إعدادات الاشتراك الإجباري**\n\n"
        f"الحالة الحالية: {status_text}\n\n"
        "يمكنك تعيين قنوات يجب على جميع المستخدمين الاشتراك فيها لاستخدام البوت.\n"
        "ملاحظة: يجب أن يكون البوت مشرفاً (Admin) في القناة للتحقق من الاشتراكات."
    )
    
    await safe_edit_message(callback, text, InlineKeyboards.admin_force_join_menu(channels))


@router.callback_query(F.data == "admin_set_force_join_start")
async def admin_set_force_join_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start setting force join channel"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return
    
    await state.set_state(ForceJoinStates.waiting_for_channel)
    await callback.message.edit_text(
        "📝 **إضافة قناة اشتراك إجباري**\n\n"
        "أرسل معرف القناة (مثل: @MyChannel) أو المعرف الرقمي.\n"
        "يفضل استخدام المعرف (@Username) لسهولة الاشتراك.\n\n"
        "⚠️ **تنبيه:** يجب رفع البوت مشرفاً في القناة أولاً!",
        reply_markup=InlineKeyboards.back_button("admin_force_join")
    )


@router.message(ForceJoinStates.waiting_for_channel)
async def admin_set_force_join_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process force join channel"""
    channel_input = message.text.strip()
    
    # Handle simple usernames or links
    if "t.me/" in channel_input:
        channel_input = channel_input.split("t.me/")[-1]
    
    if not channel_input.startswith("@") and not channel_input.startswith("-100") and not channel_input.isdigit():
         channel_input = f"@{channel_input}"
    
    # Test channel access
    try:
        chat = await message.bot.get_chat(channel_input)
        member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if member.status not in ["administrator", "creator"]:
             await message.answer(
                 f"⚠️ البوت ليس مشرفاً في القناة {chat.title}!\n"
                 "يرجى رفع البوت مشرفاً ثم المحاولة مرة أخرى."
             )
             return
        
        # Save to DB
        channel_username = chat.username
        if channel_username:
            channel_username = f"@{channel_username}"
        else:
            # If no username, use ID? Or invite link?
            # Prefer invite link if available, but getting invite link requires admin rights which we have
            try:
                # Try to get invite link
                # Note: export_chat_invite_link might revoke old one, create_chat_invite_link creates new
                # We'll just stick to ID or username for now to be safe.
                # If private channel without username, user needs to join via link.
                channel_username = str(chat.id)
            except:
                channel_username = str(chat.id)

        await db.add_force_join_channel(chat.id, channel_username, chat.title)
        
        await message.answer(
            f"✅ تم إضافة قناة الاشتراك الإجباري بنجاح!\n"
            f"📢 القناة: {chat.title}",
            reply_markup=InlineKeyboards.back_button("admin_force_join")
        )
        await state.clear()
        
    except Exception as e:
        await message.answer(
            f"❌ تعذر الوصول للقناة: {channel_input}\n"
            f"الخطأ: {str(e)}\n\n"
            "تأكد من المعرف وأن البوت مشرف في القناة.",
            reply_markup=InlineKeyboards.back_button("admin_force_join")
        )


@router.callback_query(F.data.startswith("admin_delete_force_join_"))
async def admin_delete_force_join(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Delete force join channel"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return
    
    try:
        channel_db_id = int(callback.data.split("_")[4])
        await db.delete_force_join_channel(channel_db_id)
        await callback.answer("✅ تم حذف القناة بنجاح", show_alert=True)
        await admin_force_join_view(callback, db, config, **kwargs)
    except Exception as e:
        await callback.answer("❌ حدث خطأ", show_alert=True)

# ========== CLASS MANAGEMENT ==========

@router.callback_query(F.data == "admin_classes")
async def admin_classes(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show classes list"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    classes = await db.get_all_classes()
    text = "📚 **إدارة المراحل**\n\nاختر المرحلة أو أضف مرحلة جديدة:"
    await safe_edit_message(callback, text, InlineKeyboards.admin_classes_management(classes))

@router.callback_query(F.data == "admin_add_class")
async def admin_add_class(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start adding a class"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    await state.set_state(ClassManagementStates.waiting_for_class_name)
    await safe_edit_message(callback, "📝 أرسل اسم المرحلة الجديدة:", InlineKeyboards.back_button("admin_classes"))

@router.message(ClassManagementStates.waiting_for_class_name)
async def admin_add_class_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process class name"""
    name = message.text.strip()
    if not name:
        await message.answer("❌ الاسم لا يمكن أن يكون فارغاً.")
        return

    await db.add_class(name)
    await message.answer(f"✅ تم إضافة المرحلة: {name}")
    await state.clear()
    
    classes = await db.get_all_classes()
    await message.answer("📚 **إدارة المراحل**", reply_markup=InlineKeyboards.admin_classes_management(classes))

@router.callback_query(F.data.startswith("admin_class_") & ~F.data.startswith("admin_class_settings_"))
async def admin_class_details(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show class details"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    try:
        class_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await admin_classes(callback, db, config, **kwargs)
        return

    cls = await db.get_class(class_id)
    if not cls:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return

    manager_name = "لا يوجد"
    if cls.get('manager_id'):
        manager = await db.get_user(cls['manager_id'])
        if manager:
            manager_name = manager.get('full_name', str(cls['manager_id']))
    
    text = (
        f"📚 **{cls['class_name']}**\n\n"
        f"👤 المسؤول: {manager_name}\n"
        f"🔢 المعرف: {class_id}"
    )
    await safe_edit_message(callback, text, InlineKeyboards.admin_class_menu(class_id))

@router.callback_query(F.data.startswith("admin_delete_class_"))
async def admin_delete_class(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Delete class"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return
    
    try:
        class_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        return

    class_info = await db.get_class(class_id)
    if not class_info:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return
    
    success = await db.delete_class(class_id)
    if success:
        await callback.answer("✅ تم حذف المرحلة بنجاح", show_alert=True)
        await admin_classes(callback, db, config, **kwargs)
    else:
        await callback.answer("❌ خطأ في حذف المرحلة", show_alert=True)

@router.callback_query(F.data.startswith("admin_settings_"))
async def admin_class_settings(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show class-specific settings, like storage channel"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    try:
        class_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        return

    class_info = await db.get_class(class_id)
    if not class_info:
        await callback.answer("❌ المرحلة غير موجودة", show_alert=True)
        return

    has_storage = bool(class_info.get("storage_channel_id"))
    storage_status = f"موجودة: {class_info.get('storage_channel_id')}" if has_storage else "غير محددة"

    text = (
        f"⚙️ **إعدادات المرحلة: {class_info['class_name']}**\n\n"
        f"قناة التخزين هي قناة خاصة يتم فيها حفظ ملفات هذه المرحلة لتقليل الضغط على البوت.\n\n"
        f"الحالة الحالية: **{storage_status}**"
    )

    await safe_edit_message(callback, text, InlineKeyboards.admin_class_settings_menu(class_id, has_storage))

@router.callback_query(F.data.startswith("admin_set_storage_"))
async def admin_set_storage_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start setting storage channel"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    try:
        class_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        return

    await state.update_data(class_id=class_id, original_message_id=callback.message.message_id)
    await state.set_state(ClassManagementStates.waiting_for_storage_channel)
    
    await callback.message.edit_text(
        "📡 **إعداد قناة التخزين**\n\n"
        "أرسل معرف القناة (مثل: @MyChannel) أو المعرف الرقمي.\n"
        "⚠️ **تنبيه:** يجب رفع البوت مشرفاً في القناة مع صلاحية إرسال الرسائل.",
        reply_markup=InlineKeyboards.back_button(f"admin_settings_{class_id}")
    )

@router.message(ClassManagementStates.waiting_for_storage_channel)
async def admin_set_storage_process(message: Message, state: FSMContext, db: DatabaseManager, **kwargs):
    """Process storage channel ID/username/forward"""
    data = await state.get_data()
    class_id = data.get("class_id")
    
    chat_id = None
    chat_username = None
    
    # 1. Check if it's a forwarded message from a channel
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        chat_id = message.forward_from_chat.id
        chat_username = message.forward_from_chat.username
    else:
        # 2. Check text input
        user_input = message.text.strip() if message.text else ""
        if user_input:
            # Check if it looks like an ID or Username
            try:
                # Try getting chat info
                chat = await message.bot.get_chat(user_input)
                chat_id = chat.id
                chat_username = chat.username
            except Exception as e:
                await message.answer(f"❌ لم أتمكن من العثور على القناة: {user_input}\nتأكد من المعرف أو قم بتوجيه رسالة من القناة.")
                return
        else:
             await message.answer("❌ الرجاء إرسال معرف القناة أو توجيه رسالة منها.")
             return

    # Validate Bot Permissions
    try:
        member = await message.bot.get_chat_member(chat_id, message.bot.id)
        if member.status not in ["administrator", "creator"]:
            await message.answer(
                "⚠️ **البوت ليس مشرفاً في القناة!**\n\n"
                "يجب رفع البوت مشرفاً (Admin) في القناة مع صلاحية **نشر الرسائل** (Post Messages) لكي يعمل النظام."
            )
            return
            
        # Check posting permission specifically if possible (depends on aiogram version/object)
        if isinstance(member, (types.ChatMemberAdministrator, types.ChatMemberOwner)):
             # Note: Owner usually has all permissions. Administrator has flags.
             # We assume if admin, it's likely okay, but good to check if we could.
             pass

    except Exception as e:
        await message.answer(f"❌ حدث خطأ أثناء التحقق من القناة: {e}")
        return

    # Save to DB
    # Fix: Pass arguments correctly (username, channel_id)
    if await db.set_class_storage_channel(class_id, username=chat_username, channel_id=chat_id):
        # Send test message immediately
        try:
            await message.bot.send_message(chat_id, "✅ تم ربط هذه القناة بنجاح كقناة تخزين للبوت.")
            await message.answer(f"✅ تم تعيين قناة التخزين بنجاح: {chat_username or chat_id}\n📢 تم إرسال رسالة اختبار للقناة للتأكد من الصلاحيات.")
        except Exception as e:
            await message.answer(f"⚠️ تم حفظ القناة، ولكن فشل إرسال رسالة الاختبار: {e}\nيرجى التأكد من أن البوت مشرف ولديه صلاحية **نشر الرسائل**.")
    else:
        await message.answer("❌ حدث خطأ في قاعدة البيانات.")
        return

    await state.clear()

    # --- REFRESH LOGIC ---
    # Refresh the settings menu
    try:
        class_info = await db.get_class(class_id)
        if class_info:
            has_storage = bool(class_info.get("storage_channel_id"))
            storage_status = f"✅ موجودة: {class_info.get('storage_channel_username') or class_info.get('storage_channel_id')}" if has_storage else "❌ غير محددة"

            text = (
                f"⚙️ **إعدادات المرحلة: {class_info['class_name']}**\n\n"
                f"قناة التخزين هي قناة خاصة يتم فيها حفظ ملفات هذه المرحلة لتقليل الضغط على البوت.\n\n"
                f"الحالة الحالية: **{storage_status}**"
            )
            
            keyboard = InlineKeyboards.admin_class_settings_menu(class_id, has_storage)

            await message.bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=data.get("original_message_id"),
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error refreshing settings menu: {e}")
        
    # Try to delete the user's message
    try:
        await message.delete()
    except:
        pass

@router.callback_query(F.data.startswith("admin_clear_storage_"))
async def admin_clear_storage(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Clear storage channel for a class"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    try:
        class_id = int(callback.data.split("_")[3])
        # Use the specific clear method
        await db.clear_class_storage_channel(class_id)
        await callback.answer("✅ تم إزالة قناة التخزين.", show_alert=True)
        
        # Refresh settings view
        await admin_class_settings(callback, db, config, **kwargs)

    except Exception as e:
        logger.error(f"Error clearing storage: {e}")
        await callback.answer("❌ حدث خطأ.", show_alert=True)

@router.callback_query(F.data.startswith("admin_test_storage_"))
async def admin_test_storage(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Test storage channel for a class"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    try:
        class_id = int(callback.data.split("_")[3])
        class_info = await db.get_class(class_id)
        storage_id = class_info.get("storage_channel_id")

        if not storage_id:
            await callback.answer("⚠️ لا توجد قناة تخزين محددة.", show_alert=True)
            return

        await callback.answer("⏳ جاري إرسال رسالة اختبار...", show_alert=False)
        await callback.bot.send_message(storage_id, f"رسالة اختبار لقناة تخزين المرحلة: {class_info['class_name']}")
        await callback.answer("✅ تم إرسال رسالة الاختبار بنجاح!", show_alert=True)

    except Exception as e:
        logger.error(f"Error testing storage: {e}")
        await callback.answer(f"❌ فشل الاختبار: {e}", show_alert=True)

@router.callback_query(F.data.startswith("admin_set_manager_"))
async def admin_set_manager_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start setting manager for class"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return
    
    try:
        class_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        return

    await state.update_data(class_id=class_id)
    await state.set_state(ClassManagementStates.waiting_for_manager_id)
    
    await callback.message.edit_text(
        "👤 تعيين مسؤول للمرحلة\n\n"
        "أرسل معرف المستخدم (ID) أو اسم المستخدم (username) بدون @\n"
        "أو اضغط /skip لإزالة المسؤول الحالي",
        reply_markup=InlineKeyboards.back_button(f"admin_class_{class_id}")
    )

@router.message(ClassManagementStates.waiting_for_manager_id)
async def admin_set_manager_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process manager ID/username"""
    data = await state.get_data()
    class_id = data.get("class_id")
    
    if message.text == "/skip":
        await db.set_class_manager(class_id, None)
        await message.answer("✅ تم إزالة المسؤول الحالي.")
        await state.clear()
        return

    user_input = message.text.strip()
    target_user_id = None
    
    if user_input.isdigit():
        target_user_id = int(user_input)
    else:
        # Try to resolve username
        username = user_input.replace("@", "")
        user = await db.get_user_by_username(username)
        if user:
            target_user_id = user['user_id']
        else:
            await message.answer("❌ لم يتم العثور على المستخدم. تأكد من أنه استخدم البوت من قبل.")
            return

    if await db.set_class_manager(class_id, target_user_id):
        await message.answer(f"✅ تم تعيين المسؤول بنجاح: {target_user_id}")
    else:
        await message.answer("❌ حدث خطأ أثناء تعيين المسؤول.")
        
    await state.clear()
    
    # Optional: Show class details again
    cls = await db.get_class(class_id)
    if cls:
        text = f"📚 **{cls['class_name']}**\n\n👤 المسؤول: {target_user_id}\n🔢 المعرف: {class_id}"
        await message.answer(text, reply_markup=InlineKeyboards.admin_class_menu(class_id))


# ========== BROADCAST SYSTEM ==========

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_menu(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show broadcast target selection"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return

    buttons = [
        [InlineKeyboardButton(text="📢 للجميع (مشتركين)", callback_data="broadcast_target_all_users")],
        [InlineKeyboardButton(text="🎓 للطلاب فقط", callback_data="broadcast_target_all_students")],
        [InlineKeyboardButton(text="👨‍🏫 للمسؤولين فقط", callback_data="broadcast_target_all_managers")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_dashboard")]
    ]
    
    text = "📢 **نظام الإذاعة**\n\nاختر الفئة المستهدفة للإذاعة:"
    await safe_edit_message(callback, text, InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("broadcast_target_"))
async def admin_broadcast_target_select(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Select target and ask for message"""
    user_id = callback.from_user.id
    if not await check_is_superadmin(user_id, db, config or getattr(router, 'config', None), kwargs): return
    
    target_str = callback.data.replace("broadcast_target_", "")
    
    # Map string to enum
    target_map = {
        "all_users": BroadcastTargetType.ALL_USERS,
        "all_students": BroadcastTargetType.ALL_STUDENTS,
        "all_managers": BroadcastTargetType.ALL_MANAGERS
    }
    
    target_type = target_map.get(target_str)
    if not target_type:
        await callback.answer("❌ هدف غير صالح", show_alert=True)
        return

    await state.update_data(broadcast_target_type=target_type.value)
    await state.set_state(BroadcastStates.waiting_for_message)
    
    await safe_edit_message(
        callback, 
        "📝 **إرسال رسالة إذاعة**\n\nأرسل الرسالة التي تريد إذاعتها (نص، صورة، فيديو، ملف).\nيمكنك استخدام التنسيق (Bold, Italic, etc).", 
        InlineKeyboards.back_button("admin_broadcast")
    )


@router.message(BroadcastStates.waiting_for_message)
async def admin_broadcast_message_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process broadcast message and confirm"""
    # Extract message content using helper
    msg_data = extract_message_data(message)
    if not msg_data:
        await message.answer("❌ نوع الرسالة غير مدعوم.")
        return

    # Save to state
    await state.update_data(broadcast_message=msg_data)
    
    # Show confirmation
    data = await state.get_data()
    target_type_val = data.get("broadcast_target_type")
    
    target_names = {
        "all_users": "جميع المشتركين",
        "all_students": "جميع الطلاب",
        "all_managers": "جميع المسؤولين"
    }
    target_name = target_names.get(target_type_val, target_type_val)
    
    text = (
        "📢 **تأكيد الإذاعة**\n\n"
        f"🎯 الهدف: {target_name}\n"
        f"📄 نوع الرسالة: {msg_data.message_type}\n\n"
        "هل أنت متأكد من إرسال هذه الرسالة؟"
    )
    
    buttons = [
        [
            InlineKeyboardButton(text="✅ إرسال الآن", callback_data="broadcast_confirm_send"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="broadcast_cancel")
        ]
    ]
    
    # Send a copy of the message to show preview
    if msg_data.message_type == 'text':
        await message.answer(f"محاكمة للرسالة:\n\n{msg_data.message_text}")
    elif msg_data.message_type == 'photo':
        await message.answer_photo(msg_data.file_id, caption=msg_data.caption)
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "broadcast_confirm_send")
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, bot: Any):
    """Execute broadcast"""
    data = await state.get_data()
    msg_data: BroadcastMessage = data.get("broadcast_message")
    target_type_val = data.get("broadcast_target_type")
    
    if not msg_data or not target_type_val:
        await callback.answer("❌ انتهت صلاحية الجلسة", show_alert=True)
        await admin_broadcast_menu(callback, db)
        return
    
    await safe_edit_message(callback, "⏳ جاري الإرسال... يرجى الانتظار", None)
    
    # Initialize manager
    broadcast_manager = BroadcastManager(db, bot)
    
    # Create message object
    target_type = BroadcastTargetType(target_type_val)
    broadcast_msg = BroadcastMessage(
        sender_id=callback.from_user.id,
        target_type=target_type,
        message_text=msg_data.message_text,
        message_type=msg_data.message_type,
        file_id=msg_data.file_id,
        caption=msg_data.caption
    )
    
    # Send
    result = await broadcast_manager.send_broadcast(broadcast_msg)
    
    # Report
    report = (
        "✅ **تمت الإذاعة بنجاح**\n\n"
        f"📊 المستهدفين: {result.total_targets}\n"
        f"✅ تم الإرسال: {result.successful_sends}\n"
        f"❌ فشل: {result.failed_sends}\n"
        f"🚫 محظور: {result.blocked_users}\n"
        f"⏱ الوقت: {result.send_duration:.2f} ثانية"
    )
    
    await callback.message.edit_text(report, reply_markup=InlineKeyboards.back_button("admin_broadcast"))
    await state.clear()


@router.callback_query(F.data == "broadcast_cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    """Cancel broadcast"""
    await state.clear()
    await callback.answer("✅ تم الإلغاء")
    await admin_broadcast_menu(callback, db)

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from typing import Dict, Any

from keyboards.inline import InlineKeyboards
from database.db_manager import DatabaseManager
from states.registration import SubjectStates, FileStates, ExamStates
from utils.helpers import safe_edit_message

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "manager_classes")
async def manager_classes(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show manager's classes"""
    user_id = callback.from_user.id
    classes = await db.get_user_managed_classes(user_id)
    
    if not classes:
        await callback.answer("⚠️ أنت لست مسؤولاً على أي مرحلة", show_alert=True)
        return
    
    text = "📚 مراحلي\n\nاختر المرحلة:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_classes_list(classes))


@router.callback_query(F.data.startswith("manager_class_"))
async def manager_class_menu(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show class management menu"""
    class_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Check if user is manager of this class
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية على هذه المرحلة", show_alert=True)
        return
    
    # Determine course: Priority to URL param, fallback to DB
    active_course = 1
    if len(callback.data.split("_")) > 3:
        active_course = int(callback.data.split("_")[3])
        await db.set_user_active_course(user_id, active_course)
    else:
        active_course = await db.get_user_active_course(user_id)
    course_text = "الأول" if active_course == 1 else "الثاني"
    
    class_info = await db.get_class(class_id)
    text = (
        f"📚 المرحلة: {class_info['class_name']}\n"
        f"📍 الكورس الحالي: {course_text}\n\n"
        "العمليات التالية ستتم على الكورس المحدد:\n"
        "• 📚 المواد: عرض وإدارة مواد الكورس الحالي\n"
        "• ➕ إضافة مادة: إضافة مادة جديدة للكورس الحالي\n\n"
        "اختر الإجراء:"
    )
    await safe_edit_message(callback, text, InlineKeyboards.manager_class_menu(class_id, active_course))


@router.callback_query(F.data.startswith("manager_set_course_"))
async def manager_set_course(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Set active course context"""
    parts = callback.data.split("_")
    class_id = int(parts[3])
    new_course = int(parts[4])
    user_id = callback.from_user.id
    
    # Check permissions
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return

    # Update context
    await db.set_user_active_course(user_id, new_course)
    
    # Refresh menu
    await callback.answer(f"✅ تم تغيير الكورس إلى: {new_course}")
    
    # Call manager_class_menu logic directly to refresh
    # We construct a fake callback data to reuse the function logic if needed, 
    # but it's better to just copy the logic or call it cleanly.
    # Let's just re-render the menu.
    
    active_course = new_course
    course_text = "الأول" if active_course == 1 else "الثاني"
    
    class_info = await db.get_class(class_id)
    text = (
        f"📚 المرحلة: {class_info['class_name']}\n"
        f"📍 الكورس الحالي: {course_text}\n\n"
        "العمليات التالية ستتم على الكورس المحدد:\n"
        "• 📚 المواد: عرض وإدارة مواد الكورس الحالي\n"
        "• ➕ إضافة مادة: إضافة مادة جديدة للكورس الحالي\n\n"
        "اختر الإجراء:"
    )
    await safe_edit_message(callback, text, InlineKeyboards.manager_class_menu(class_id, active_course))


@router.callback_query(F.data.startswith("manager_add_subject_"))
async def manager_add_subject_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, **kwargs):
    """Start adding new subject"""
    parts = callback.data.split("_")
    class_id = int(parts[3])
    
    # Get user info
    user_id = callback.from_user.id
    
    # Determine course: Priority to URL param (button click), fallback to DB
    course = 1
    if len(parts) > 4:
        course = int(parts[4])
        # Sync DB with the explicit choice from the UI
        await db.set_user_active_course(user_id, course)
    else:
        course = await db.get_user_active_course(user_id)
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    await state.update_data(class_id=class_id, course=course)
    await state.set_state(SubjectStates.waiting_for_subject_name)
    
    await callback.message.edit_text(
        f"➕ إضافة مادة جديدة (كورس {course})\n\nأرسل اسم المادة:",
        reply_markup=InlineKeyboards.back_button(f"manager_class_{class_id}_{course}")
    )

@router.callback_query(F.data.startswith("manager_import_group_"))
async def manager_import_group_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    parts = callback.data.split("_")
    subject_id = int(parts[3])
    file_type = parts[4] if len(parts) > 4 else 'theory'
    user_id = callback.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    await state.update_data(subject_id=subject_id, group_items=[], group_base_name=None, file_type=file_type)
    await state.set_state(FileStates.waiting_for_group_base_name)
    
    type_text = "النظري" if file_type == 'theory' else "العملي"
    
    await callback.message.edit_text(
        f"📦 استيراد مجموعة ملازم {type_text}\n\nأرسل الاسم الأساسي للمجموعة (مثال: ملازم البرمجة - الفصل الأول):",
        reply_markup=InlineKeyboards.back_button(f"manager_files_{subject_id}_{file_type}")
    )

@router.message(StateFilter(FileStates.waiting_for_group_base_name))
async def manager_import_group_base(message: Message, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    data = await state.get_data()
    subject_id = data.get("subject_id")
    user_id = message.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await message.answer("❌ المادة غير موجودة")
        await state.clear()
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await message.answer("❌ ليس لديك صلاحية")
        await state.clear()
        return
    base_name = (message.text or "").strip()
    if not base_name:
        await message.answer("❌ الاسم الأساسي لا يمكن أن يكون فارغاً.\n\nأرسل الاسم الأساسي:")
        return
    await state.update_data(group_base_name=base_name, group_items=[])
    await state.set_state(FileStates.waiting_for_group_forwards)
    await message.answer(
        "✅ تم حفظ الاسم الأساسي.\n\nقم الآن بتوجيه (Forward) الرسائل من قناة التخزين لهذه المادة.\n"
        "يمكنك توجيه عدة رسائل واحدة تلو الأخرى، ثم اضغط إنهاء وحفظ من هذه الرسالة فقط.",
        reply_markup=InlineKeyboards.group_import_controls(subject_id)
    )

@router.message(StateFilter(FileStates.waiting_for_group_forwards))
async def manager_import_group_collect(message: Message, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    data = await state.get_data()
    subject_id = data.get("subject_id")
    user_id = message.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await message.answer("❌ المادة غير موجودة")
        await state.clear()
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await message.answer("❌ ليس لديك صلاحية")
        await state.clear()
        return
    if not message.forward_from_chat or not getattr(message, "forward_from_message_id", None):
        await message.answer("⚠️ يرجى توجيه رسالة من قناة التخزين (وليس إرسال ملف جديد).")
        return
    class_settings = await db.get_class_settings(subject['class_id'])
    storage_id = class_settings.get("storage_channel_id") if class_settings else None
    storage_username = class_settings.get("storage_channel_username") if class_settings else None
    fwd_chat_id = message.forward_from_chat.id
    fwd_username = message.forward_from_chat.username
    valid = False
    if storage_id and fwd_chat_id == storage_id:
        valid = True
    elif storage_username and fwd_username and storage_username.replace("@", "").lower() == fwd_username.lower():
        valid = True
    if not valid:
        await message.answer("❌ هذه الرسالة ليست من قناة التخزين المحددة لهذه المرحلة.\nقم بتحديث قناة التخزين أو أعد التوجيه من القناة الصحيحة.")
        return
    items = data.get("group_items") or []
    items.append({
        "chat_id": fwd_chat_id,
        "message_id": message.forward_from_message_id
    })
    await state.update_data(group_items=items)
    await message.answer(f"✅ تم إضافة رسالة. إجمالي الرسائل المستلمة: {len(items)}")

@router.callback_query(F.data.startswith("manager_group_finish_"))
async def manager_import_group_finish(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, **kwargs):
    data = await state.get_data()
    subject_id = int(callback.data.split("_")[3])
    base_name = data.get("group_base_name") or "ملف"
    items = data.get("group_items") or []
    file_type = data.get("file_type", "theory")
    user_id = callback.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        await state.clear()
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        await state.clear()
        return
    if not items:
        await callback.answer("⚠️ لم يتم إضافة أي رسائل", show_alert=True)
        return
    saved = 0
    for idx, item in enumerate(items, start=1):
        name = f"{base_name} #{idx}"
        fid = await db.add_file(subject_id=subject_id, file_name=name, uploaded_by=user_id, channel_message_id=item["message_id"], file_type=file_type)
        if fid:
            saved += 1
    await state.clear()
    received = len(items)
    failed = received - saved
    report_text = (
        "📦 تقرير الاستيراد\n\n"
        f"📨 المستلم: {received}\n"
        f"💾 المحفوظ: {saved}\n"
        f"⚠️ فشل: {failed}"
    )
    await callback.answer("✅ تم إنهاء الاستيراد", show_alert=True)
    await safe_edit_message(callback, report_text, InlineKeyboards.back_button(f"manager_files_{subject_id}_{file_type}"))

@router.callback_query(F.data.startswith("manager_group_cancel_"))
async def manager_import_group_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("✅ تم الإلغاء", show_alert=True)
    await safe_edit_message(callback, "تم إلغاء الاستيراد الجماعي", InlineKeyboards.back_button("back_to_manager_menu"))

@router.message(StateFilter(SubjectStates.waiting_for_subject_name))
async def manager_add_subject_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process subject name input"""
    data = await state.get_data()
    class_id = data.get("class_id")
    course = data.get("course", 1)
    user_id = message.from_user.id
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, class_id):
        await message.answer("❌ ليس لديك صلاحية")
        await state.clear()
        return
    
    subject_name = message.text.strip()
    
    if not subject_name:
        await message.answer("❌ اسم المادة لا يمكن أن يكون فارغاً.\n\nأرسل اسم المادة:")
        return
    
    # Check if subject already exists (globally in class to avoid unique constraint violation)
    existing_subjects = await db.get_class_subjects(class_id)
    if any(subj['subject_name'].upper() == subject_name.upper() for subj in existing_subjects):
        await message.answer(f"❌ المادة '{subject_name}' موجودة مسبقاً.\n\nأرسل اسم آخر:")
        return
    
    # Add subject
    subject_id = await db.add_subject(class_id, subject_name, course)
    if subject_id:
        await message.answer(
            f"✅ تم إضافة المادة '{subject_name}' بنجاح للكورس {course}!",
            reply_markup=InlineKeyboards.back_button(f"manager_subjects_{class_id}")
        )
        await db.add_log(user_id, "subject_added", f"Subject: {subject_id}, Class: {class_id}, Course: {course}")
    else:
        await message.answer("❌ خطأ في إضافة المادة. حاول مرة أخرى.")
    
    await state.clear()


@router.callback_query(F.data.startswith("manager_subjects_"))
async def manager_subjects(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show subjects for class"""
    parts = callback.data.split("_")
    class_id = int(parts[2])
    user_id = callback.from_user.id
    
    # Determine course: Priority to URL param, fallback to DB
    course = 1
    if len(parts) > 3:
        course = int(parts[3])
        await db.set_user_active_course(user_id, course)
    else:
        course = await db.get_user_active_course(user_id)
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_info = await db.get_class(class_id)
    subjects = await db.get_class_subjects(class_id, course)
    
    text = f"📚 المرحلة: {class_info['class_name']}\n\nالمواد (كورس {course}):"
    await safe_edit_message(callback, text, InlineKeyboards.manager_subjects_menu(subjects, class_id, course))


@router.callback_query(F.data.startswith("manager_subject_"))
async def manager_subject_menu(callback: CallbackQuery, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Show subject management menu"""
    subject_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager of this class
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية على هذه المادة", show_alert=True)
        return
        
    files_count = len(await db.get_subject_files(subject_id))
    course = subject.get('course', 1)
    text = (
        f"📖 المادة: {subject['subject_name']}\n"
        f"📁 عدد الملفات: {files_count}\n\n"
        "اختر الإجراء:\n"
        "• 📎 إرفاق ملف: إضافة ملف جديد من قناة التخزين\n"
        "• 📁 الملفات: عرض الملفات وحذفها\n"
        "• 🔁 نقل إلى الكورس الآخر: نقل المادة بين الكورس 1 و2\n"
        "• 🗑️ حذف المادة: حذف المادة مع ملفاتها"
    )
    await safe_edit_message(callback, text, InlineKeyboards.manager_subject_menu(subject_id, subject['class_id'], course))

@router.callback_query(F.data.startswith("manager_move_subject_course_"))
async def manager_move_subject_course(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Move subject to the other course"""
    parts = callback.data.split("_")
    subject_id = int(parts[4])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    current_course = int(subject.get('course', 1))
    new_course = 2 if current_course == 1 else 1
    
    success = await db.update_subject_course(subject_id, new_course)
    if success:
        await callback.answer(f"✅ تم نقل المادة إلى الكورس {new_course}", show_alert=True)
        # Refresh subject menu with updated course context
        updated = await db.get_subject(subject_id)
        text = f"📖 المادة: {updated['subject_name']}\n🔁 الكورس الحالي: {updated.get('course', new_course)}\n\nاختر الإجراء:"
        await safe_edit_message(callback, text, InlineKeyboards.manager_subject_menu(subject_id, updated['class_id'], updated.get('course', new_course)))
    else:
        await callback.answer("❌ تعذر نقل المادة", show_alert=True)


@router.callback_query(F.data.startswith("manager_add_file_"))
async def manager_add_file_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Start adding file - request message_id from channel"""
    parts = callback.data.split("_")
    subject_id = int(parts[3])
    file_type = parts[4] if len(parts) > 4 else 'theory'
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    # Get storage channel from config
    storage_channel = config.get("storage_channel", {}) if config else {}
    channel_username = storage_channel.get("username")
    # Override with per-class storage if available
    try:
        class_settings = await db.get_class_settings(subject['class_id'])
        if class_settings and (class_settings.get('storage_channel_username') or class_settings.get('storage_channel_id')):
            channel_username = class_settings.get('storage_channel_username') or channel_username
    except Exception:
        pass
    if not channel_username:
        channel_username = "@SS_Cs1"
    
    await state.update_data(subject_id=subject_id, file_type=file_type)
    await state.set_state(FileStates.waiting_for_message_id)
    
    type_text = "نظري" if file_type == 'theory' else "عملي"
    
    await callback.message.edit_text(
        f"📎 إضافة ملف ({type_text}) للمادة: {subject['subject_name']}\n\n"
        f"📌 خطوات إضافة الملف:\n"
        f"1️⃣ ارفع الملف إلى القناة {channel_username}\n"
        f"2️⃣ انسخ رقم الرسالة (message_id)\n"
        f"3️⃣ أرسل الرقم هنا\n\n"
        f"💡 مثال: إذا كان رابط الرسالة:\n"
        f"https://t.me/{channel_username.replace('@', '')}/1827\n"
        f"فالرقم هو: 1827\n\n"
        f"أرسل رقم الرسالة (message_id) الآن:",
        reply_markup=InlineKeyboards.back_button(f"manager_files_{subject_id}_{file_type}")
    )


@router.message(StateFilter(FileStates.waiting_for_message_id))
async def manager_add_file_process(message: Message, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Process message ID input"""
    data = await state.get_data()
    subject_id = data.get("subject_id")
    user_id = message.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await message.answer("❌ المادة غير موجودة")
        await state.clear()
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await message.answer("❌ ليس لديك صلاحية")
        await state.clear()
        return
    
    # Extract message_id from text (could be just number or full URL)
    message_text = message.text.strip()
    
    # Get storage channel info for validation
    class_settings = await db.get_class_settings(subject['class_id'])
    storage_username = None
    storage_id = None
    
    if class_settings:
        storage_username = class_settings.get('storage_channel_username')
        storage_id = class_settings.get('storage_channel_id')
    
    if not storage_username and not storage_id and config:
        # Fallback to global config
        storage_config = config.get("storage_channel", {})
        storage_username = storage_config.get("username")
        storage_id = storage_config.get("channel_id")

    # Normalize storage username (remove @)
    if storage_username:
        storage_username = storage_username.lstrip("@").lower()

    # Try to extract message_id from URL or get it directly
    channel_message_id = None
    try:
        # If it's a URL like https://t.me/SS_Cs1/1827
        if "t.me/" in message_text:
            parts = message_text.split("/")
            channel_message_id = int(parts[-1])
            
            # Validate Channel if possible
            if len(parts) >= 2:
                url_channel = parts[-2].lower() # username or c/123456
                
                # Check if it matches configured channel
                # Case 1: Public channel username
                if storage_username and url_channel != "c":
                    if url_channel != storage_username:
                        await message.answer(
                            f"⚠️ تنبيه: الرابط من قناة @{url_channel} بينما قناة التخزين هي @{storage_username}.\n"
                            "يجب أن يكون الملف في قناة التخزين المحددة ليعمل بشكل صحيح.\n\n"
                            "يرجى إعادة إرسال الرابط الصحيح أو رقم الرسالة من القناة الصحيحة."
                        )
                        return
                
                # Case 2: Private channel ID (url is t.me/c/1234567890/msg_id)
                elif url_channel == "c" and len(parts) >= 3:
                    # In this case parts[-2] is the chat_id without -100 prefix usually
                    url_chat_id = parts[-2]
                    # We can't easily validate ID against username without API call, 
                    # but we can validate against storage_id if we have it.
                    # This is complex, so we'll skip strict validation for private links for now 
                    # unless we are sure.
                    pass
        else:
            # It's just a number
            channel_message_id = int(message_text)
    except (ValueError, IndexError):
        await message.answer(
            "❌ رقم غير صحيح!\n\n"
            "أرسل رقم الرسالة فقط (مثل: 1827)\n"
            "أو رابط الرسالة الكامل (مثل: https://t.me/SS_Cs1/1827)"
        )
        return
    
    if channel_message_id <= 0:
        await message.answer("❌ رقم الرسالة يجب أن يكون أكبر من صفر")
        return
    
    # Optional: Verify message exists in channel (can be skipped if you trust the user)
    # Store message_id and ask for file name
    await state.update_data(channel_message_id=channel_message_id)
    await state.set_state(FileStates.waiting_for_file_name)
    await message.answer(
        f"✅ تم حفظ رقم الرسالة: {channel_message_id}\n\n"
        "الآن أرسل اسم الملف (مثلاً: كتاب البرمجة  - الفصل الأول):"
    )


@router.message(StateFilter(FileStates.waiting_for_file_name))
async def manager_add_file_name(message: Message, state: FSMContext, db: DatabaseManager, config: Dict[str, Any] = None, **kwargs):
    """Process file name and save file with channel_message_id"""
    data = await state.get_data()
    subject_id = data.get("subject_id")
    channel_message_id = data.get("channel_message_id")
    file_type = data.get("file_type", "theory")
    user_id = message.from_user.id
    
    # If no channel_message_id in state, this is the file name for a previously received file
    if not channel_message_id:
        await message.answer("❌ لم يتم رفع الملف إلى القناة. أرسل الملف أولاً.")
        await state.clear()
        return
    
    file_name = message.text.strip()
    
    if not file_name:
        await message.answer("❌ اسم الملف لا يمكن أن يكون فارغاً.\n\nأرسل اسم الملف:")
        return
    
    # Add file to database with channel_message_id
    file_id = await db.add_file(
        subject_id=subject_id,
        file_name=file_name,
        uploaded_by=user_id,
        channel_message_id=channel_message_id,
        file_type=file_type
    )
    if file_id:
        await message.answer(
            f"✅ تم إضافة الملف '{file_name}' بنجاح!",
            reply_markup=InlineKeyboards.back_button(f"manager_files_{subject_id}_{file_type}")
        )
        await db.add_log(user_id, "file_added", f"File: {file_id}, Subject: {subject_id}, Type: {file_type}")
    else:
        await message.answer("❌ خطأ في إضافة الملف. حاول مرة أخرى.")
    
    await state.clear()


@router.callback_query(F.data.startswith("manager_files_"))
async def manager_files(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show files for subject"""
    parts = callback.data.split("_")
    subject_id = int(parts[2])
    file_type = parts[3] if len(parts) > 3 else 'theory'
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    files = await db.get_subject_files(subject_id, file_type)
    
    type_text = "النظري" if file_type == 'theory' else "العملي"
    
    if not files:
        text = f"📖 المادة: {subject['subject_name']}\n📁 الملازم {type_text}:\n\n⚠️ لا توجد ملفات حالياً."
    else:
        text = f"📖 المادة: {subject['subject_name']}\n📁 الملازم {type_text}:\n\nاضغط على حذف لحذف الملف , او ارسال لرؤية الملف:"
    
    await safe_edit_message(callback, text, InlineKeyboards.manager_files_list(files, subject_id, subject['class_id'], file_type))


@router.callback_query(F.data.startswith("manager_delete_file_"))
async def manager_delete_file(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Delete file"""
    file_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    file_info = await db.get_file(file_id)
    if not file_info:
        await callback.answer("❌ الملف غير موجود", show_alert=True)
        return
    
    subject = await db.get_subject(file_info['subject_id'])
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
        
    file_type = file_info.get('file_type', 'theory')
    
    success = await db.delete_file(file_id)
    if success:
        await callback.answer("✅ تم حذف الملف بنجاح", show_alert=True)
        await db.add_log(user_id, "file_deleted", f"File: {file_id}")
        
        # Refresh files list
        files = await db.get_subject_files(subject['subject_id'], file_type)
        
        type_text = "النظري" if file_type == 'theory' else "العملي"
        
        if not files:
            text = f"📖 المادة: {subject['subject_name']}\n📁 الملازم {type_text}:\n\n⚠️ لا توجد ملفات حالياً."
        else:
            text = f"📖 المادة: {subject['subject_name']}\n📁 الملازم {type_text}:\n\nاضغط على حذف لحذف الملف , او ارسال لرؤية الملف:"
            
        await safe_edit_message(callback, text, InlineKeyboards.manager_files_list(files, subject['subject_id'], subject['class_id'], file_type))
    else:
        await callback.answer("❌ خطأ في حذف الملف", show_alert=True)
@router.callback_query(F.data.startswith("manager_delete_subject_"))
async def manager_delete_subject(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    await safe_edit_message(callback, f"هل أنت متأكد من حذف المادة: {subject['subject_name']}؟", InlineKeyboards.confirm_delete_subject(subject_id))

@router.callback_query(F.data.startswith("confirm_delete_subject_"))
async def confirm_delete_subject(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    success = await db.delete_subject(subject_id)
    if success:
        await callback.answer("✅ تم حذف المادة بنجاح", show_alert=True)
        await db.add_log(user_id, "subject_deleted", f"Subject: {subject_id}")
        course = subject.get('course', 1)
        subjects = await db.get_class_subjects(subject['class_id'], course)
        class_info = await db.get_class(subject['class_id'])
        if subjects:
            text = f"📚 المرحلة: {class_info['class_name']}\n\nالمواد (كورس {course}):"
            await safe_edit_message(callback, text, InlineKeyboards.manager_subjects_menu(subjects, subject['class_id'], course))
        else:
            await callback.message.edit_text(f"⚠️ لا توجد مواد في هذا الكورس ({course})", reply_markup=InlineKeyboards.back_button(f"manager_class_{subject['class_id']}"))
    else:
        await callback.answer("❌ خطأ في حذف المادة", show_alert=True)

@router.callback_query(F.data.startswith("cancel_delete_subject_"))
async def cancel_delete_subject(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    course = subject.get('course', 1)
    text = (
        f"📖 المادة: {subject['subject_name']}\n"
        f"📁 عدد الملفات: {len(await db.get_subject_files(subject_id))}\n\n"
        "اختر الإجراء:\n"
        "• 📎 إرفاق ملف: إضافة ملف جديد من قناة التخزين\n"
        "• 📁 الملفات: عرض الملفات وحذفها\n"
        "• 🔁 نقل إلى الكورس الآخر: نقل المادة بين الكورس 1 و2\n"
        "• 🗑️ حذف المادة: حذف المادة مع ملفاتها وامتحاناتها"
    )
    await safe_edit_message(callback, text, InlineKeyboards.manager_subject_menu(subject_id, subject['class_id'], course))


@router.callback_query(F.data.startswith("manager_exams_"))
async def manager_exams(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show subjects for exam management"""
    parts = callback.data.split("_")
    class_id = int(parts[2])
    user_id = callback.from_user.id
    
    # Determine course: Priority to URL param, fallback to DB
    course = 1
    if len(parts) > 3:
        course = int(parts[3])
        await db.set_user_active_course(user_id, course)
    else:
        course = await db.get_user_active_course(user_id)
    
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_info = await db.get_class(class_id)
    subjects = await db.get_class_subjects(class_id, course)
    
    if not subjects:
        text = f"📚 المرحلة: {class_info['class_name']}\n\n⚠️ لا توجد مواد في هذا الكورس ({course}).\nيمكنك التبديل للكورس الآخر من القائمة الرئيسية."
    else:
        text = f"📚 المرحلة: {class_info['class_name']}\n\nاختر المادة لإدارة الامتحانات (كورس {course}):"
    await safe_edit_message(callback, text, InlineKeyboards.manager_exam_subjects(subjects, class_id, course))


@router.callback_query(F.data.startswith("manager_exam_subject_"))
async def manager_exam_subject_menu(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show exam menu for subject"""
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject or not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    exams = await db.get_subject_exams(subject_id)
    course = subject.get('course', 1)
    text = f"📖 المادة: {subject['subject_name']}\n📝 عدد الامتحانات: {len(exams)}\n\nاختر الإجراء:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_exams_list(exams, subject_id, subject['class_id'], course))


@router.callback_query(F.data.startswith("manager_add_exam_"))
async def manager_add_exam_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, **kwargs):
    """Start adding exam"""
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject or not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    await state.update_data(subject_id=subject_id)
    text = f"📝 إضافة امتحان للمادة: {subject['subject_name']}\n\nاختر نوع الامتحان:"
    await safe_edit_message(callback, text, InlineKeyboards.exam_types(subject_id))


@router.callback_query(F.data.startswith("exam_type_"))
async def manager_exam_type_selected(callback: CallbackQuery, state: FSMContext):
    """Process exam type selection"""
    parts = callback.data.split("_")
    exam_type_code = parts[2] 
    subject_id = int(parts[3])
    
    # Map code to Arabic text
    exam_type_map = {
        "mid": "مد",
        "quiz": "كوز",
        "midyear": "نصف سنة",
        "final": "أخير سنة",
    }
    exam_type = exam_type_map.get(exam_type_code, "مد")
    
    await state.update_data(exam_type=exam_type, subject_id=subject_id)
    await state.set_state(ExamStates.waiting_for_exam_title)
    
    await callback.message.edit_text(
        f"📝 نوع الامتحان: {exam_type}\n\nأرسل عنوان الامتحان (سيظهر على الزر):",
        reply_markup=InlineKeyboards.back_button(f"manager_exam_subject_{subject_id}")
    )


@router.message(StateFilter(ExamStates.waiting_for_exam_title))
async def manager_exam_title_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process exam title"""
    data = await state.get_data()
    subject_id = data.get("subject_id")
    user_id = message.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject or not await db.is_class_manager(user_id, subject['class_id']):
        await message.answer("❌ ليس لديك صلاحية")
        await state.clear()
        return
    
    title = message.text.strip()
    if not title:
        await message.answer("❌ العنوان لا يمكن أن يكون فارغاً.\n\nأرسل عنوان الامتحان:")
        return
    
    await state.update_data(title=title)
    await state.set_state(ExamStates.waiting_for_exam_content)
    await message.answer(f"✅ العنوان: {title}\n\nالآن أرسل الامتحان (صورة/ملف/نص):")


@router.message(StateFilter(ExamStates.waiting_for_exam_content), F.document | F.photo | F.text)
async def manager_exam_content_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process exam content"""
    data = await state.get_data()
    subject_id = data.get("subject_id")
    exam_type = data.get("exam_type")
    title = data.get("title")
    user_id = message.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject or not await db.is_class_manager(user_id, subject['class_id']):
        await message.answer("❌ ليس لديك صلاحية")
        await state.clear()
        return
    
    telegram_file_id = None
    content_type = None
    content_text = None
    
    if message.document:
        telegram_file_id = message.document.file_id
        content_type = "document"
    elif message.photo:
        telegram_file_id = message.photo[-1].file_id
        content_type = "photo"
    elif message.text:
        content_text = message.text
        content_type = "text"
    
    exam_id = await db.add_exam(
        subject_id=subject_id,
        exam_type=exam_type,
        title=title,
        uploaded_by=user_id,
        telegram_file_id=telegram_file_id,
        content_type=content_type,
        content_text=content_text
    )
    
    if exam_id:
        await message.answer(f"✅ تم إضافة الامتحان '{title}' بنجاح!")
        await db.add_log(user_id, "exam_added", f"Exam: {exam_id}")
    else:
        await message.answer("❌ خطأ في إضافة الامتحان.")
    
    await state.clear()


@router.callback_query(F.data.startswith("manager_delete_exam_"))
async def manager_delete_exam(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Delete exam"""
    exam_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    exam = await db.get_exam(exam_id)
    if not exam:
        await callback.answer("❌ الامتحان غير موجود", show_alert=True)
        return
    
    subject = await db.get_subject(exam['subject_id'])
    if not subject or not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    success = await db.delete_exam(exam_id)
    if success:
        await callback.answer("✅ تم حذف الامتحان بنجاح", show_alert=True)
        exams = await db.get_subject_exams(subject['subject_id'])
        course = subject.get('course', 1)
        text = f"📖 المادة: {subject['subject_name']}\n📝 عدد الامتحانات: {len(exams)}\n\nاختر الإجراء:"
        await safe_edit_message(callback, text, InlineKeyboards.manager_exams_list(exams, subject['subject_id'], subject['class_id'], course))
    else:
        await callback.answer("❌ خطأ في حذف الامتحان", show_alert=True)


@router.callback_query(F.data == "back_to_manager_menu")
async def back_to_manager_menu(callback: CallbackQuery):
    """Back to manager menu"""
    await safe_edit_message(callback, "لوحة المسؤول\n\nاختر من القائمة:", InlineKeyboards.manager_menu())

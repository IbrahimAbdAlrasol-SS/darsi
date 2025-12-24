import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from typing import Dict, Any

from keyboards.inline import InlineKeyboards
from database.db_manager import DatabaseManager
from states.registration import SubjectStates, FileStates, ExamStates, ExamStates, ExamStates
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
    
    class_info = await db.get_class(class_id)
    text = f"📚 المرحلة: {class_info['class_name']}\n\nاختر الإجراء:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_class_menu(class_id))


@router.callback_query(F.data.startswith("manager_add_subject_"))
async def manager_add_subject_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, **kwargs):
    """Start adding new subject"""
    class_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    await state.update_data(class_id=class_id)
    await state.set_state(SubjectStates.waiting_for_subject_name)
    
    await callback.message.edit_text(
        "➕ إضافة مادة جديدة\n\nأرسل اسم المادة:",
        reply_markup=InlineKeyboards.back_button(f"manager_class_{class_id}")
    )


@router.message(StateFilter(SubjectStates.waiting_for_subject_name))
async def manager_add_subject_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process subject name input"""
    data = await state.get_data()
    class_id = data.get("class_id")
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
    
    # Check if subject already exists
    existing_subjects = await db.get_class_subjects(class_id)
    if any(subj['subject_name'].upper() == subject_name.upper() for subj in existing_subjects):
        await message.answer(f"❌ المادة '{subject_name}' موجودة مسبقاً.\n\nأرسل اسم آخر:")
        return
    
    # Add subject
    subject_id = await db.add_subject(class_id, subject_name)
    if subject_id:
        await message.answer(f"✅ تم إضافة المادة '{subject_name}' بنجاح!")
        await db.add_log(user_id, "subject_added", f"Subject: {subject_id}, Class: {class_id}")
    else:
        await message.answer("❌ خطأ في إضافة المادة. حاول مرة أخرى.")
    
    await state.clear()


@router.callback_query(F.data.startswith("manager_subjects_"))
async def manager_subjects(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show subjects for class"""
    class_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_info = await db.get_class(class_id)
    subjects = await db.get_class_subjects(class_id)
    
    if not subjects:
        await callback.answer("⚠️ لا توجد مواد في هذه المرحلة", show_alert=True)
        return
    
    text = f"📚 المرحلة: {class_info['class_name']}\n\nالمواد:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_subjects_menu(subjects, class_id))


@router.callback_query(F.data.startswith("manager_subject_"))
async def manager_subject_menu(callback: CallbackQuery, db: DatabaseManager, **kwargs):
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
    text = f"📖 المادة: {subject['subject_name']}\n📁 عدد الملفات: {files_count}\n\nاختر الإجراء:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_subject_menu(subject_id, subject['class_id']))


@router.callback_query(F.data.startswith("manager_add_file_"))
async def manager_add_file_start(callback: CallbackQuery, state: FSMContext, db: DatabaseManager, **kwargs):
    """Start adding file - request file upload"""
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    await state.update_data(subject_id=subject_id)
    await state.set_state(FileStates.waiting_for_file_name)
    
    await callback.message.edit_text(
        f"📎 إرفاق ملف للمادة: {subject['subject_name']}\n\n"
        f"أرسل الملف الآن:",
        reply_markup=InlineKeyboards.back_button(f"manager_subject_{subject_id}")
    )


@router.message(StateFilter(FileStates.waiting_for_file_name), F.document | F.photo | F.video | F.audio | F.voice)
async def manager_add_file_process(message: Message, state: FSMContext, db: DatabaseManager):
    """Process file upload"""
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
    
    # Get file ID
    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id
    
    if not file_id:
        await message.answer("❌ نوع الملف غير مدعوم. أرسل ملف صالح.")
        return
    
    # Store file_id and ask for file name
    await state.update_data(telegram_file_id=file_id)
    await message.answer(
        "✅ تم استلام الملف!\n\n"
        "الآن أرسل اسم الملف (مثلاً: كتاب الرياضيات - الفصل الأول):"
    )


@router.message(StateFilter(FileStates.waiting_for_file_name))
async def manager_add_file_name(message: Message, state: FSMContext, db: DatabaseManager):
    """Process file name and save file"""
    data = await state.get_data()
    subject_id = data.get("subject_id")
    telegram_file_id = data.get("telegram_file_id")
    user_id = message.from_user.id
    
    # If no telegram_file_id in state, this is the file name for a previously received file
    if not telegram_file_id:
        await message.answer("❌ لم يتم استلام الملف. أرسل الملف أولاً.")
        return
    
    file_name = message.text.strip()
    
    if not file_name:
        await message.answer("❌ اسم الملف لا يمكن أن يكون فارغاً.\n\nأرسل اسم الملف:")
        return
    
    # Add file to database
    file_id = await db.add_file(subject_id, telegram_file_id, file_name, user_id)
    if file_id:
        await message.answer(f"✅ تم إضافة الملف '{file_name}' بنجاح!")
        await db.add_log(user_id, "file_added", f"File: {file_id}, Subject: {subject_id}")
    else:
        await message.answer("❌ خطأ في إضافة الملف. حاول مرة أخرى.")
    
    await state.clear()


@router.callback_query(F.data.startswith("manager_files_"))
async def manager_files(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show files for subject"""
    subject_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    files = await db.get_subject_files(subject_id)
    
    if not files:
        await callback.answer("⚠️ لا توجد ملفات في هذه المادة", show_alert=True)
        return
    
    text = f"📖 المادة: {subject['subject_name']}\n📁 الملفات:\n\nاضغط على الملف لحذفه:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_files_list(files, subject_id, subject['class_id']))


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
    
    success = await db.delete_file(file_id)
    if success:
        await callback.answer("✅ تم حذف الملف بنجاح", show_alert=True)
        await db.add_log(user_id, "file_deleted", f"File: {file_id}")
        
        # Refresh files list
        files = await db.get_subject_files(subject['subject_id'])
        if files:
            text = f"📖 المادة: {subject['subject_name']}\n📁 الملفات:\n\nاضغط على الملف لحذفه:"
            await safe_edit_message(callback, text, InlineKeyboards.manager_files_list(files, subject['subject_id'], subject['class_id']))
        else:
            await callback.message.edit_text("⚠️ لا توجد ملفات في هذه المادة", reply_markup=InlineKeyboards.back_button(f"manager_subject_{subject['subject_id']}"))
    else:
        await callback.answer("❌ خطأ في حذف الملف", show_alert=True)
@router.callback_query(F.data.startswith("manager_delete_subject_"))
async def manager_delete_subject(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Delete subject"""
    subject_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    subject = await db.get_subject(subject_id)
    if not subject:
        await callback.answer("❌ المادة غير موجودة", show_alert=True)
        return
    
    # Check if user is manager
    if not await db.is_class_manager(user_id, subject['class_id']):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    success = await db.delete_subject(subject_id)
    if success:
        await callback.answer("✅ تم حذف المادة بنجاح", show_alert=True)
        await db.add_log(user_id, "subject_deleted", f"Subject: {subject_id}")
        
        # Go back to subjects list
        subjects = await db.get_class_subjects(subject['class_id'])
        class_info = await db.get_class(subject['class_id'])
        
        if subjects:
            text = f"📚 المرحلة: {class_info['class_name']}\n\nالمواد:"
            await safe_edit_message(callback, text, InlineKeyboards.manager_subjects_menu(subjects, subject['class_id']))
        else:
            await callback.message.edit_text("⚠️ لا توجد مواد في هذه المرحلة", reply_markup=InlineKeyboards.back_button(f"manager_class_{subject['class_id']}"))
    else:
        await callback.answer("❌ خطأ في حذف المادة", show_alert=True)


@router.callback_query(F.data.startswith("manager_exams_"))
async def manager_exams(callback: CallbackQuery, db: DatabaseManager, **kwargs):
    """Show subjects for exam management"""
    class_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    if not await db.is_class_manager(user_id, class_id):
        await callback.answer("❌ ليس لديك صلاحية", show_alert=True)
        return
    
    class_info = await db.get_class(class_id)
    subjects = await db.get_class_subjects(class_id)
    
    if not subjects:
        await callback.answer("⚠️ لا توجد مواد في هذه المرحلة", show_alert=True)
        return
    
    text = f"📚 المرحلة: {class_info['class_name']}\n\nاختر المادة لإدارة الامتحانات:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_exam_subjects(subjects, class_id))


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
    text = f"📖 المادة: {subject['subject_name']}\n📝 عدد الامتحانات: {len(exams)}\n\nاختر الإجراء:"
    await safe_edit_message(callback, text, InlineKeyboards.manager_exams_list(exams, subject_id, subject['class_id']))


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
        "final": "أخير سنة"
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
        text = f"📖 المادة: {subject['subject_name']}\n📝 عدد الامتحانات: {len(exams)}\n\nاختر الإجراء:"
        await safe_edit_message(callback, text, InlineKeyboards.manager_exams_list(exams, subject['subject_id'], subject['class_id']))
    else:
        await callback.answer("❌ خطأ في حذف الامتحان", show_alert=True)


@router.callback_query(F.data == "back_to_manager_menu")
async def back_to_manager_menu(callback: CallbackQuery):
    """Back to manager menu"""
    await safe_edit_message(callback, "لوحة المسؤول\n\nاختر من القائمة:", InlineKeyboards.manager_menu())

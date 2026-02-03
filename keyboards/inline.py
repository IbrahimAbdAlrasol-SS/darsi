#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any ,sys
DEEP_LINKS_ENABLED = False
class InlineKeyboards:
    """Class for creating inline keyboards"""
    @staticmethod
    def classes_list(classes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """Create keyboard with list of classes"""
        buttons = []
        row: List[InlineKeyboardButton] = []
        for cls in classes:
            btn = InlineKeyboardButton(
                text=cls['class_name'],
                callback_data=f"class_{cls['class_id']}"
            )
            row.append(btn)
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton(text="⭐ مفضلتي", callback_data="user_favorites")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def subjects_list(subjects: List[Dict[str, Any]], class_id: int, current_course: int = 1) -> InlineKeyboardMarkup:
        """Create keyboard with list of subjects"""
        buttons = []
        
        # Build subject buttons
        for subject in subjects:
            buttons.append([InlineKeyboardButton(
                text=subject['subject_name'],
                callback_data=f"subject_{subject['subject_id']}"
            )])
        
        # Bottom row: course toggle + back
        next_course = 2 if current_course == 1 else 1
        course_text = "الثاني" if current_course == 1 else "الأول"
        buttons.append([
            InlineKeyboardButton(
                text=f"🔄 عرض الكورس {course_text}",
                callback_data=f"class_{class_id}_{next_course}"
            ),
            InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_classes")
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def files_list(files: List[Dict[str, Any]], subject_id: int, file_type: str = 'theory') -> InlineKeyboardMarkup:
        """Create keyboard with list of files"""
        buttons = []
        for file in files:
            buttons.append([InlineKeyboardButton(
                text=f"📄 {file['file_name']}",
                callback_data=f"download_file_{file['file_id']}"
            )])
        
        # Add "Download All" button if there are files
        if files:
            buttons.append([InlineKeyboardButton(
                text="📦 تحميل جميع الملفات",
                callback_data=f"download_all_{subject_id}_{file_type}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 رجوع للمادة", callback_data=f"subject_{subject_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Admin main menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 لوحة التحكم الشاملة", callback_data="admin_dashboard")],
            [InlineKeyboardButton(text="📚 إدارة المراحل", callback_data="admin_classes")],
        ])

    @staticmethod
    def admin_dashboard_menu() -> InlineKeyboardMarkup:
        """Super Admin Dashboard menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 الإحصائيات", callback_data="admin_analytics"),
             InlineKeyboardButton(text="📢 الإذاعة", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="⚠️ سجل الأخطاء", callback_data="admin_errors"),
             InlineKeyboardButton(text="🔒 اشتراك إجباري", callback_data="admin_force_join")],
            [InlineKeyboardButton(text="💾 نسخ احتياطي", callback_data="admin_backup")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_admin_menu")]
        ])

    @staticmethod
    def admin_force_join_menu(channels: List[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
        """Force join management menu"""
        buttons = [
            [InlineKeyboardButton(text="➕ إضافة قناة جديدة", callback_data="admin_set_force_join_start")]
        ]
        
        if channels:
            for channel in channels:
                title = channel.get('channel_title') or channel.get('channel_username') or "قناة"
                buttons.append([
                    InlineKeyboardButton(text=f"📺 {title}", callback_data="ignore"),
                    InlineKeyboardButton(text="🗑️ حذف", callback_data=f"admin_delete_force_join_{channel['id']}")
                ])
            
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_dashboard")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def broadcast_confirm() -> InlineKeyboardMarkup:
        """Confirm broadcast sending"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ إرسال الآن", callback_data="broadcast_send")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="broadcast_cancel")]
        ])

    @staticmethod
    def admin_classes_management(classes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """Admin classes management menu"""
        buttons = [
            [InlineKeyboardButton(text="➕ إضافة مرحلة جديدة", callback_data="admin_add_class")]
        ]
        
        for cls in classes:
            manager_text = " (مسؤول)" if cls.get('manager_id') else " (بدون مسؤول)"
            buttons.append([InlineKeyboardButton(
                text=f"📚 {cls['class_name']}{manager_text}",
                callback_data=f"admin_class_{cls['class_id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_admin_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def admin_class_menu(class_id: int) -> InlineKeyboardMarkup:
        """Admin class management options"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 تعيين مسؤول", callback_data=f"admin_set_manager_{class_id}")],
            [InlineKeyboardButton(text="🗑️ حذف المرحلة", callback_data=f"admin_delete_class_{class_id}")],
            [InlineKeyboardButton(text="⚙️ إعدادات المرحلة", callback_data=f"admin_settings_{class_id}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_classes")]
        ])
    
    @staticmethod
    def admin_class_settings_menu(class_id: int, has_storage: bool) -> InlineKeyboardMarkup:
        buttons = []
        if has_storage:
            buttons.append([InlineKeyboardButton(text="📡 اختبار القناة", callback_data=f"admin_test_storage_{class_id}")])
            buttons.append([InlineKeyboardButton(text="🔄 تغيير قناة التخزين", callback_data=f"admin_set_storage_{class_id}")])
            buttons.append([InlineKeyboardButton(text="🗑️ إزالة قناة التخزين", callback_data=f"admin_clear_storage_{class_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="➕ إضافة قناة التخزين", callback_data=f"admin_set_storage_{class_id}")])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"admin_class_{class_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def manager_menu() -> InlineKeyboardMarkup:
        """Manager main menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 مراحلي", callback_data="manager_classes")],
        ])
    
    @staticmethod
    def manager_classes_list(classes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """Manager's classes list"""
        buttons = []
        for cls in classes:
            buttons.append([InlineKeyboardButton(
                text=cls['class_name'],
                callback_data=f"manager_class_{cls['class_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_manager_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def manager_class_menu(class_id: int, current_course: int = 1) -> InlineKeyboardMarkup:
        """Manager class management menu"""
        course_text = "الأول" if current_course == 1 else "الثاني"
        next_course = 2 if current_course == 1 else 1
        
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔄 الكورس الحالي: {course_text}", callback_data=f"manager_set_course_{class_id}_{next_course}")],
            [InlineKeyboardButton(text="📚 المواد", callback_data=f"manager_subjects_{class_id}_{current_course}"),
             InlineKeyboardButton(text=f"➕ إضافة مادة (كورس {current_course})", callback_data=f"manager_add_subject_{class_id}_{current_course}")],
            [InlineKeyboardButton(text="📝 الامتحانات", callback_data=f"manager_exams_{class_id}_{current_course}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="manager_classes")]
        ])
    
    @staticmethod
    def manager_subjects_menu(subjects: List[Dict[str, Any]], class_id: int, current_course: int = 1) -> InlineKeyboardMarkup:
        """Manager subjects list"""
        buttons = []
        
        for subject in subjects:
            buttons.append([InlineKeyboardButton(
                text=subject['subject_name'],
                callback_data=f"manager_subject_{subject['subject_id']}"
            )])
        
        # Course toggle and Back button in the same row
        next_course = 2 if current_course == 1 else 1
        course_text = "الثاني" if current_course == 1 else "الأول"
        buttons.append([
            InlineKeyboardButton(
                text=f"🔄 عرض الكورس {course_text}",
                callback_data=f"manager_subjects_{class_id}_{next_course}"
            ),
            InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_class_{class_id}_{current_course}")
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def manager_subject_menu(subject_id: int, class_id: int, course: int = 1) -> InlineKeyboardMarkup:
        """Manager subject menu - Split into Theory/Practical/Exams"""
        buttons = []
        
        # Main Categories
        buttons.append([
            InlineKeyboardButton(text="📚 الملازم النظري", callback_data=f"manager_files_{subject_id}_theory")
        ])
        buttons.append([
            InlineKeyboardButton(text="🧪 الملازم العملي", callback_data=f"manager_files_{subject_id}_practical")
        ])
        # Exams button removed

        # Administrative Actions
        row_actions = [
            InlineKeyboardButton(text="🔁 نقل مادة", callback_data=f"manager_move_subject_course_{subject_id}"),
            InlineKeyboardButton(text="🗑️ حذف المادة", callback_data=f"manager_delete_subject_{subject_id}")
        ]
        buttons.append(row_actions)
        
        if DEEP_LINKS_ENABLED:
            buttons.append([InlineKeyboardButton(text="🔗 نسخ رابط المادة", callback_data=f"copy_link_subject_{subject_id}")])
            
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_subjects_{class_id}_{course}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def manager_files_list(files: List[Dict[str, Any]], subject_id: int, class_id: int, file_type: str = 'theory') -> InlineKeyboardMarkup:
        """Manager files list with delete and view options"""
        buttons = []
        
        # Add File Button (Context Aware)
        type_text = "نظري" if file_type == 'theory' else "عملي"
        buttons.append([
            InlineKeyboardButton(text=f"➕ إضافة ملف {type_text}", callback_data=f"manager_add_file_{subject_id}_{file_type}")
        ])
        
        # Import Group Button
        buttons.append([
            InlineKeyboardButton(text="📥 استيراد مجموعة ملفات", callback_data=f"manager_import_group_{subject_id}_{file_type}")
        ])

        for file in files:
            # File name label (non-clickable)
            buttons.append([
                InlineKeyboardButton(
                    text=f"📄 {file['file_name']}",
                    callback_data="ignore"
                )
            ])
            # Actions
            buttons.append([
                InlineKeyboardButton(
                    text="📤 ارسال",
                    callback_data=f"download_file_{file['file_id']}"
                ),
                InlineKeyboardButton(
                    text="🗑️ حذف",
                    callback_data=f"manager_delete_file_{file['file_id']}"
                )
            ])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_subject_{subject_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def group_import_controls(subject_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ إنهاء وحفظ", callback_data=f"manager_group_finish_{subject_id}")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data=f"manager_group_cancel_{subject_id}")]
        ])
    
    @staticmethod
    def back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
        """Create simple back button"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data=callback_data)]
        ])
    
    @staticmethod
    def confirm_delete() -> InlineKeyboardMarkup:
        """Confirm delete action"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأكيد", callback_data="confirm_delete")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_delete")]
        ])
    
    @staticmethod
    def confirm_delete_subject(subject_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأكيد", callback_data=f"confirm_delete_subject_{subject_id}")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data=f"cancel_delete_subject_{subject_id}")]
        ])
    
    # ========== EXAM KEYBOARDS ==========
    
    @staticmethod
    def manager_exam_subjects(subjects: List[Dict[str, Any]], class_id: int, current_course: int = 1) -> InlineKeyboardMarkup:
        """Show subjects for exam management"""
        buttons = []
        next_course = 2 if current_course == 1 else 1
        course_text = "الثاني" if current_course == 1 else "الأول"
        for subject in subjects:
            buttons.append([InlineKeyboardButton(
                text=subject['subject_name'],
                callback_data=f"manager_exam_subject_{subject['subject_id']}"
            )])
        buttons.append([
            InlineKeyboardButton(
                text=f"🔄 عرض الكورس {course_text}",
                callback_data=f"manager_exams_{class_id}_{next_course}"
            ),
            InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_class_{class_id}_{current_course}")
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def exam_types(subject_id: int) -> InlineKeyboardMarkup:
        """Choose exam type"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 مد", callback_data=f"exam_type_mid_{subject_id}"),InlineKeyboardButton(text="📝 كوز", callback_data=f"exam_type_quiz_{subject_id}")],
            
            [InlineKeyboardButton(text="📝 نصف سنة", callback_data=f"exam_type_midyear_{subject_id}"), InlineKeyboardButton(text="📝 أخير سنة", callback_data=f"exam_type_final_{subject_id}")],
            
            [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_exam_subject_{subject_id}")]
        ])
    
    @staticmethod
    def manager_exams_list(exams: List[Dict[str, Any]], subject_id: int, class_id: int, course: int = 1) -> InlineKeyboardMarkup:
        """Manager exams list with delete option"""
        buttons = []
        for exam in exams:
            buttons.append([InlineKeyboardButton(
                text=f"🗑️ {exam['title']} ({exam['exam_type']})",
                callback_data=f"manager_delete_exam_{exam['exam_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="➕ إضافة امتحان", callback_data=f"manager_add_exam_{subject_id}")])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_exams_{class_id}_{course}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def user_subject_menu(subject_id: int, class_id: int, course: int = 1, is_favorite: bool = False) -> InlineKeyboardMarkup:
        """User subject menu - choose between theory, practical"""
        fav_text = "💔 إزالة من المفضلة" if is_favorite else "❤️ إضافة إلى المفضلة"
        
        # Side-by-side buttons for Theory and Practical
        buttons = [
            [
                InlineKeyboardButton(text="📚 النظري", callback_data=f"user_files_{subject_id}_theory"),
                InlineKeyboardButton(text="🧪 العملي", callback_data=f"user_files_{subject_id}_practical")
            ],
            [
                InlineKeyboardButton(text="📝 الامتحانات", callback_data=f"user_exams_{subject_id}")
            ],
            [InlineKeyboardButton(text=fav_text, callback_data=f"toggle_favorite_{subject_id}")],
        ]
        
        if DEEP_LINKS_ENABLED:
            buttons.append([InlineKeyboardButton(text="🔗 مشاركة المادة", callback_data=f"copy_link_subject_{subject_id}")])
            
        buttons.append([InlineKeyboardButton(text="🔙 عودة للمواد", callback_data=f"class_{class_id}_{course}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def user_exam_types(subject_id: int) -> InlineKeyboardMarkup:
        """User exam types menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 كوز", callback_data=f"user_exam_type_quiz_{subject_id}"),
                InlineKeyboardButton(text="📝 مد", callback_data=f"user_exam_type_mid_{subject_id}")
            ],
            [
                InlineKeyboardButton(text="📝 نصف سنة", callback_data=f"user_exam_type_midyear_{subject_id}"),
                InlineKeyboardButton(text="📝 أخير سنة", callback_data=f"user_exam_type_final_{subject_id}")
            ],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"subject_{subject_id}")]
        ])

    
    @staticmethod
    def favorites_list(subjects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        buttons = []
        for subj in subjects:
            buttons.append([InlineKeyboardButton(
                text=f"📖 {subj['subject_name']} (كورس {subj.get('course', 1)})",
                callback_data=f"subject_{subj['subject_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 عودة للقائمة الرئيسية", callback_data="back_to_classes")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def user_exams_list(exams: List[Dict[str, Any]], subject_id: int, exam_type: str) -> InlineKeyboardMarkup:
        """User exams list"""
        buttons = []
        for exam in exams:
            buttons.append([InlineKeyboardButton(
                text=f"📝 {exam['title']} ({exam['exam_type']})",
                callback_data=f"download_exam_{exam['exam_id']}"
            )])
        
        if exams:
            buttons.append([InlineKeyboardButton(
                text="📦 إرسال الكل",
                callback_data=f"send_all_exams_{subject_id}_{exam_type}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"user_exams_{subject_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


class InlineKeyboards:
    """Class for creating inline keyboards"""
    
    @staticmethod
    def classes_list(classes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """Create keyboard with list of classes"""
        buttons = []
        for cls in classes:
            buttons.append([InlineKeyboardButton(
                text=cls['class_name'],
                callback_data=f"class_{cls['class_id']}"
            )])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def subjects_list(subjects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """Create keyboard with list of subjects"""
        buttons = []
        for subject in subjects:
            buttons.append([InlineKeyboardButton(
                text=subject['subject_name'],
                callback_data=f"subject_{subject['subject_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_classes")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def files_list(files: List[Dict[str, Any]], subject_id: int) -> InlineKeyboardMarkup:
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
                text="📦 تحميل الكل",
                callback_data=f"download_all_{subject_id}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"back_to_subjects_{subject_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Admin main menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 إدارة المراحل", callback_data="admin_classes")],
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
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_classes")]
        ])
    
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
    def manager_class_menu(class_id: int) -> InlineKeyboardMarkup:
        """Manager class management menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ إضافة مادة", callback_data=f"manager_add_subject_{class_id}")],
            [InlineKeyboardButton(text="📚 المواد", callback_data=f"manager_subjects_{class_id}")],
            [InlineKeyboardButton(text="📝 الامتحانات", callback_data=f"manager_exams_{class_id}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="manager_classes")]
        ])
    
    @staticmethod
    def manager_subjects_menu(subjects: List[Dict[str, Any]], class_id: int) -> InlineKeyboardMarkup:
        """Manager subjects list"""
        buttons = []
        for subject in subjects:
            buttons.append([InlineKeyboardButton(
                text=subject['subject_name'],
                callback_data=f"manager_subject_{subject['subject_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_class_{class_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def manager_subject_menu(subject_id: int, class_id: int) -> InlineKeyboardMarkup:
        """Manager subject management menu"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📎 إرفاق ملف", callback_data=f"manager_add_file_{subject_id}")],
            [InlineKeyboardButton(text="📁 الملفات", callback_data=f"manager_files_{subject_id}")],
            [InlineKeyboardButton(text="🗑️ حذف المادة", callback_data=f"manager_delete_subject_{subject_id}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_subjects_{class_id}")]
        ])
    
    @staticmethod
    def manager_files_list(files: List[Dict[str, Any]], subject_id: int, class_id: int) -> InlineKeyboardMarkup:
        """Manager files list with delete option"""
        buttons = []
        for file in files:
            buttons.append([InlineKeyboardButton(
                text=f"🗑️ {file['file_name']}",
                callback_data=f"manager_delete_file_{file['file_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_subject_{subject_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
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
    
    # ========== EXAM KEYBOARDS ==========
    
    @staticmethod
    def manager_exam_subjects(subjects: List[Dict[str, Any]], class_id: int) -> InlineKeyboardMarkup:
        """Show subjects for exam management"""
        buttons = []
        for subject in subjects:
            buttons.append([InlineKeyboardButton(
                text=subject['subject_name'],
                callback_data=f"manager_exam_subject_{subject['subject_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_class_{class_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def exam_types(subject_id: int) -> InlineKeyboardMarkup:
        """Choose exam type"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 مد", callback_data=f"exam_type_mid_{subject_id}")],
            [InlineKeyboardButton(text="📝 كوز", callback_data=f"exam_type_quiz_{subject_id}")],
            [InlineKeyboardButton(text="📝 نصف سنة", callback_data=f"exam_type_midyear_{subject_id}")],
            [InlineKeyboardButton(text="📝 أخير سنة", callback_data=f"exam_type_final_{subject_id}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_exam_subject_{subject_id}")]
        ])
    
    @staticmethod
    def manager_exams_list(exams: List[Dict[str, Any]], subject_id: int, class_id: int) -> InlineKeyboardMarkup:
        """Manager exams list with delete option"""
        buttons = []
        for exam in exams:
            buttons.append([InlineKeyboardButton(
                text=f"🗑️ {exam['title']} ({exam['exam_type']})",
                callback_data=f"manager_delete_exam_{exam['exam_id']}"
            )])
        buttons.append([InlineKeyboardButton(text="➕ إضافة امتحان", callback_data=f"manager_add_exam_{subject_id}")])
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"manager_exams_{class_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def user_subject_menu(subject_id: int, class_id: int) -> InlineKeyboardMarkup:
        """User subject menu - choose between files and exams"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📁 الملازم", callback_data=f"user_files_{subject_id}")],
            [InlineKeyboardButton(text="📝 الامتحانات", callback_data=f"user_exams_{subject_id}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data=f"class_{class_id}")]
        ])
    
    @staticmethod
    def user_exams_list(exams: List[Dict[str, Any]], subject_id: int) -> InlineKeyboardMarkup:
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
                callback_data=f"send_all_exams_{subject_id}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"subject_{subject_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

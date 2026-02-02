#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper functions for the bot"""

import logging
from typing import Optional
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


def smart_truncate_name(name: str, max_length: int = 12) -> str:
    """
    Smart truncation for names that tries to break at word boundaries
    
    Args:
        name: The name to truncate
        max_length: Maximum length allowed
        
    Returns:
        Truncated name with ".." if truncated
    """
    if len(name) <= max_length:
        return name
    
    # Try to find a good breaking point (space)
    words = name.split()
    if len(words) > 1:
        # Try to fit first name + space + part of last name
        first_name = words[0]
        if len(first_name) <= max_length - 2:
            return first_name + ".."
        elif len(words) > 1 and len(first_name + " " + words[1][:2]) <= max_length - 2:
            return first_name + " " + words[1][:2] + ".."
    
    # If no good breaking point, just truncate
    return name[:max_length - 2] + ".."


async def safe_edit_message(
    callback: CallbackQuery, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> bool:
    """
    Safely edit message with error handling
    Returns True if successful, False if failed
    """
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Message content is the same, just answer callback
            await callback.answer()
            logger.debug(f"Message not modified for user {callback.from_user.id}")
            return True
        elif "there is no text in the message to edit" in str(e):
            # Message has no text (e.g., only media), send new message instead
            try:
                await callback.message.answer(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                await callback.answer()
                logger.debug(f"Sent new message instead of editing for user {callback.from_user.id}")
                return True
            except Exception as send_error:
                logger.error(f"Failed to send new message: {send_error}")
                await callback.answer("❌ خطأ في إرسال الرسالة", show_alert=True)
                return False
        else:
            # Other telegram errors
            logger.error(f"Telegram error editing message: {e}")
            await callback.answer("❌ خطأ في تعديل الرسالة", show_alert=True)
            return False
    except Exception as e:
        # Other unexpected errors
        logger.error(f"Unexpected error editing message: {e}")
        await callback.answer("❌ خطأ غير متوقع", show_alert=True)
        return False


async def safe_send_message(
    chat_id: int,
    text: str,
    bot,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> bool:
    """
    Safely send message with error handling
    Returns True if successful, False if failed
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        return False


def format_user_info(user) -> str:
    """Format user information for display"""
    parts = []
    
    if user.first_name:
        parts.append(user.first_name)
    if user.last_name:
        parts.append(user.last_name)
    
    name = " ".join(parts) if parts else "غيرمحدد"
    
    if user.username:
        return f"{name} (@{user.username})"
    else:
        return f"{name} (ID: {user.id})"


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text if it's too long for Telegram"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 10] + "\n\n... (متابعة)"


def get_time_ago(datetime_obj) -> str:
    """Get human readable time ago"""
    from datetime import datetime, timezone
    
    if not datetime_obj:
        return "غير محدد"
    
    try:
        if isinstance(datetime_obj, str):
            # Parse string datetime
            from datetime import datetime
            datetime_obj = datetime.fromisoformat(datetime_obj.replace('Z', '+00:00'))
        
        now = datetime.now(timezone.utc)
        diff = now - datetime_obj
        
        if diff.days > 0:
            return f"قبل {diff.days} يوم"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"قبل {hours} ساعة"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"قبل {minutes} دقيقة"
        else:
            return "الآن"
    except Exception as e:
        logger.error(f"Error calculating time ago: {e}")
        return "غير محدد"


def format_stats_text(stats: dict) -> str:
    """Format statistics dictionary into readable text"""
    if not stats:
        return "❌ لا توجد إحصائيات"
    
    formatted = []
    for key, value in stats.items():
        # Convert keys to Persian
        persian_keys = {
            'total_users': 'الاحصائيات',
            'active_users': 'الطلاب المتفاعلين',
            'blocked_users': 'المحظورين',
            'total_students': 'كل الطلاب',
            'approved_students': 'تم تأكيدهم',
            'pending_students': 'بالانتظار',
            'male_students': 'طلاب جامعيون',
            'female_students': 'طالبات جامعيات',
            'morning_students': 'صباحي',
            'evening_students': 'المسائي',
            'total_groups': 'المجموعات',
            'total_classes': 'الشعب',
            'total_subjects': 'المواد',
            'total_files': 'الملفات'
        }
        
        persian_key = persian_keys.get(key, key)
        formatted.append(f"• {persian_key}: {value:,}")
    
    return "\n".join(formatted)


def validate_persian_text(text: str) -> bool:
    """Validate if text contains valid Persian characters"""
    if not text or not text.strip():
        return False
    
    # Check for Persian characters, numbers, and common symbols
    persian_chars = set('آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیءأإؤئ۰۱۲۳۴۵۶۷۸۹')
    english_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    allowed_symbols = set(' .,!?()[]{}+-*/_=@#$%^&|~`"\':;')
    
    allowed_chars = persian_chars | english_chars | allowed_symbols
    
    for char in text:
        if char not in allowed_chars:
            return False
    
    return True


def clean_html_tags(text: str) -> str:
    """Remove HTML tags from text"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def generate_unique_id() -> str:
    """Generate unique ID for various purposes"""
    import uuid
    return str(uuid.uuid4())[:8]


async def log_user_action(db, user_id: int, action: str, details: str = None):
    """Log user action to database"""
    try:
        await db.add_log(user_id, action, details)
    except Exception as e:
        logger.error(f"Error logging user action: {e}")


def format_keyboard_data(data: dict) -> str:
    """Format dictionary data for callback data"""
    import json
    try:
        return json.dumps(data, ensure_ascii=False)[:64]  # Telegram limit
    except Exception:
        return str(data)[:64]


def parse_keyboard_data(data: str) -> dict:
    """Parse callback data back to dictionary"""
    import json
    try:
        return json.loads(data)
    except Exception:
        return {}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modular Broadcast System for School Bot
Handles all broadcast messaging functionality with proper permissions and targeting
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaDocument
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database.db_manager import DatabaseManager
from utils.helpers import safe_send_message


class BroadcastTargetType(Enum):
    """Broadcast target types"""
    ALL_USERS = "all_users"
    ALL_MANAGERS = "all_managers" 
    ALL_OWNERS = "all_owners"
    ALL_STUDENTS = "all_students"
    GROUP_MANAGERS = "group_managers"
    GROUP_STUDENTS = "group_students"
    CLASS_STUDENTS = "class_students"


@dataclass
class BroadcastMessage:
    """Broadcast message data structure"""
    sender_id: int
    target_type: BroadcastTargetType
    target_id: Optional[int] = None  # group_id or class_id for specific targets
    message_text: Optional[str] = None
    message_type: str = "text"  # text, photo, video, document, audio, voice
    file_id: Optional[str] = None
    caption: Optional[str] = None


@dataclass
class BroadcastResult:
    """Broadcast operation result"""
    total_targets: int
    successful_sends: int
    failed_sends: int
    blocked_users: int
    deleted_users: int
    success_rate: float
    send_duration: float
    errors: List[str]


class BroadcastManager:
    """Main broadcast management class"""
    
    def __init__(self, db: DatabaseManager, bot: Bot, logger: Optional[logging.Logger] = None):
        self.db = db
        self.bot = bot
        self.logger = logger or logging.getLogger(__name__)
        
        # Rate limiting settings
        self.max_concurrent_sends = 20  # Maximum concurrent sends
        self.delay_between_batches = 1.0  # Delay between batches in seconds
        self.delay_between_sends = 0.1  # Delay between individual sends
    
    async def validate_broadcast_permission(self, user_id: int, target_type: BroadcastTargetType, 
                                          target_id: Optional[int] = None) -> bool:
        """Validate if user has permission to broadcast to target"""
        try:
            # Check if user is superadmin (can broadcast to anyone)
            if await self.db.is_superadmin(user_id):
                return True
            
            # Check specific permissions based on target type
            if target_type == BroadcastTargetType.ALL_USERS:
                return await self.db.is_superadmin(user_id)
            
            elif target_type == BroadcastTargetType.ALL_MANAGERS:
                return await self.db.is_superadmin(user_id)
            
            elif target_type == BroadcastTargetType.ALL_OWNERS:
                return await self.db.is_superadmin(user_id)
            
            elif target_type == BroadcastTargetType.ALL_STUDENTS:
                return await self.db.is_superadmin(user_id)
            
            elif target_type == BroadcastTargetType.GROUP_MANAGERS:
                if not target_id:
                    return False
                return await self.db.verify_group_ownership(user_id, target_id)
            
            elif target_type == BroadcastTargetType.GROUP_STUDENTS:
                if not target_id:
                    return False
                return await self.db.verify_group_ownership(user_id, target_id)
            
            elif target_type == BroadcastTargetType.CLASS_STUDENTS:
                if not target_id:
                    return False
                return await self.db.verify_class_management(user_id, target_id)
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error validating broadcast permission: {e}")
            return False
    
    async def get_broadcast_targets(self, target_type: BroadcastTargetType, 
                                  target_id: Optional[int] = None, 
                                  sender_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of target users for broadcast"""
        try:
            targets = []
            
            if target_type == BroadcastTargetType.ALL_USERS:
                targets = await self.db.get_all_users_for_admin_broadcast('all')
            
            elif target_type == BroadcastTargetType.ALL_MANAGERS:
                targets = await self.db.get_all_users_for_admin_broadcast('managers')
            
            elif target_type == BroadcastTargetType.ALL_OWNERS:
                targets = await self.db.get_all_users_for_admin_broadcast('owners')
            
            elif target_type == BroadcastTargetType.ALL_STUDENTS:
                targets = await self.db.get_all_users_for_admin_broadcast('students')
            
            elif target_type == BroadcastTargetType.GROUP_MANAGERS:
                if not target_id:
                    return []
                targets = await self.db.get_group_managers_for_broadcast(target_id)
            
            elif target_type == BroadcastTargetType.GROUP_STUDENTS:
                if not target_id:
                    return []
                targets = await self.db.get_group_students_for_broadcast(target_id)
            
            elif target_type == BroadcastTargetType.CLASS_STUDENTS:
                if not target_id:
                    return []
                targets = await self.db.get_class_students_for_broadcast(target_id)
            
            # Remove sender from targets to avoid self-messaging
            if sender_id and targets:
                targets = [target for target in targets if target.get('user_id') != sender_id]
            
            return targets
            
        except Exception as e:
            self.logger.error(f"❌ Error getting broadcast targets: {e}")
            return []
    
    async def send_single_message(self, user_id: int, message: BroadcastMessage) -> Tuple[bool, str]:
        """Send message to a single user"""
        try:
            if message.message_type == "text":
                success = await safe_send_message(
                    chat_id=user_id,
                    text=message.message_text,
                    bot=self.bot
                )
                return success, "" if success else "Failed to send text message"
            
            elif message.message_type == "photo":
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=message.file_id,
                    caption=message.caption
                )
                return True, ""
            
            elif message.message_type == "video":
                await self.bot.send_video(
                    chat_id=user_id,
                    video=message.file_id,
                    caption=message.caption
                )
                return True, ""
            
            elif message.message_type == "document":
                await self.bot.send_document(
                    chat_id=user_id,
                    document=message.file_id,
                    caption=message.caption
                )
                return True, ""
            
            elif message.message_type == "audio":
                await self.bot.send_audio(
                    chat_id=user_id,
                    audio=message.file_id,
                    caption=message.caption
                )
                return True, ""
            
            elif message.message_type == "voice":
                await self.bot.send_voice(
                    chat_id=user_id,
                    voice=message.file_id,
                    caption=message.caption
                )
                return True, ""
            
            else:
                return False, f"Unsupported message type: {message.message_type}"
        
        except TelegramForbiddenError:
            return False, "user_blocked_bot"
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                return False, "user_deleted_account"
            return False, f"telegram_error: {str(e)}"
        except Exception as e:
            return False, f"unexpected_error: {str(e)}"
    
    async def send_broadcast_batch(self, targets: List[Dict[str, Any]], message: BroadcastMessage, 
                                 start_index: int, batch_size: int) -> Dict[str, Any]:
        """Send broadcast to a batch of users"""
        batch_targets = targets[start_index:start_index + batch_size]
        batch_results = {
            'successful': 0,
            'failed': 0,
            'blocked': 0,
            'deleted': 0,
            'errors': []
        }
        
        # Create semaphore to limit concurrent sends
        semaphore = asyncio.Semaphore(self.max_concurrent_sends)
        
        async def send_to_user(target):
            async with semaphore:
                user_id = target['user_id']
                success, error = await self.send_single_message(user_id, message)
                
                if success:
                    batch_results['successful'] += 1
                else:
                    batch_results['failed'] += 1
                    if error == "user_blocked_bot":
                        batch_results['blocked'] += 1
                    elif error == "user_deleted_account":
                        batch_results['deleted'] += 1
                    else:
                        batch_results['errors'].append(f"User {user_id}: {error}")
                
                # Small delay between sends to avoid rate limiting
                await asyncio.sleep(self.delay_between_sends)
        
        # Send to all users in batch concurrently
        tasks = [send_to_user(target) for target in batch_targets]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return batch_results
    
    async def send_broadcast(self, message: BroadcastMessage) -> BroadcastResult:
        """Send broadcast message to all targets"""
        start_time = datetime.now()
        
        try:
            # Validate permission
            has_permission = await self.validate_broadcast_permission(
                message.sender_id, message.target_type, message.target_id
            )
            
            if not has_permission:
                return BroadcastResult(
                    total_targets=0,
                    successful_sends=0,
                    failed_sends=0,
                    blocked_users=0,
                    deleted_users=0,
                    success_rate=0.0,
                    send_duration=0.0,
                    errors=["Permission denied"]
                )
            
            # Get targets
            targets = await self.get_broadcast_targets(message.target_type, message.target_id, message.sender_id)
            
            if not targets:
                return BroadcastResult(
                    total_targets=0,
                    successful_sends=0,
                    failed_sends=0,
                    blocked_users=0,
                    deleted_users=0,
                    success_rate=0.0,
                    send_duration=0.0,
                    errors=["No targets found"]
                )
            
            # Save message to database
            await self.db.save_broadcast_message(
                sender_id=message.sender_id,
                target_type=message.target_type.value,
                target_id=message.target_id,
                message_text=message.message_text,
                message_type=message.message_type,
                file_id=message.file_id
            )
            
            # Send in batches
            total_results = {
                'successful': 0,
                'failed': 0,
                'blocked': 0,
                'deleted': 0,
                'errors': []
            }
            
            batch_size = 50  # Process 50 users at a time
            total_batches = (len(targets) + batch_size - 1) // batch_size
            
            self.logger.info(f"📢 Starting broadcast to {len(targets)} users in {total_batches} batches")
            
            for batch_num in range(total_batches):
                start_index = batch_num * batch_size
                
                batch_results = await self.send_broadcast_batch(
                    targets, message, start_index, batch_size
                )
                
                # Accumulate results
                for key in ['successful', 'failed', 'blocked', 'deleted']:
                    total_results[key] += batch_results[key]
                total_results['errors'].extend(batch_results['errors'])
                
                # Log progress
                progress = ((batch_num + 1) / total_batches) * 100
                self.logger.info(f"📊 Broadcast progress: {progress:.1f}% "
                               f"({batch_num + 1}/{total_batches} batches)")
                
                # Delay between batches
                if batch_num < total_batches - 1:
                    await asyncio.sleep(self.delay_between_batches)
            
            # Calculate final results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            total_targets = len(targets)
            successful_sends = total_results['successful']
            failed_sends = total_results['failed']
            success_rate = (successful_sends / total_targets) * 100 if total_targets > 0 else 0
            
            # Log broadcast completion
            await self.db.add_log(
                user_id=message.sender_id,
                action="broadcast_completed",
                details=f"Target: {message.target_type.value}, "
                       f"Total: {total_targets}, "
                       f"Success: {successful_sends}, "
                       f"Failed: {failed_sends}, "
                       f"Rate: {success_rate:.1f}%"
            )
            
            return BroadcastResult(
                total_targets=total_targets,
                successful_sends=successful_sends,
                failed_sends=failed_sends,
                blocked_users=total_results['blocked'],
                deleted_users=total_results['deleted'],
                success_rate=success_rate,
                send_duration=duration,
                errors=total_results['errors'][:10]  # Limit errors to first 10
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error in broadcast: {e}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return BroadcastResult(
                total_targets=0,
                successful_sends=0,
                failed_sends=0,
                blocked_users=0,
                deleted_users=0,
                success_rate=0.0,
                send_duration=duration,
                errors=[f"Broadcast failed: {str(e)}"]
            )
    
    def format_broadcast_result(self, result: BroadcastResult) -> str:
        """Format broadcast result for display"""
        if result.total_targets == 0:
            return "❌ **خطأ في إرسال الإذاعة**\n\nلم يتم العثور على أي طالب أو ليس لديك صلاحيات كافية."
        
        text = f"""✅ تم إرسال الإذاعة بنجاح
📊 إحصائيات الإرسال:
• كل المستلمين: {result.total_targets:,} طالب
• الإرسال الناجح: {result.successful_sends:,} طالب
• الإرسال الفاشل: {result.failed_sends:,} طالب
• المستخدمين المحظورين: {result.blocked_users:,} طالب
• الحسابات المحذوفة: {result.deleted_users:,} طالب
• نسبة النجاح: {result.success_rate:.1f}%
• مدة الإرسال: {result.send_duration:.1f} ثانية

🎉 تم الارسال بنجاح!"""

        if result.errors:
            text += f"\n\n⚠️ الأخطاء التي حدثت:\n"
            for i, error in enumerate(result.errors[:5], 1):
                text += f"{i}. {error}\n"
            
            if len(result.errors) > 5:
                text += f"... و {len(result.errors) - 5} خطأ آخر"
        
        return text
    
    async def get_broadcast_preview_info(self, target_type: BroadcastTargetType, 
                                       target_id: Optional[int] = None,
                                       sender_id: Optional[int] = None) -> Dict[str, Any]:
        """Get preview information about broadcast targets"""
        try:
            targets = await self.get_broadcast_targets(target_type, target_id, sender_id)
            
            # Get target type name in Persian
            type_names = {
                BroadcastTargetType.ALL_USERS: "المشتركين",
                BroadcastTargetType.ALL_MANAGERS: "ممثلي الشعب",
                BroadcastTargetType.ALL_OWNERS: "كل الاساتيذ",
                BroadcastTargetType.ALL_STUDENTS: "كل الطلاب",
                BroadcastTargetType.GROUP_MANAGERS: "ممثلي الكروب",
                BroadcastTargetType.GROUP_STUDENTS: "الطلاب الكروب",
                BroadcastTargetType.CLASS_STUDENTS: "طلاب الشعبه"
            }
            
            return {
                'target_count': len(targets),
                'target_name': type_names.get(target_type, "نامشخص"),
                'targets': targets[:10]  # First 10 for preview
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting broadcast preview: {e}")
            return {
                'target_count': 0,
                'target_name': "خطاء",
                'targets': []
            }


def extract_message_data(message: Message) -> BroadcastMessage:
    """Extract broadcast message data from Telegram message"""
    message_data = BroadcastMessage(
        sender_id=message.from_user.id,
        target_type=BroadcastTargetType.ALL_USERS,  # Will be set later
        message_text=message.text or message.caption,
        caption=message.caption
    )
    
    # Determine message type and file_id
    if message.text:
        message_data.message_type = "text"
    elif message.photo:
        message_data.message_type = "photo"
        message_data.file_id = message.photo[-1].file_id
    elif message.video:
        message_data.message_type = "video"
        message_data.file_id = message.video.file_id
    elif message.document:
        message_data.message_type = "document"
        message_data.file_id = message.document.file_id
    elif message.audio:
        message_data.message_type = "audio"
        message_data.file_id = message.audio.file_id
    elif message.voice:
        message_data.message_type = "voice"
        message_data.file_id = message.voice.file_id
    else:
        message_data.message_type = "text"
        message_data.message_text = "الميديا هذي غير مدعومه"
    
    return message_data

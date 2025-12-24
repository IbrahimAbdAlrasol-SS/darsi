#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from aiogram import Bot
from database.db_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

class SmartReminderSystem:
    """Intelligent reminder system that monitors exam participation and sends comparative reminders"""
    
    def __init__(self, bot: Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db
        self.running = False
        self.check_interval = 3600  # Check every hour
        self.REMINDER_THRESHOLDS = [
            {'percent': 50, 'label': 'الأول (50%)'},
            {'percent': 70, 'label': 'الثاني (70%)'},
            {'percent': 90, 'label': 'الأخير (90%)'}
        ]
        
    async def start(self):
        """Start the smart reminder system"""
        if self.running:
            return
            
        self.running = True
        logger.info("🤖 Smart Reminder System started - 3 reminders only (50%, 70%, 90%)")
        
        # Initialize reminders tracking table if not exists
        await self._init_reminders_table()
        
        # Start the background task
        asyncio.create_task(self._reminder_loop())
    
    async def stop(self):
        """Stop the smart reminder system"""
        self.running = False
        logger.info("🤖 Smart Reminder System stopped")
    
    async def _init_reminders_table(self):
        """Initialize the reminders tracking table"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS exam_reminders (
                        exam_id INTEGER,
                        reminder_percent INTEGER,
                        sent_at TEXT,
                        PRIMARY KEY (exam_id, reminder_percent)
                    )
                """)
                await conn.commit()
        except Exception as e:
            logger.error(f"❌ Error initializing reminders table: {e}")
    
    async def _reminder_loop(self):
        """Main loop that runs the reminder checks"""
        while self.running:
            try:
                await self._check_active_exams()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Error in reminder loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _check_active_exams(self):
        """Check all active exams and send intelligent reminders"""
        try:
            # Get all active exams that haven't expired
            active_exams = await self._get_active_exams()
            
            for exam in active_exams:
                await self._process_exam_reminders(exam)
                
        except Exception as e:
            logger.error(f"❌ Error checking active exams: {e}")
    
    async def _get_active_exams(self) -> List[Dict[str, Any]]:
        """Get all active exams that are still within their duration"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT e.*, c.class_name, c.group_id, g.group_title
                    FROM exams e
                    JOIN classes c ON e.class_id = c.class_id
                    JOIN groups g ON c.group_id = g.group_id
                    WHERE e.is_active = 1 
                    AND datetime(e.creation_date, '+' || e.duration_days || ' days') > datetime('now')
                    AND datetime(e.creation_date, '+2 hours') < datetime('now')  -- At least 2 hours old
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error getting active exams: {e}")
            return []
    
    async def _process_exam_reminders(self, exam: Dict[str, Any]):
        """Process reminders for a specific exam"""
        try:
            exam_id = exam['exam_id']
            class_id = exam['class_id']
            group_id = exam['group_id']
            
            # Get all approved students in this class
            students = await self.db.get_class_students(class_id, status='approved')
            if not students:
                return
            
            # Get students who have submitted
            submitted_students = await self._get_submitted_students(exam_id)
            submitted_user_ids = {s['user_id'] for s in submitted_students}
            
            # Get students who haven't submitted
            pending_students = [s for s in students if s['user_id'] not in submitted_user_ids]
            
            if not pending_students:
                logger.info(f"✅ All students have submitted for exam {exam['title']}")
                return
            
            # Calculate exam progress
            total_students = len(students)
            submitted_count = len(submitted_students)
            submission_rate = (submitted_count / total_students) * 100 if total_students > 0 else 0
            
            # Check which reminder should be sent (50%, 70%, or 90%)
            reminder_to_send = await self._get_reminder_to_send(exam)
            
            if reminder_to_send:
                await self._send_intelligent_reminders(
                    exam, 
                    pending_students, 
                    submitted_count, 
                    total_students,
                    reminder_to_send
                )
                
        except Exception as e:
            logger.error(f"❌ Error processing exam reminders: {e}")
    
    async def _get_submitted_students(self, exam_id: int) -> List[Dict[str, Any]]:
        """Get students who have submitted for this exam"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT DISTINCT student_user_id as user_id FROM submissions 
                    WHERE exam_id = ?
                """, (exam_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error getting submitted students: {e}")
            return []
    
    async def _get_reminder_to_send(self, exam: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Determine which reminder should be sent (50%, 70%, or 90%)"""
        try:
            exam_id = exam['exam_id']
            creation_date_str = exam['creation_date']
            duration_days = exam['duration_days']
            
            # Parse creation date
            try:
                if 'T' in creation_date_str:
                    creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                    if creation_date.tzinfo:
                        creation_date = creation_date.replace(tzinfo=None)
                else:
                    creation_date = datetime.strptime(creation_date_str, '%Y-%m-%d %H:%M:%S')
            except:
                logger.warning(f"⚠️ Could not parse date for exam {exam_id}")
                return None
            
            # Calculate time progress
            now = datetime.now()
            exam_end = creation_date + timedelta(days=duration_days)
            total_duration = exam_end - creation_date
            time_elapsed = now - creation_date
            
            # Calculate percentage of time elapsed
            if total_duration.total_seconds() <= 0:
                return None
                
            percent_elapsed = (time_elapsed.total_seconds() / total_duration.total_seconds()) * 100
            
            logger.info(f"📊 Exam {exam['title']}: {percent_elapsed:.1f}% time elapsed")
            
            # Check each threshold
            for threshold in self.REMINDER_THRESHOLDS:
                threshold_percent = threshold['percent']
                
                # Check if we've crossed this threshold and haven't sent this reminder yet
                if percent_elapsed >= threshold_percent:
                    already_sent = await self._is_reminder_sent(exam_id, threshold_percent)
                    
                    if not already_sent:
                        logger.info(f"✅ Time to send {threshold['label']} reminder for exam {exam['title']}")
                        return threshold
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error checking reminder threshold: {e}")
            return None
    
    async def _is_reminder_sent(self, exam_id: int, reminder_percent: int) -> bool:
        """Check if a specific reminder has already been sent"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT COUNT(*) FROM exam_reminders 
                    WHERE exam_id = ? AND reminder_percent = ?
                """, (exam_id, reminder_percent))
                result = await cursor.fetchone()
                return result[0] > 0
        except Exception as e:
            logger.error(f"❌ Error checking if reminder sent: {e}")
            return False
    
    async def _mark_reminder_sent(self, exam_id: int, reminder_percent: int):
        """Mark a reminder as sent"""
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO exam_reminders (exam_id, reminder_percent, sent_at)
                    VALUES (?, ?, ?)
                """, (exam_id, reminder_percent, datetime.now().isoformat()))
                await conn.commit()
        except Exception as e:
            logger.error(f"❌ Error marking reminder as sent: {e}")
    
    async def _send_intelligent_reminders(self, exam: Dict[str, Any], pending_students: List[Dict[str, Any]], 
                                        submitted_count: int, total_students: int, reminder_info: Dict[str, Any]):
        """Send intelligent comparative reminders - ONLY to students, NOT to group"""
        try:
            exam_id = exam['exam_id']
            exam_title = exam['title']
            class_name = exam['class_name']
            group_id = exam['group_id']
            duration_days = exam['duration_days']
            reminder_label = reminder_info['label']
            reminder_percent = reminder_info['percent']
            
            # Calculate time remaining
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT 
                        (julianday(datetime(creation_date, '+' || duration_days || ' days')) - julianday('now')) * 24 as hours_remaining
                    FROM exams 
                    WHERE exam_id = ?
                """, (exam_id,))
                result = await cursor.fetchone()
                
                if result and result[0]:
                    hours_remaining = max(0, int(result[0]))
                else:
                    try:
                        creation_date = datetime.strptime(exam['creation_date'], '%Y-%m-%d %H:%M:%S')
                        exam_end = creation_date + timedelta(days=duration_days)
                        time_remaining = exam_end - datetime.now()
                        hours_remaining = max(0, int(time_remaining.total_seconds() / 3600))
                    except:
                        hours_remaining = duration_days * 24
            
            submission_rate = (submitted_count / total_students) * 100
            
            # ⛔ GROUP NOTIFICATIONS DISABLED - As requested by user
            # We will NOT send statistics to the group
            logger.info(f"ℹ️ Group notifications disabled - skipping group message")
            
            # Send personalized messages ONLY to pending students (exclude managers/owners)
            success_count = 0
            for student in pending_students:
                try:
                    user_id = student['user_id']
                    
                    # Check if this user is a manager or owner - don't send reminders to them
                    is_manager = await self._is_user_manager(user_id)
                    is_owner = await self._is_user_owner(user_id, group_id)
                    
                    if is_manager or is_owner:
                        logger.info(f"⏭️ Skipping reminder for {student['full_name']} (manager/owner)")
                        continue
                    
                    # Create personalized message
                    personal_msg = (
                        f"⚡ **تذكير {reminder_label}**\n\n"
                        f"مرحبًا {student['full_name']}! 👋\n\n"
                        f"📝 الواجب/التقرير: **{exam_title}**\n"
                        f"📚 الشعبة: **{class_name}**\n"
                        f"⏰ الوقت المتبقي: **{hours_remaining} ساعة**\n\n"
                        f"📊 **معلومات:**\n"
                        f"✅ {submitted_count} من زملائك أنهوا الواجب\n"
                        f"⏳ {len(pending_students)} طالب لم ينتهوا بعد\n"
                        f"📈 نسبة الإنجاز: {submission_rate:.1f}%\n\n"
                        f"🚀 **لا تتأخر!** زملاؤك يتقدمون!\n\n"
                        f"👆 اضغط /panel للإجابة الآن"
                    )
                    
                    await self.bot.send_message(user_id, personal_msg)
                    success_count += 1
                    await asyncio.sleep(0.05)  # Small delay to avoid rate limiting
                    
                except Exception as e:
                    logger.warning(f"❌ Failed to send reminder to {student.get('full_name', 'Unknown')}: {e}")
            
            # Mark this reminder as sent
            await self._mark_reminder_sent(exam_id, reminder_percent)
            
            # Log the reminder
            await self.db.add_log(
                user_id=None,
                action="smart_reminder_sent",
                details=f"exam_id:{exam_id}, reminder:{reminder_label}, sent_to:{success_count}/{len(pending_students)}, rate:{submission_rate:.1f}%"
            )
            
            logger.info(f"🤖 Reminder {reminder_label} sent for exam {exam_title}: {success_count}/{len(pending_students)} successful")
            
        except Exception as e:
            logger.error(f"❌ Error sending intelligent reminders: {e}")
    
    async def _is_user_manager(self, user_id: int) -> bool:
        """Check if user is a manager of any class"""
        try:
            managed_classes = await self.db.get_user_managed_classes(user_id)
            return len(managed_classes) > 0
        except Exception as e:
            logger.error(f"❌ Error checking if user is manager: {e}")
            return False
    
    async def _is_user_owner(self, user_id: int, group_id: int) -> bool:
        """Check if user is owner of the group"""
        try:
            return await self.db.is_group_owner(user_id, group_id)
        except Exception as e:
            logger.error(f"❌ Error checking if user is owner: {e}")
            return False

"""
Exam reminder scheduler system
"""
import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot
    from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ExamReminderScheduler:
    """Handles automated exam reminders"""
    
    def __init__(self, bot: "Bot", db: "DatabaseManager"):
        self.bot = bot
        self.db = db
        self.running = False
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info("🔔 Exam reminder scheduler started")
        
        while self.running:
            try:
                await self.process_pending_reminders()
                # Check every 5 minutes
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("🛑 Exam reminder scheduler stopped")
    
    async def process_pending_reminders(self):
        """Process all pending reminders"""
        try:
            reminders = await self.db.get_pending_reminders()
            
            for reminder in reminders:
                await self.send_reminder(reminder)
                await self.db.mark_reminder_sent(reminder['schedule_id'])
            
        except Exception as e:
            logger.error(f"❌ Error processing reminders: {e}")
    
    async def send_reminder(self, reminder: dict):
        """Send a specific reminder"""
        try:
            reminder_type = reminder['reminder_type']
            exam_id = reminder['exam_id']
            exam_title = reminder['title']
            class_name = reminder['class_name']
            group_id = reminder['group_id']
            
            if reminder_type == 'day1':
                await self.send_day1_reminder(exam_id, exam_title, class_name, group_id)
            elif reminder_type == 'end':
                await self.send_end_reminder(exam_id, exam_title, class_name, group_id)
            elif reminder_type == 'tease':
                await self.send_tease_message(exam_id, exam_title, class_name, group_id)
            
        except Exception as e:
            logger.error(f"❌ Error sending reminder: {e}")
    
    async def send_day1_reminder(self, exam_id: int, exam_title: str, class_name: str, group_id: int):
        """Send day 1 reminder to students who haven't submitted (group only)"""
        try:
            students = await self.db.get_students_without_submission(exam_id)
            
            for student in students:
                user_id = student['user_id']
                full_name = student['full_name']
                username = student.get('username', '')
                
                # Check if this user is a manager or owner - don't send reminders to them
                is_manager = await self._is_user_manager(user_id)
                is_owner = await self._is_user_owner(user_id, group_id)
                
                if is_manager or is_owner:
                    logger.info(f"⏭️ Skipping day1 reminder for {full_name} (manager/owner)")
                    continue
                
                # Tag in group only
                try:
                    user_tag = f"@{username}" if username else full_name
                    group_msg = (
                        f"📢 {user_tag}\n\n"
                        f"⏰ تذكير: امتحان **{exam_title}** بانتظار إجابتك!\n"
                        f"⚡ أسرع بالحل!"
                    )
                    await self.bot.send_message(group_id, group_msg)
                    logger.info(f"📢 Day1 reminder sent to {full_name} (group)")
                except Exception as e:
                    logger.warning(f"❌ Failed to send group reminder for {full_name}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error in day1 reminder: {e}")
    
    async def send_end_reminder(self, exam_id: int, exam_title: str, class_name: str, group_id: int):
        """Send final reminder and statistics"""
        try:
            # Get all students and submissions
            students_without = await self.db.get_students_without_submission(exam_id)
            all_submissions = await self.db.get_exam_submissions(exam_id)
            
            submitted_count = len(all_submissions)
            not_submitted_count = len(students_without)
            total_students = submitted_count + not_submitted_count
            
            # Calculate statistics
            if total_students > 0:
                submit_percentage = round((submitted_count / total_students) * 100, 1)
            else:
                submit_percentage = 0
            
            # Find fast responders (submitted in first 24 hours)
            fast_responders = []
            lazy_students = []
            
            # Sort submissions by time 
            sorted_submissions = sorted(all_submissions, key=lambda x: x.get('submission_date', ''))
            
            if sorted_submissions:
                # Get top 3 fastest
                fast_responders = sorted_submissions[:3]
            
            # Get lazy students (haven't submitted)
            lazy_students = students_without[:3]  # Show max 3
            
            # Create final message
            final_msg = (
                f"⏰ **انتهى امتحان {exam_title}!**\n\n"
                f"📊 **الإحصائيات النهائية:**\n"
                f"✅ أجابوا: {submitted_count} طالب جامعي ({submit_percentage}%)\n"
                f"❌ لم يجيبوا: {not_submitted_count} طالب جامعي\n\n"
            )
            
            if fast_responders:
                final_msg += "🏆 الأبرز/المتفوقون:\n"
                for i, resp in enumerate(fast_responders, 1):
                    name = resp.get('student_name') or resp.get('full_name', 'غير محدد')
                    final_msg += f"{i}. {name} ⚡\n"
                final_msg += "\n"
            
            if lazy_students:
                final_msg += "😴 الكسالى:\n"
                for student in lazy_students:
                    name = student['full_name']
                    username = student.get('username', '')
                    user_tag = f"@{username}" if username else name
                    final_msg += f"• {user_tag} 🐌\n"
                final_msg += "\n"
            
            final_msg += "📚 انتظروا الامتحان القادم!"
            
            await self.bot.send_message(group_id, final_msg)
            logger.info(f"📊 Final stats sent for exam {exam_title}")
            
        except Exception as e:
            logger.error(f"❌ Error in end reminder: {e}")
    
    async def send_tease_message(self, exam_id: int, exam_title: str, class_name: str, group_id: int):
        """Send teasing message comparing fast vs slow students"""
        try:
            import random
            
            # Random chance to send tease (30% probability)
            if random.random() > 0.3:
                return
                
            students_without = await self.db.get_students_without_submission(exam_id)
            all_submissions = await self.db.get_exam_submissions(exam_id)
            
            if not students_without or not all_submissions:
                return
                
            # Pick one fast responder and one lazy student
            fast_student = random.choice(all_submissions)
            lazy_student = random.choice(students_without)
            
            fast_name = fast_student.get('student_name') or fast_student.get('full_name', 'طالب شاطر')
            lazy_name = lazy_student['full_name']
            lazy_username = lazy_student.get('username', '')
            lazy_tag = f"@{lazy_username}" if lazy_username else lazy_name
            
            # More varied and less aggressive tease messages
            tease_messages = [
                f"💫 {fast_name} أبدع أكثر من {lazy_tag}! 🚀\n\n{lazy_tag} لا تخاف، بعدك إلّه وقت! ⏰",
                f"⚡ {fast_name} كان أسرع! 🏃‍♂️\n\n{lazy_tag} هدي، بعدك فرصة! 😊",
                f"🏃‍♂️ {fast_name} ركض وسوى الامتحان!\n\n{lazy_tag} إنت بعدك تكدر! 💪",
                f"🎯 {fast_name} ورّاك شلون ينحل الامتحان!\n\n{lazy_tag} شد حيلك! 🚀",
                f"🌟 {fast_name} كلش ممتاز!\n\n{lazy_tag} إنت بعدك تكدر تصير مثله! ✨",
                f"🔥 {fast_name} أبدع كلش!\n\n{lazy_tag} أطلّع حماسك! 💥"
            ]
            
            tease_msg = random.choice(tease_messages)
            
            await self.bot.send_message(group_id, tease_msg)
            logger.info(f"😏 Tease message sent for exam {exam_title}")
            
        except Exception as e:
            logger.error(f"❌ Error in tease message: {e}")
    
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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiosqlite
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class DatabaseManager:
    """Database manager for school bot using SQLite"""
    
    def __init__(self, db_path: str = "school_bot.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
    
    async def init_database(self):
        """Initialize database with all required tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                await db.commit()
                self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all required tables - simplified version"""
        
        # Users table - stores admin and managers only
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_blocked INTEGER DEFAULT 0,
                is_superadmin INTEGER DEFAULT 0,
                join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Classes table - stores classes (مراحل/شعب) with manager
        await db.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                class_id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL UNIQUE,
                manager_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES users (user_id)
            )
        """)
        
        # Subjects table - stores subjects (مواد) for each class
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                subject_name TEXT NOT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes (class_id),
                UNIQUE(class_id, subject_name)
            )
        """)
        
        # Files table - stores files uploaded by managers
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                telegram_file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                uploaded_by INTEGER NOT NULL,
                upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects (subject_id),
                FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
            )
        """)
        
        # Logs table - stores important events
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Create indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_classes_manager ON classes(manager_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subjects_class ON subjects(class_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_files_subject ON files(subject_id)")
    
    async def get_connection(self):
        """Get database connection"""
        return await aiosqlite.connect(self.db_path)
    
    # USER MANAGEMENT METHODS
    
    async def add_user(self, user_id: int, full_name: str, username: str = None, 
                      first_name: str = None, last_name: str = None) -> bool:
        """Add or update user in database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, full_name, username, first_name, last_name, last_activity)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, full_name, username, first_name, last_name))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error adding user {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting user {user_id}: {e}")
            return None
    
    async def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return bool(row[0]) if row else False
        except Exception as e:
            self.logger.error(f"❌ Error checking block status for user {user_id}: {e}")
            return False
    
    async def is_superadmin(self, user_id: int) -> bool:
        """Check if user is superadmin"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT is_superadmin FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return bool(row[0]) if row else False
        except Exception as e:
            self.logger.error(f"❌ Error checking superadmin status for user {user_id}: {e}")
            return False

    async def set_superadmin(self, user_id: int, is_superadmin: bool = True) -> bool:
        """Set or unset superadmin flag for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET is_superadmin = ? WHERE user_id = ?",
                    (1 if is_superadmin else 0, user_id),
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error setting superadmin for user {user_id}: {e}")
            return False
    
    async def update_user_username(self, user_id: int, username: str) -> bool:
        """Update user's username"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating username for user {user_id}: {e}")
            return False
    
    async def block_user(self, user_id: int, block: bool = True) -> bool:
        """Block or unblock user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (int(block), user_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error blocking user {user_id}: {e}")
            return False
    
    async def unblock_user(self, user_id: int) -> bool:
        """Unblock user (alias for block_user with False)"""
        return await self.block_user(user_id, False)
    
    # CLASS-LEVEL BLOCK METHODS (for managers)
    
    async def block_user_from_class(self, user_id: int, class_id: int, blocked_by: int, reason: str = None) -> bool:
        """Block user from specific class (for managers)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO class_blocks (user_id, class_id, blocked_by, block_reason)
                    VALUES (?, ?, ?, ?)
                """, (user_id, class_id, blocked_by, reason))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error blocking user {user_id} from class {class_id}: {e}")
            return False
    
    async def unblock_user_from_class(self, user_id: int, class_id: int) -> bool:
        """Unblock user from specific class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM class_blocks WHERE user_id = ? AND class_id = ?", (user_id, class_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error unblocking user {user_id} from class {class_id}: {e}")
            return False
    
    async def is_user_blocked_from_class(self, user_id: int, class_id: int) -> bool:
        """Check if user is blocked from specific class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM class_blocks WHERE user_id = ? AND class_id = ?", (user_id, class_id)) as cursor:
                    return await cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"❌ Error checking class block status: {e}")
            return False
    
    # GROUP-LEVEL BLOCK METHODS (for owners)
    
    async def block_user_from_group(self, user_id: int, group_id: int, blocked_by: int, reason: str = None) -> bool:
        """Block user from entire group (for owners)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO group_blocks (user_id, group_id, blocked_by, block_reason)
                    VALUES (?, ?, ?, ?)
                """, (user_id, group_id, blocked_by, reason))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error blocking user {user_id} from group {group_id}: {e}")
            return False
    
    async def unblock_user_from_group(self, user_id: int, group_id: int) -> bool:
        """Unblock user from group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM group_blocks WHERE user_id = ? AND group_id = ?", (user_id, group_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error unblocking user {user_id} from group {group_id}: {e}")
            return False
    
    async def is_user_blocked_from_group(self, user_id: int, group_id: int) -> bool:
        """Check if user is blocked from entire group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM group_blocks WHERE user_id = ? AND group_id = ?", (user_id, group_id)) as cursor:
                    return await cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"❌ Error checking group block status: {e}")
            return False
    
    async def get_user_blocks_in_group(self, user_id: int, group_id: int) -> Dict[str, Any]:
        """Get comprehensive block status for user in group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Check global block
                global_blocked = await self.is_user_blocked(user_id)
                
                # Check group block
                group_blocked = await self.is_user_blocked_from_group(user_id, group_id)
                
                # Check class blocks
                async with db.execute("""
                    SELECT cb.class_id, c.class_name 
                    FROM class_blocks cb
                    JOIN classes c ON cb.class_id = c.class_id
                    WHERE cb.user_id = ? AND c.group_id = ?
                """, (user_id, group_id)) as cursor:
                    class_blocks = [dict(row) for row in await cursor.fetchall()]
                
                return {
                    'global_blocked': global_blocked,
                    'group_blocked': group_blocked,
                    'class_blocks': class_blocks,
                    'any_block': global_blocked or group_blocked or len(class_blocks) > 0
                }
        except Exception as e:
            self.logger.error(f"❌ Error getting user blocks: {e}")
            return {'global_blocked': False, 'group_blocked': False, 'class_blocks': [], 'any_block': False}
    
    async def update_submission_review(self, submission_id: int, status: str, reviewed_by: int) -> bool:
        """Update submission review status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE submissions 
                    SET status = ?, reviewed_by = ?, review_date = CURRENT_TIMESTAMP
                    WHERE submission_id = ?
                """, (status, reviewed_by, submission_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating submission review: {e}")
            return False
    
    async def update_student_status(self, user_id: int, class_id: int, status: str) -> bool:
        """Update student registration status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE students 
                    SET status = ?
                    WHERE user_id = ? AND class_id = ?
                """, (status, user_id, class_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating student status: {e}")
            return False
    
    # GROUP MANAGEMENT METHODS
    
    async def add_group(self, group_id: int, group_title: str, owner_id: int, group_username: str = None) -> bool:
        """Add or update group in database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO groups (group_id, group_title, group_username, owner_id)
                    VALUES (?, ?, ?, ?)
                """, (group_id, group_title, group_username, owner_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error adding group {group_id}: {e}")
            return False
    
    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get group by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting group {group_id}: {e}")
            return None
    
    async def is_group_owner(self, user_id: int, group_id: int) -> bool:
        """Check if user is owner of group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT owner_id FROM groups WHERE group_id = ?", (group_id,)) as cursor:
                    row = await cursor.fetchone()
                    # -1 means no owner (removed owner)
                    return row[0] == user_id and row[0] != -1 if row else False
        except Exception as e:
            self.logger.error(f"❌ Error checking group ownership: {e}")
            return False
    
    async def get_user_groups(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all groups where user is owner"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                # Exclude groups with owner_id = -1 (no owner)
                async with db.execute("SELECT * FROM groups WHERE owner_id = ? AND is_active = 1 AND owner_id != -1", (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting user groups: {e}")
            return []
    
    async def remove_group_owner(self, group_id: int) -> bool:
        """Remove owner from group (set owner_id to a dummy value)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Since owner_id is NOT NULL, we set it to -1 (dummy value for "no owner")
                await db.execute("UPDATE groups SET owner_id = -1 WHERE group_id = ?", (group_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error removing group owner: {e}")
            return False
    
    # CLASS MANAGEMENT METHODS
    
    async def add_class(self, group_id: int, class_name: str, manager_id: int = None) -> Optional[int]:
        """Add class to group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO classes (group_id, class_name, manager_id)
                    VALUES (?, ?, ?)
                """, (group_id, class_name, manager_id))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error adding class: {e}")
            return None
    
    async def get_class(self, class_id: int) -> Optional[Dict[str, Any]]:
        """Get class by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM classes WHERE class_id = ?", (class_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting class {class_id}: {e}")
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get full user row by user_id"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting user by id: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting user by username: {e}")
            return None

    async def get_user_managed_classes_in_group(self, user_id: int, group_id: int) -> List[Dict[str, Any]]:
        """Get classes managed by a user within a specific group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM classes WHERE group_id = ? AND manager_id = ? AND is_active = 1",
                    (group_id, user_id),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting user managed classes in group: {e}")
            return []

    async def get_group_students_by_status(self, group_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Return students of a group, optionally filtered by status (approved/pending/blocked/rejected)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                base_sql = (
                    "SELECT s.*, c.class_name, c.class_id, g.group_title, u.full_name AS user_full_name, u.username, u.is_blocked "
                    "FROM students s "
                    "JOIN classes c ON s.class_id = c.class_id "
                    "JOIN groups g ON s.group_id = g.group_id "
                    "LEFT JOIN users u ON s.user_id = u.user_id "
                    "WHERE s.group_id = ?"
                )
                params = [group_id]
                if status:
                    base_sql += " AND s.status = ?"
                    params.append(status)
                async with db.execute(base_sql, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting group students by status: {e}")
            return []

    async def get_group_classes(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all classes in a group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM classes WHERE group_id = ? AND is_active = 1", (group_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting group classes: {e}")
            return []
    
    async def set_class_manager(self, class_id: int, manager_id: int) -> bool:
        """Set manager for a class"""
        try:
            # If manager_id is None, we're removing the manager
            if manager_id is not None:
                # Check if user is registered as student anywhere - prevent role conflict
                student_registrations = await self.get_student_registrations(manager_id)
                if student_registrations:
                    self.logger.warning(f"🚨 Cannot set user {manager_id} as manager: they are registered as student")
                    return False
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE classes SET manager_id = ? WHERE class_id = ?", (manager_id, class_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error setting class manager: {e}")
            return False
    
    async def is_class_manager(self, user_id: int, class_id: int) -> bool:
        """Check if user is manager of class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT manager_id FROM classes WHERE class_id = ?", (class_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] == user_id if row else False
        except Exception as e:
            self.logger.error(f"❌ Error checking class manager: {e}")
            return False
    
    async def get_user_managed_classes(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all classes managed by user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT c.*, g.group_title 
                    FROM classes c 
                    JOIN groups g ON c.group_id = g.group_id 
                    WHERE c.manager_id = ? AND c.is_active = 1
                """, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting managed classes: {e}")
            return []
    
    async def delete_class(self, class_id: int) -> bool:
        """Cascade delete class-related data and completely remove class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # DISABLE foreign keys temporarily for cascade delete
                await db.execute("PRAGMA foreign_keys = OFF;")
                
                # Start transaction
                await db.execute("BEGIN TRANSACTION;")
                
                try:
                    # Collect exam ids for this class
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT exam_id FROM exams WHERE class_id = ?", (class_id,)) as cursor:
                        exam_rows = await cursor.fetchall()
                        exam_ids = [row["exam_id"] for row in exam_rows]
                    
                    # Delete submissions for these exams (child records first)
                    if exam_ids:
                        placeholders = ",".join(["?"] * len(exam_ids))
                        await db.execute(f"DELETE FROM submissions WHERE exam_id IN ({placeholders})", exam_ids)
                        await db.execute(f"DELETE FROM reminders WHERE exam_id IN ({placeholders})", exam_ids)
                    
                    # Delete exams (child records)
                    await db.execute("DELETE FROM exams WHERE class_id = ?", (class_id,))
                    
                    # Delete students in this class (child records)
                    await db.execute("DELETE FROM students WHERE class_id = ?", (class_id,))
                    
                    # Finally delete class (parent record)
                    await db.execute("DELETE FROM classes WHERE class_id = ?", (class_id,))
                    
                    # Commit transaction
                    await db.execute("COMMIT;")
                    
                    # Re-enable foreign keys
                    await db.execute("PRAGMA foreign_keys = ON;")
                    
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    await db.execute("ROLLBACK;")
                    # Re-enable foreign keys even on error
                    await db.execute("PRAGMA foreign_keys = ON;")
                    raise e
                    
        except Exception as e:
            self.logger.error(f"❌ Error deleting class: {e}")
            return False
    
    # STUDENT MANAGEMENT METHODS
    
    async def register_student(self, user_id: int, group_id: int, class_id: int, 
                             full_name: str, gender: str, course: str, school_session: str) -> Optional[int]:
        """Register student for a class or update existing rejected registration"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if user already has a registration in this group
                async with db.execute("""
                    SELECT id, status FROM students 
                    WHERE user_id = ? AND group_id = ?
                """, (user_id, group_id)) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    existing_id, status = existing
                    if status == 'approved':
                        # User is already approved, cannot re-register
                        return None
                    elif status in ['rejected', 'blocked']:
                        # Update existing rejected/blocked registration
                        await db.execute("""
                            UPDATE students 
                            SET class_id = ?, full_name = ?, gender = ?, course = ?, 
                                school_session = ?, status = 'pending', registration_date = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (class_id, full_name, gender, course, school_session, existing_id))
                        await db.commit()
                        return existing_id
                    elif status == 'pending':
                        # Update existing pending registration
                        await db.execute("""
                            UPDATE students 
                            SET class_id = ?, full_name = ?, gender = ?, course = ?, 
                                school_session = ?, registration_date = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (class_id, full_name, gender, course, school_session, existing_id))
                        await db.commit()
                        return existing_id
                
                # No existing registration, create new one
                cursor = await db.execute("""
                    INSERT INTO students (user_id, group_id, class_id, full_name, gender, course, school_session)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, group_id, class_id, full_name, gender, course, school_session))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error registering student: {e}")
            return None
    
    async def add_student(self, user_id: int, full_name: str, class_id: int, 
                         course: str, school_session: str, status: str = 'pending', 
                         gender: str = None, approved_by: int = None, approval_date: str = None) -> Optional[int]:
        """Add a student directly to a class (for link registrations)"""
        try:
            from datetime import datetime
            async with aiosqlite.connect(self.db_path) as db:
                # Get group_id from class
                async with db.execute("SELECT group_id FROM classes WHERE class_id = ?", (class_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        self.logger.error(f"❌ Class {class_id} not found")
                        return None
                    group_id = row[0]
                
                # Check if user already registered in this group
                async with db.execute(
                    "SELECT id, status FROM students WHERE user_id = ? AND group_id = ?",
                    (user_id, group_id)
                ) as cursor:
                    existing = await cursor.fetchone()
                    if existing:
                        existing_id, existing_status = existing
                        self.logger.warning(f"User {user_id} already registered in group {group_id} with status {existing_status}")
                        # Update existing registration instead
                        update_fields = "class_id = ?, full_name = ?, course = ?, school_session = ?, status = ?"
                        update_values = [class_id, full_name, course, school_session, status]
                        
                        if approved_by is not None:
                            update_fields += ", approved_by = ?, approval_date = ?"
                            update_values.extend([approved_by, approval_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                        
                        update_values.append(existing_id)
                        await db.execute(f"UPDATE students SET {update_fields} WHERE id = ?", tuple(update_values))
                        await db.commit()
                        return existing_id
                
                # Insert new student
                if approved_by is not None and approval_date is None:
                    approval_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor = await db.execute("""
                    INSERT INTO students (user_id, group_id, class_id, full_name, gender, course, school_session, status, approved_by, approval_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, group_id, class_id, full_name, gender, course, school_session, status, approved_by, approval_date))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error adding student: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    async def get_student_by_user_and_class(self, user_id: int, class_id: int) -> Optional[Dict[str, Any]]:
        """Check if user is registered in a specific class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT s.*, c.class_name, g.group_title 
                    FROM students s 
                    JOIN classes c ON s.class_id = c.class_id 
                    JOIN groups g ON s.group_id = g.group_id 
                    WHERE s.user_id = ? AND s.class_id = ?
                """, (user_id, class_id)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting student by user and class: {e}")
            return None
    
    async def get_student_registration(self, user_id: int, group_id: int) -> Optional[Dict[str, Any]]:
        """Get student registration in a group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT s.*, c.class_name, g.group_title 
                    FROM students s 
                    JOIN classes c ON s.class_id = c.class_id 
                    JOIN groups g ON s.group_id = g.group_id 
                    WHERE s.user_id = ? AND s.group_id = ?
                """, (user_id, group_id)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting student registration: {e}")
            return None
    
    async def get_student_registrations(self, user_id: int, group_id: int = None) -> List[Dict[str, Any]]:
        """Get all student registrations for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if group_id:
                    # Get registrations for specific group
                    async with db.execute("""
                        SELECT s.*, c.class_name, g.group_title 
                        FROM students s 
                        JOIN classes c ON s.class_id = c.class_id 
                        JOIN groups g ON s.group_id = g.group_id 
                        WHERE s.user_id = ? AND s.group_id = ? AND s.status = 'approved'
                    """, (user_id, group_id)) as cursor:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]
                else:
                    # Get all registrations
                    async with db.execute("""
                        SELECT s.*, c.class_name, g.group_title 
                        FROM students s 
                        JOIN classes c ON s.class_id = c.class_id 
                        JOIN groups g ON s.group_id = g.group_id 
                        WHERE s.user_id = ? AND s.status = 'approved'
                    """, (user_id,)) as cursor:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting student registrations: {e}")
            return []
    
    async def approve_student(self, student_id: int, status: str, approver_id: int) -> bool:
        """Approve/reject/block student registration with concurrency guard."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if status in ("approved", "rejected"):
                    cursor = await db.execute(
                        """
                        UPDATE students
                        SET status = ?, approval_date = CURRENT_TIMESTAMP, approved_by = ?
                        WHERE id = ? AND status = 'pending'
                        """,
                        (status, approver_id, student_id),
                    )
                elif status == "blocked":
                    cursor = await db.execute(
                        """
                        UPDATE students
                        SET status = 'blocked', approval_date = CURRENT_TIMESTAMP, approved_by = ?
                        WHERE id = ? AND status != 'blocked'
                        """,
                        (approver_id, student_id),
                    )
                else:
                    return False
                await db.commit()
                return cursor.rowcount and cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"❌ Error approving student: {e}")
            return False

    async def get_student_request(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Get a single student registration with joins (for review UI)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT s.*, c.class_name, g.group_title, u.full_name as user_full_name, u.username
                    FROM students s 
                    JOIN classes c ON s.class_id = c.class_id 
                    JOIN groups g ON s.group_id = g.group_id 
                    JOIN users u ON s.user_id = u.user_id
                    WHERE s.id = ?
                """, (student_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting student request: {e}")
            return None
    
    async def get_pending_registrations(self, group_id: int = None, class_id: int = None) -> List[Dict[str, Any]]:
        """Get pending student registrations"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                query = """
                    SELECT s.*, c.class_name, g.group_title, u.full_name as user_full_name, u.username
                    FROM students s 
                    JOIN classes c ON s.class_id = c.class_id 
                    JOIN groups g ON s.group_id = g.group_id 
                    JOIN users u ON s.user_id = u.user_id
                    WHERE s.status = 'pending'
                """
                params = []
                
                if group_id:
                    query += " AND s.group_id = ?"
                    params.append(group_id)
                
                if class_id:
                    query += " AND s.class_id = ?"
                    params.append(class_id)
                
                query += " ORDER BY s.registration_date ASC"
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting pending registrations: {e}")
            return []
    
    async def get_class_students(self, class_id: int, status: str = 'approved') -> List[Dict[str, Any]]:
        """Get students in a class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if status is None:
                    # Get all students regardless of status
                    async with db.execute("""
                        SELECT s.*, u.username, u.first_name, u.last_name
                        FROM students s 
                        JOIN users u ON s.user_id = u.user_id 
                        WHERE s.class_id = ?
                        ORDER BY s.full_name
                    """, (class_id,)) as cursor:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]
                else:
                    # Get students with specific status
                    async with db.execute("""
                        SELECT s.*, u.username, u.first_name, u.last_name
                        FROM students s 
                        JOIN users u ON s.user_id = u.user_id 
                        WHERE s.class_id = ? AND s.status = ?
                        ORDER BY s.full_name
                    """, (class_id, status)) as cursor:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting class students: {e}")
            return []
    
    # LOG METHODS
    
    async def add_log(self, user_id: int, action: str, details: str = None):
        """Add log entry"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO logs (user_id, action, details)
                    VALUES (?, ?, ?)
                """, (user_id, action, details))
                await db.commit()
        except Exception as e:
            self.logger.error(f"❌ Error adding log: {e}")
    
    # STATISTICS METHODS
    
    async def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total users
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    row = await cursor.fetchone()
                    stats['total_users'] = row[0]
                
                # Active users (not blocked)
                async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0") as cursor:
                    row = await cursor.fetchone()
                    stats['active_users'] = row[0]
                
                # Blocked users
                async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1") as cursor:
                    row = await cursor.fetchone()
                    stats['blocked_users'] = row[0]
                
                # Superadmins
                async with db.execute("SELECT COUNT(*) FROM users WHERE is_superadmin = 1") as cursor:
                    row = await cursor.fetchone()
                    stats['superadmins'] = row[0]
                
                return stats
        except Exception as e:
            self.logger.error(f"❌ Error getting user stats: {e}")
            return {}
    
    async def get_group_stats(self) -> Dict[str, int]:
        """Get group statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total groups
                async with db.execute("SELECT COUNT(*) FROM groups WHERE is_active = 1") as cursor:
                    row = await cursor.fetchone()
                    stats['total_groups'] = row[0]
                
                # Total classes
                async with db.execute("SELECT COUNT(*) FROM classes WHERE is_active = 1") as cursor:
                    row = await cursor.fetchone()
                    stats['total_classes'] = row[0]
                
                return stats
        except Exception as e:
            self.logger.error(f"❌ Error getting group stats: {e}")
            return {}

    async def get_all_groups(self) -> List[Dict[str, Any]]:
        """List all active groups"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT group_id, group_title FROM groups WHERE is_active = 1 ORDER BY created_date DESC") as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting all groups: {e}")
            return []

    async def count_group_users(self, group_id: int) -> int:
        """Count distinct users related to a group (by registrations)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM students WHERE group_id = ?",
                    (group_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            self.logger.error(f"❌ Error counting group users: {e}")
            return 0

    async def get_group_users(self, group_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get paginated distinct users in a group with basic info and block flag."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = (
                    """
                    SELECT u.user_id, u.full_name, u.username, u.is_blocked,
                           (SELECT COUNT(*) FROM classes c WHERE c.group_id = ? AND c.manager_id = u.user_id) AS manager_of,
                           CASE WHEN EXISTS(SELECT 1 FROM group_blocks gb WHERE gb.user_id = u.user_id AND gb.group_id = ?) 
                                THEN 1 ELSE 0 END AS group_blocked
                    FROM users u
                    WHERE u.user_id IN (SELECT DISTINCT s.user_id FROM students s WHERE s.group_id = ?)
                    ORDER BY u.full_name COLLATE NOCASE ASC
                    LIMIT ? OFFSET ?
                    """
                )
                async with db.execute(query, (group_id, group_id, group_id, limit, offset)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting group users: {e}")
            return []

    async def get_user_manager_classes_in_group(self, user_id: int, group_id: int) -> List[Dict[str, Any]]:
        """Return classes in a group where this user is manager."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT class_id, class_name FROM classes WHERE group_id = ? AND manager_id = ? AND is_active = 1",
                    (group_id, user_id),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting user's manager classes in group: {e}")
            return []

    async def update_user_info(self, user_id: int, full_name: str = None, username: str = None) -> bool:
        """Update user basic info."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if full_name is not None and username is not None:
                    await db.execute("UPDATE users SET full_name = ?, username = ? WHERE user_id = ?", (full_name, username, user_id))
                elif full_name is not None:
                    await db.execute("UPDATE users SET full_name = ? WHERE user_id = ?", (full_name, user_id))
                elif username is not None:
                    await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
                else:
                    return True
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating user {user_id}: {e}")
            return False
    
    async def get_student_stats(self, group_id: int = None, class_id: int = None) -> Dict[str, int]:
        """Get student statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                base_query = "SELECT COUNT(*) FROM students WHERE 1=1"
                params = []
                
                if group_id:
                    base_query += " AND group_id = ?"
                    params.append(group_id)
                
                if class_id:
                    base_query += " AND class_id = ?"
                    params.append(class_id)
                
                # Total students
                async with db.execute(base_query, params) as cursor:
                    row = await cursor.fetchone()
                    stats['total_students'] = row[0]
                
                # Approved students
                async with db.execute(base_query + " AND status = 'approved'", params) as cursor:
                    row = await cursor.fetchone()
                    stats['approved_students'] = row[0]
                
                # Pending students
                async with db.execute(base_query + " AND status = 'pending'", params) as cursor:
                    row = await cursor.fetchone()
                    stats['pending_students'] = row[0]
                
                # Morning shift students
                async with db.execute(base_query + " AND school_session = 'صباحي' AND status = 'approved'", params) as cursor:
                    row = await cursor.fetchone()
                    stats['morning_students'] = row[0]
                
                # Evening shift students
                async with db.execute(base_query + " AND school_session = 'مسائي' AND status = 'approved'", params) as cursor:
                    row = await cursor.fetchone()
                    stats['evening_students'] = row[0]
                
                # Male students
                async with db.execute(base_query + " AND gender = 'طالب جامعي' AND status = 'approved'", params) as cursor:
                    row = await cursor.fetchone()
                    stats['male_students'] = row[0]
                
                # Female students
                async with db.execute(base_query + " AND gender = 'طالبة جامعية' AND status = 'approved'", params) as cursor:
                    row = await cursor.fetchone()
                    stats['female_students'] = row[0]
                
                return stats
        except Exception as e:
            self.logger.error(f"❌ Error getting student stats: {e}")
            return {}
    
    # EXAM MANAGEMENT METHODS
    
    async def add_exam(self, class_id: int, title: str, duration_days: int,
                      created_by: int, content_type: str = None, file_id: str = None, caption: str = None,
                      assigned_teacher_id: int = None, max_score: int = 20) -> Optional[int]:
        """Add exam/lesson to class (uses exams schema: file_id, creation_date, is_active)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO exams (class_id, title, content_type, file_id, caption, duration_days, created_by, is_active, assigned_teacher_id, max_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (class_id, title, content_type, file_id, caption, duration_days, created_by, assigned_teacher_id, max_score))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error adding exam: {e}")
            return None
    
    async def get_class_exams(self, class_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get exams for a class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if status == 'active':
                    # Only show active exams that haven't expired
                    cursor = await db.execute("""
                        SELECT * FROM exams 
                        WHERE class_id = ? AND is_active = 1
                        AND datetime(creation_date, '+' || duration_days || ' days') > datetime('now')
                        ORDER BY creation_date DESC
                    """, (class_id,))
                elif status == 'expired':
                    # Show exams that have expired
                    cursor = await db.execute("""
                        SELECT * FROM exams 
                        WHERE class_id = ? AND is_active = 1
                        AND datetime(creation_date, '+' || duration_days || ' days') <= datetime('now')
                        ORDER BY creation_date DESC
                    """, (class_id,))
                elif status == 'archived':
                    cursor = await db.execute("""
                        SELECT * FROM exams WHERE class_id = ? AND is_active = 0
                        ORDER BY creation_date DESC
                    """, (class_id,))
                else:
                    cursor = await db.execute("""
                        SELECT * FROM exams WHERE class_id = ?
                        ORDER BY creation_date DESC
                    """, (class_id,))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting class exams: {e}")
            return []
    
    async def is_exam_expired(self, exam_id: int) -> bool:
        """Check if exam has expired"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT datetime(creation_date, '+' || duration_days || ' days') <= datetime('now') as expired
                    FROM exams WHERE exam_id = ?
                """, (exam_id,))
                row = await cursor.fetchone()
                return bool(row[0]) if row else True
        except Exception as e:
            self.logger.error(f"❌ Error checking exam expiry: {e}")
            return True
    
    async def get_exam(self, exam_id: int) -> Optional[Dict[str, Any]]:
        """Get exam by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,))
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            self.logger.error(f"❌ Error getting exam: {e}")
            return None
    
    async def get_student_submission(self, exam_id: int, student_user_id: int) -> Optional[Dict[str, Any]]:
        """Get student's submission for an exam"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM submissions 
                    WHERE exam_id = ? AND student_user_id = ?
                """, (exam_id, student_user_id))
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            self.logger.error(f"❌ Error getting student submission: {e}")
            return None

    async def submit_exam_answer(self, exam_id: int, student_user_id: int, 
                               answer_text: str = None, answer_file_id: str = None) -> Optional[int]:
        """Submit student answer to exam (only if not already submitted)"""
        try:
            # Check if already submitted
            existing = await self.get_student_submission(exam_id, student_user_id)
            if existing:
                self.logger.warning(f"Student {student_user_id} already submitted for exam {exam_id}")
                return None
                
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO submissions 
                    (exam_id, student_user_id, answer_text, answer_file_id, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (exam_id, student_user_id, answer_text, answer_file_id))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error submitting exam answer: {e}")
            return None
    
    async def get_submission_by_id(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """Get submission by ID with student and exam details"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT s.*, 
                           s.student_user_id as user_id,
                           u.full_name, 
                           u.username, 
                           st.full_name as student_name, 
                           e.title as exam_title
                    FROM submissions s
                    JOIN users u ON s.student_user_id = u.user_id
                    LEFT JOIN students st ON s.student_user_id = st.user_id
                    JOIN exams e ON s.exam_id = e.exam_id
                    WHERE s.submission_id = ?
                """, (submission_id,))
                
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            self.logger.error(f"❌ Error getting submission by ID: {e}")
            return None

    async def get_exam_submissions(self, exam_id: int) -> List[Dict[str, Any]]:
        """Get all submissions for an exam with class and course info"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT s.*, 
                           u.full_name, 
                           u.username, 
                           COALESCE(st.full_name, u.full_name) as student_name,
                           st.course, 
                           st.school_session, 
                           c.class_name,
                           s.score_numerator,
                           s.score_denominator
                    FROM submissions s
                    JOIN users u ON s.student_user_id = u.user_id
                    LEFT JOIN students st ON s.student_user_id = st.user_id
                    LEFT JOIN classes c ON st.class_id = c.class_id
                    WHERE s.exam_id = ?
                    ORDER BY s.submission_date DESC
                """, (exam_id,))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting exam submissions: {e}")
            return []
    
    async def update_submission_status(self, submission_id: int, status: str, 
                                     feedback: str = None) -> bool:
        """Update submission status (approved/rejected/warned/expelled)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE submissions 
                    SET status = ?, feedback = ?, review_date = CURRENT_TIMESTAMP
                    WHERE submission_id = ?
                """, (status, feedback, submission_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating submission status: {e}")
            return False
    
    async def update_submission_score(self, submission_id: int, score_numerator: float, 
                                     score_denominator: float, reviewed_by: int, feedback: str = None) -> bool:
        """Update submission with numeric score"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Determine status based on score percentage
                percentage = (score_numerator / score_denominator * 100) if score_denominator > 0 else 0
                if percentage >= 50:
                    status = 'passed'
                else:
                    status = 'failed'
                
                await db.execute("""
                    UPDATE submissions 
                    SET score_numerator = ?, score_denominator = ?, status = ?, reviewed_by = ?, 
                        feedback = ?, review_date = CURRENT_TIMESTAMP
                    WHERE submission_id = ?
                """, (score_numerator, score_denominator, status, reviewed_by, feedback, submission_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating submission score: {e}")
            return False
    
    async def delete_submission(self, submission_id: int) -> bool:
        """Delete a submission completely to allow re-submission"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM submissions WHERE submission_id = ?
                """, (submission_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting submission: {e}")
            return False

    # USER CONTEXT MANAGEMENT METHODS
    
    async def set_user_context(self, user_id: int, group_id: int = None, class_id: int = None) -> bool:
        """Set user's current group/class context"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_context (user_id, current_group_id, current_class_id, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, group_id, class_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error setting user context: {e}")
            return False
    
    async def get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current context"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT uc.*, g.group_title, c.class_name
                    FROM user_context uc
                    LEFT JOIN groups g ON uc.current_group_id = g.group_id
                    LEFT JOIN classes c ON uc.current_class_id = c.class_id
                    WHERE uc.user_id = ?
                """, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting user context: {e}")
            return None
    
    async def clear_user_context(self, user_id: int) -> bool:
        """Clear user's context"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM user_context WHERE user_id = ?", (user_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error clearing user context: {e}")
            return False

    # COMPREHENSIVE STUDENT INFO METHODS
    
    async def get_student_comprehensive_info(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive student information including all groups and classes"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Get user basic info
                async with db.execute("""
                    SELECT * FROM users WHERE user_id = ?
                """, (user_id,)) as cursor:
                    user_row = await cursor.fetchone()
                    if not user_row:
                        return None
                    user_info = dict(user_row)
                
                # Get all student registrations with group and class info
                async with db.execute("""
                    SELECT s.*, g.group_title, g.group_username, c.class_name, c.manager_id,
                           u_manager.full_name as manager_name
                    FROM students s
                    JOIN groups g ON s.group_id = g.group_id
                    JOIN classes c ON s.class_id = c.class_id
                    LEFT JOIN users u_manager ON c.manager_id = u_manager.user_id
                    WHERE s.user_id = ?
                    ORDER BY s.registration_date DESC
                """, (user_id,)) as cursor:
                    registrations = [dict(row) for row in await cursor.fetchall()]
                
                # Get managed classes info
                async with db.execute("""
                    SELECT c.*, g.group_title, g.group_username
                    FROM classes c
                    JOIN groups g ON c.group_id = g.group_id
                    WHERE c.manager_id = ? AND c.is_active = 1
                """, (user_id,)) as cursor:
                    managed_classes = [dict(row) for row in await cursor.fetchall()]
                
                # Get owned groups info
                async with db.execute("""
                    SELECT * FROM groups WHERE owner_id = ? AND is_active = 1
                """, (user_id,)) as cursor:
                    owned_groups = [dict(row) for row in await cursor.fetchall()]
                
                return {
                    'user_info': user_info,
                    'registrations': registrations,
                    'managed_classes': managed_classes,
                    'owned_groups': owned_groups
                }
        except Exception as e:
            self.logger.error(f"❌ Error getting comprehensive student info: {e}")
            return None
    
    async def get_student_registrations_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all student registrations for a specific user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT s.*, g.group_title, g.group_username, c.class_name, c.manager_id,
                           u_manager.full_name as manager_name
                    FROM students s
                    JOIN groups g ON s.group_id = g.group_id
                    JOIN classes c ON s.class_id = c.class_id
                    LEFT JOIN users u_manager ON c.manager_id = u_manager.user_id
                    WHERE s.user_id = ?
                    ORDER BY s.registration_date DESC
                """, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting student registrations by user: {e}")
            return []

    async def delete_student_registration(self, user_id: int, group_id: int) -> bool:
        """Delete student registration (for rejected registrations)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM students 
                    WHERE user_id = ? AND group_id = ?
                """, (user_id, group_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting student registration: {e}")
            return False
    
    async def delete_student_from_class(self, user_id: int, class_id: int) -> bool:
        """Delete student from specific class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM students 
                    WHERE user_id = ? AND class_id = ?
                """, (user_id, class_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting student from class: {e}")
            return False
    
    async def update_student_status(self, user_id: int, class_id: int, status: str) -> bool:
        """Update student registration status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE students 
                    SET status = ?, approval_date = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND class_id = ?
                """, (status, user_id, class_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating student status: {e}")
            return False

    # ======================= BROADCAST METHODS =======================
    
    async def get_group_managers_for_broadcast(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all class managers in a specific group for broadcast messaging"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT DISTINCT u.user_id, u.full_name, u.username, u.first_name, u.last_name,
                           c.class_name, c.class_id
                    FROM users u
                    JOIN classes c ON u.user_id = c.manager_id
                    WHERE c.group_id = ? AND c.is_active = 1 AND u.is_blocked = 0
                    ORDER BY u.full_name COLLATE NOCASE ASC
                """, (group_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting group managers for broadcast: {e}")
            return []

    async def get_group_students_for_broadcast(self, group_id: int, status: str = 'approved') -> List[Dict[str, Any]]:
        """Get all students in a specific group for broadcast messaging"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT DISTINCT u.user_id, u.full_name, u.username, u.first_name, u.last_name,
                           s.class_id, c.class_name, s.course, s.school_session, s.gender
                    FROM users u
                    JOIN students s ON u.user_id = s.user_id
                    JOIN classes c ON s.class_id = c.class_id
                    WHERE s.group_id = ? AND s.status = ? AND u.is_blocked = 0 AND c.is_active = 1
                    ORDER BY u.full_name COLLATE NOCASE ASC
                """, (group_id, status)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting group students for broadcast: {e}")
            return []

    async def get_class_students_for_broadcast(self, class_id: int, status: str = 'approved') -> List[Dict[str, Any]]:
        """Get all students in a specific class for manager broadcast"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT u.user_id, u.full_name, u.username, u.first_name, u.last_name,
                           s.course, s.school_session, s.gender, c.class_name
                    FROM users u
                    JOIN students s ON u.user_id = s.user_id
                    JOIN classes c ON s.class_id = c.class_id
                    WHERE s.class_id = ? AND s.status = ? AND u.is_blocked = 0
                    ORDER BY u.full_name COLLATE NOCASE ASC
                """, (class_id, status)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting class students for broadcast: {e}")
            return []

    async def get_manager_classes_for_broadcast(self, manager_id: int) -> List[Dict[str, Any]]:
        """Get all classes managed by a user for manager broadcast"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT c.class_id, c.class_name, c.group_id, g.group_title,
                           COUNT(DISTINCT s.user_id) as student_count
                    FROM classes c
                    JOIN groups g ON c.group_id = g.group_id
                    LEFT JOIN students s ON c.class_id = s.class_id AND s.status = 'approved'
                    WHERE c.manager_id = ? AND c.is_active = 1 AND g.is_active = 1
                    GROUP BY c.class_id, c.class_name, c.group_id, g.group_title
                    ORDER BY g.group_title, c.class_name
                """, (manager_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting manager classes for broadcast: {e}")
            return []

    async def get_all_users_for_admin_broadcast(self, user_type: str = 'all') -> List[Dict[str, Any]]:
        """Get all users for admin broadcast based on type"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if user_type == 'all':
                    query = """
                        SELECT DISTINCT user_id, full_name, username, first_name, last_name
                        FROM users 
                        WHERE is_blocked = 0
                        ORDER BY full_name COLLATE NOCASE ASC
                    """
                    params = ()
                    
                elif user_type == 'managers':
                    query = """
                        SELECT DISTINCT u.user_id, u.full_name, u.username, u.first_name, u.last_name
                        FROM users u
                        JOIN classes c ON u.user_id = c.manager_id
                        WHERE u.is_blocked = 0 AND c.is_active = 1
                        ORDER BY u.full_name COLLATE NOCASE ASC
                    """
                    params = ()
                    
                elif user_type == 'owners':
                    query = """
                        SELECT DISTINCT u.user_id, u.full_name, u.username, u.first_name, u.last_name
                        FROM users u
                        JOIN groups g ON u.user_id = g.owner_id
                        WHERE u.is_blocked = 0 AND g.is_active = 1
                        ORDER BY u.full_name COLLATE NOCASE ASC
                    """
                    params = ()
                    
                elif user_type == 'students':
                    query = """
                        SELECT DISTINCT u.user_id, u.full_name, u.username, u.first_name, u.last_name
                        FROM users u
                        JOIN students s ON u.user_id = s.user_id
                        WHERE u.is_blocked = 0 AND s.status = 'approved'
                        ORDER BY u.full_name COLLATE NOCASE ASC
                    """
                    params = ()
                    
                else:
                    return []
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting users for admin broadcast: {e}")
            return []

    async def verify_group_ownership(self, user_id: int, group_id: int) -> bool:
        """Verify if user is the owner of a specific group"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT 1 FROM groups 
                    WHERE group_id = ? AND owner_id = ? AND is_active = 1
                """, (group_id, user_id)) as cursor:
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            self.logger.error(f"❌ Error verifying group ownership: {e}")
            return False

    async def verify_class_management(self, user_id: int, class_id: int) -> bool:
        """Verify if user is the manager of a specific class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT 1 FROM classes 
                    WHERE class_id = ? AND manager_id = ? AND is_active = 1
                """, (class_id, user_id)) as cursor:
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            self.logger.error(f"❌ Error verifying class management: {e}")
            return False

    async def save_broadcast_message(self, sender_id: int, target_type: str, target_id: int = None, 
                                   message_text: str = None, message_type: str = 'text', 
                                   file_id: str = None) -> int:
        """Save broadcast message to database and return message_id"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    INSERT INTO messages (sender_id, target_type, target_id, message_text, message_type, file_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sender_id, target_type, target_id, message_text, message_type, file_id)) as cursor:
                    message_id = cursor.lastrowid
                    await db.commit()
                    return message_id
        except Exception as e:
            self.logger.error(f"❌ Error saving broadcast message: {e}")
            return None

    async def get_broadcast_stats(self, group_id: int = None) -> Dict[str, int]:
        """Get broadcast statistics for a group or globally"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                if group_id:
                    # Group-specific stats
                    # Managers count
                    async with db.execute("""
                        SELECT COUNT(DISTINCT c.manager_id) FROM classes c
                        WHERE c.group_id = ? AND c.is_active = 1 AND c.manager_id IS NOT NULL
                    """, (group_id,)) as cursor:
                        row = await cursor.fetchone()
                        stats['managers_count'] = row[0] if row else 0
                    
                    # Students count
                    async with db.execute("""
                        SELECT COUNT(DISTINCT s.user_id) FROM students s
                        JOIN classes c ON s.class_id = c.class_id
                        WHERE s.group_id = ? AND s.status = 'approved' AND c.is_active = 1
                    """, (group_id,)) as cursor:
                        row = await cursor.fetchone()
                        stats['students_count'] = row[0] if row else 0
                        
                    # Total group users
                    stats['total_group_users'] = stats['managers_count'] + stats['students_count']
                    
                else:
                    # Global stats for admin
                    # All users
                    async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0") as cursor:
                        row = await cursor.fetchone()
                        stats['all_users'] = row[0] if row else 0
                    
                    # All managers
                    async with db.execute("""
                        SELECT COUNT(DISTINCT c.manager_id) FROM classes c
                        WHERE c.is_active = 1 AND c.manager_id IS NOT NULL
                    """) as cursor:
                        row = await cursor.fetchone()
                        stats['all_managers'] = row[0] if row else 0
                    
                    # All owners
                    async with db.execute("""
                        SELECT COUNT(DISTINCT g.owner_id) FROM groups g
                        WHERE g.is_active = 1
                    """) as cursor:
                        row = await cursor.fetchone()
                        stats['all_owners'] = row[0] if row else 0
                    
                    # All students
                    async with db.execute("""
                        SELECT COUNT(DISTINCT s.user_id) FROM students s
                        WHERE s.status = 'approved'
                    """) as cursor:
                        row = await cursor.fetchone()
                        stats['all_students'] = row[0] if row else 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"❌ Error getting broadcast stats: {e}")
            return {}

    # Reminder scheduling methods
    async def schedule_exam_reminders(self, exam_id: int, duration_days: int) -> bool:
        """Schedule reminders for an exam"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                from datetime import datetime, timedelta
                
                # Get exam creation time
                async with db.execute("SELECT creation_date FROM exams WHERE exam_id = ?", (exam_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return False
                    
                    creation_date = datetime.fromisoformat(row[0])
                
                # Calculate proper timing based on duration
                if duration_days <= 0:
                    # For materials (duration_days=0), no reminders
                    return True
                
                # Use real days for scheduling
                # Schedule day 1 reminder (after 1 real day)
                day1_time = creation_date + timedelta(days=1)
                await db.execute("""
                    INSERT INTO reminder_schedules (exam_id, reminder_type, scheduled_time)
                    VALUES (?, 'day1', ?)
                """, (exam_id, day1_time.isoformat()))
                
                # Schedule end reminder (at 90% of actual exam duration)
                end_time = creation_date + timedelta(days=duration_days * 0.9)
                await db.execute("""
                    INSERT INTO reminder_schedules (exam_id, reminder_type, scheduled_time)
                    VALUES (?, 'end', ?)
                """, (exam_id, end_time.isoformat()))
                
                # Schedule random tease messages (30%, 60%, 80% of duration)
                import random
                tease_percentages = [0.3, 0.6, 0.8]
                
                for percentage in tease_percentages:
                    tease_time = creation_date + timedelta(days=duration_days * percentage)
                    await db.execute("""
                        INSERT INTO reminder_schedules (exam_id, reminder_type, scheduled_time)
                        VALUES (?, 'tease', ?)
                    """, (exam_id, tease_time.isoformat()))
                
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error scheduling exam reminders: {e}")
            return False
    
    async def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Get all pending reminders that should be sent now"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                from datetime import datetime
                
                current_time = datetime.now().isoformat()
                
                query = """
                    SELECT r.*, e.title, e.class_id, c.class_name, c.group_id
                    FROM reminder_schedules r
                    JOIN exams e ON r.exam_id = e.exam_id
                    JOIN classes c ON e.class_id = c.class_id
                    WHERE r.is_sent = 0 AND r.scheduled_time <= ?
                    ORDER BY r.scheduled_time ASC
                """
                
                async with db.execute(query, (current_time,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting pending reminders: {e}")
            return []
    
    async def mark_reminder_sent(self, schedule_id: int) -> bool:
        """Mark a reminder as sent"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE reminder_schedules SET is_sent = 1 WHERE schedule_id = ?",
                    (schedule_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error marking reminder as sent: {e}")
            return False
    
    async def get_students_without_submission(self, exam_id: int) -> List[Dict[str, Any]]:
        """Get students who haven't submitted an answer to this exam"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                query = """
                    SELECT st.*, u.username
                    FROM students st
                    JOIN users u ON st.user_id = u.user_id
                    JOIN exams e ON st.class_id = e.class_id
                    WHERE e.exam_id = ? AND st.status = 'approved'
                    AND st.user_id NOT IN (
                        SELECT DISTINCT s.student_user_id 
                        FROM submissions s 
                        WHERE s.exam_id = ?
                    )
                """
                
                async with db.execute(query, (exam_id, exam_id)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting students without submission: {e}")
            return []
    
    async def get_class_materials(self, class_id: int) -> List[Dict[str, Any]]:
        """Get important materials for a class (exams with duration_days=0)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                query = """
                    SELECT * FROM exams 
                    WHERE class_id = ? AND duration_days = 0 AND is_active = 1
                    ORDER BY creation_date DESC
                """
                
                async with db.execute(query, (class_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting class materials: {e}")
            return []
    
    async def get_exam_by_id(self, exam_id: int) -> Dict[str, Any]:
        """Get exam/material by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                async with db.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting exam by ID: {e}")
            return None
    
    async def delete_exam(self, exam_id: int) -> bool:
        """Delete exam/material by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE exams SET is_active = 0 WHERE exam_id = ?", (exam_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting exam: {e}")
            return False
    
    async def is_exam_assigned_teacher(self, exam_id: int, user_id: int) -> bool:
        """Check if user is the assigned teacher for an exam"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT assigned_teacher_id FROM exams WHERE exam_id = ?", 
                    (exam_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return row[0] == user_id
                    # If no teacher assigned, any manager can grade
                    return False
        except Exception as e:
            self.logger.error(f"❌ Error checking exam teacher: {e}")
            return False
    
    async def get_teacher_exams(self, teacher_id: int) -> list:
        """Get all exams assigned to a teacher"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM exams 
                    WHERE assigned_teacher_id = ? 
                    ORDER BY creation_date DESC
                """, (teacher_id,))
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting teacher exams: {e}")
            return []
    
    async def get_pending_submissions_count(self, exam_id: int) -> int:
        """Get count of pending (ungraded) submissions for an exam"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM submissions 
                    WHERE exam_id = ? AND score_numerator IS NULL
                """, (exam_id,))
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            self.logger.error(f"❌ Error getting pending submissions count: {e}")
            return 0
    
    async def get_submission(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """Get submission by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT s.*, u.full_name as student_name,
                           s.score_numerator as score,
                           s.answer_file_id as file_id,
                           s.answer_text as caption,
                           'text' as content_type
                    FROM submissions s
                    LEFT JOIN users u ON s.student_user_id = u.user_id
                    WHERE s.submission_id = ?
                """, (submission_id,))
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    result = dict(zip(columns, row))
                    # Determine content type based on file_id
                    if result.get('file_id'):
                        result['content_type'] = 'document'  # Can be refined later
                    return result
                return None
        except Exception as e:
            self.logger.error(f"❌ Error getting submission: {e}")
            return None
    
    async def grade_submission(self, submission_id: int, score: float, graded_by: int) -> bool:
        """Grade a submission"""
        try:
            # Get exam max_score
            async with aiosqlite.connect(self.db_path) as db:
                # First get the exam_id from submission
                cursor = await db.execute("""
                    SELECT exam_id FROM submissions WHERE submission_id = ?
                """, (submission_id,))
                row = await cursor.fetchone()
                if not row:
                    return False
                exam_id = row[0]
                
                # Get max_score from exam
                cursor = await db.execute("""
                    SELECT max_score FROM exams WHERE exam_id = ?
                """, (exam_id,))
                row = await cursor.fetchone()
                max_score = row[0] if row else 20
                
                # Update submission with score and status
                status = 'passed' if score >= (max_score * 0.5) else 'failed'
                await db.execute("""
                    UPDATE submissions 
                    SET score_numerator = ?, 
                        score_denominator = ?,
                        status = ?,
                        reviewed_by = ?, 
                        review_date = CURRENT_TIMESTAMP 
                    WHERE submission_id = ?
                """, (score, max_score, status, graded_by, submission_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error grading submission: {e}")
            return False
    
    # REGISTRATION LINK METHODS
    
    async def create_registration_link(self, created_by: int, class_id: int, course: str, 
                                      school_session: str, max_uses: int = None) -> Optional[Dict[str, Any]]:
        """Create a new registration link"""
        try:
            import secrets
            # Generate unique link code
            link_code = secrets.token_urlsafe(16)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO registration_links (link_code, created_by, class_id, course, school_session, max_uses)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (link_code, created_by, class_id, course, school_session, max_uses))
                await db.commit()
                link_id = cursor.lastrowid
                
                # Get the full link info
                return await self.get_registration_link_by_id(link_id)
        except Exception as e:
            self.logger.error(f"❌ Error creating registration link: {e}")
            return None
    
    async def get_registration_link_by_code(self, link_code: str) -> Optional[Dict[str, Any]]:
        """Get registration link by code"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT rl.*, c.class_name, c.group_id, g.group_title
                    FROM registration_links rl
                    JOIN classes c ON rl.class_id = c.class_id
                    JOIN groups g ON c.group_id = g.group_id
                    WHERE rl.link_code = ? AND rl.is_active = 1
                """, (link_code,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting registration link: {e}")
            return None
    
    async def get_registration_link_by_id(self, link_id: int) -> Optional[Dict[str, Any]]:
        """Get registration link by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT rl.*, c.class_name, c.group_id, g.group_title
                    FROM registration_links rl
                    JOIN classes c ON rl.class_id = c.class_id
                    JOIN groups g ON c.group_id = g.group_id
                    WHERE rl.link_id = ?
                """, (link_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting registration link: {e}")
            return None
    
    async def get_user_registration_links(self, user_id: int, class_id: int = None) -> List[Dict[str, Any]]:
        """Get all registration links created by a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if class_id:
                    query = """
                        SELECT rl.*, c.class_name, c.group_id, g.group_title
                        FROM registration_links rl
                        JOIN classes c ON rl.class_id = c.class_id
                        JOIN groups g ON c.group_id = g.group_id
                        WHERE rl.created_by = ? AND rl.class_id = ?
                        ORDER BY rl.created_date DESC
                    """
                    params = (user_id, class_id)
                else:
                    query = """
                        SELECT rl.*, c.class_name, c.group_id, g.group_title
                        FROM registration_links rl
                        JOIN classes c ON rl.class_id = c.class_id
                        JOIN groups g ON c.group_id = g.group_id
                        WHERE rl.created_by = ?
                        ORDER BY rl.created_date DESC
                    """
                    params = (user_id,)
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting user registration links: {e}")
            return []
    
    async def increment_link_usage(self, link_id: int) -> bool:
        """Increment usage count for a registration link"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE registration_links 
                    SET usage_count = usage_count + 1
                    WHERE link_id = ?
                """, (link_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error incrementing link usage: {e}")
            return False
    
    async def track_link_registration(self, link_id: int, user_id: int, student_id: int) -> bool:
        """Track a registration made through a link"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO link_registrations (link_id, user_id, student_id)
                    VALUES (?, ?, ?)
                """, (link_id, user_id, student_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error tracking link registration: {e}")
            return False
    
    async def get_link_registrations(self, link_id: int) -> List[Dict[str, Any]]:
        """Get all registrations made through a specific link"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT lr.*, u.full_name, u.username, s.full_name as student_name, 
                           s.status, s.registration_date
                    FROM link_registrations lr
                    JOIN users u ON lr.user_id = u.user_id
                    JOIN students s ON lr.student_id = s.id
                    WHERE lr.link_id = ?
                    ORDER BY lr.registration_date DESC
                """, (link_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting link registrations: {e}")
            return []
    
    async def deactivate_registration_link(self, link_id: int) -> bool:
        """Deactivate a registration link"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE registration_links 
                    SET is_active = 0
                    WHERE link_id = ?
                """, (link_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deactivating link: {e}")
            return False
    
    async def delete_registration_link(self, link_id: int) -> bool:
        """Delete a registration link completely"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Delete link registrations first
                await db.execute("DELETE FROM link_registrations WHERE link_id = ?", (link_id,))
                # Delete the link
                await db.execute("DELETE FROM registration_links WHERE link_id = ?", (link_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting link: {e}")
            return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiosqlite
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any


class DatabaseManager:
    """Database manager - simplified version for classes/subjects/files system"""
    
    def __init__(self, db_path: str = "school_bot.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
    
    async def init_database(self):
        """Initialize database with required tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                await db.commit()
                self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all required tables"""
        
        # Users table
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
        
        # Classes table (مراحل/شعب)
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
        
        # Subjects table (مواد)
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
        
        # Files table
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
        
        # Logs table
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
        
        # Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_classes_manager ON classes(manager_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subjects_class ON subjects(class_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_files_subject ON files(subject_id)")
    
    async def get_connection(self):
        """Get database connection"""
        return await aiosqlite.connect(self.db_path)
    
    # ========== USER METHODS ==========
    
    async def add_user(self, user_id: int, full_name: str, username: str = None, 
                      first_name: str = None, last_name: str = None) -> bool:
        """Add or update user"""
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
    
    async def is_superadmin(self, user_id: int) -> bool:
        """Check if user is superadmin"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT is_superadmin FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return bool(row[0]) if row else False
        except Exception as e:
            self.logger.error(f"❌ Error checking superadmin status: {e}")
            return False
    
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
    
    # ========== CLASS METHODS ==========
    
    async def add_class(self, class_name: str, manager_id: int = None) -> Optional[int]:
        """Add new class (مرحلة)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO classes (class_name, manager_id)
                    VALUES (?, ?)
                """, (class_name, manager_id))
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
    
    async def get_all_classes(self) -> List[Dict[str, Any]]:
        """Get all active classes"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM classes WHERE is_active = 1 ORDER BY class_name", ()) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting all classes: {e}")
            return []
    
    async def set_class_manager(self, class_id: int, manager_id: int) -> bool:
        """Set manager for a class"""
        try:
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
                    return row and row[0] == user_id
        except Exception as e:
            self.logger.error(f"❌ Error checking class manager: {e}")
            return False
    
    async def get_user_managed_classes(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all classes managed by user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM classes WHERE manager_id = ? AND is_active = 1 ORDER BY class_name",
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting managed classes: {e}")
            return []
    
    async def delete_class(self, class_id: int) -> bool:
        """Delete class and all related data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Delete files first
                await db.execute("DELETE FROM files WHERE subject_id IN (SELECT subject_id FROM subjects WHERE class_id = ?)", (class_id,))
                # Delete subjects
                await db.execute("DELETE FROM subjects WHERE class_id = ?", (class_id,))
                # Delete class
                await db.execute("DELETE FROM classes WHERE class_id = ?", (class_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting class: {e}")
            return False
    
    # ========== SUBJECT METHODS ==========
    
    async def add_subject(self, class_id: int, subject_name: str) -> Optional[int]:
        """Add subject (مادة) to class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO subjects (class_id, subject_name)
                    VALUES (?, ?)
                """, (class_id, subject_name))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error adding subject: {e}")
            return None
    
    async def get_subject(self, subject_id: int) -> Optional[Dict[str, Any]]:
        """Get subject by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM subjects WHERE subject_id = ?", (subject_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting subject {subject_id}: {e}")
            return None
    
    async def get_class_subjects(self, class_id: int) -> List[Dict[str, Any]]:
        """Get all subjects for a class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM subjects WHERE class_id = ? ORDER BY subject_name",
                    (class_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting class subjects: {e}")
            return []
    
    async def delete_subject(self, subject_id: int) -> bool:
        """Delete subject and all its files"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Delete files first
                await db.execute("DELETE FROM files WHERE subject_id = ?", (subject_id,))
                # Delete subject
                await db.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting subject: {e}")
            return False
    
    # ========== FILE METHODS ==========
    
    async def add_file(self, subject_id: int, telegram_file_id: str, file_name: str, uploaded_by: int) -> Optional[int]:
        """Add file to subject"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO files (subject_id, telegram_file_id, file_name, uploaded_by)
                    VALUES (?, ?, ?, ?)
                """, (subject_id, telegram_file_id, file_name, uploaded_by))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error adding file: {e}")
            return None
    
    async def get_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Get file by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM files WHERE file_id = ?", (file_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting file {file_id}: {e}")
            return None
    
    async def get_subject_files(self, subject_id: int) -> List[Dict[str, Any]]:
        """Get all files for a subject"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM files WHERE subject_id = ? ORDER BY upload_date DESC",
                    (subject_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting subject files: {e}")
            return []
    
    async def delete_file(self, file_id: int) -> bool:
        """Delete file"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting file: {e}")
            return False
    
    # ========== LOG METHODS ==========
    
    async def add_log(self, user_id: int, action: str, details: str = None) -> bool:
        """Add log entry"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO logs (user_id, action, details)
                    VALUES (?, ?, ?)
                """, (user_id, action, details))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error adding log: {e}")
            return False


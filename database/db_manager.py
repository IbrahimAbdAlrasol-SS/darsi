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
                # Check and update old schema if needed
                await self._migrate_old_schema(db)
                await self._create_tables(db)
                await self._migrate_files_table(db)
                await self._migrate_subjects_table(db)
                await self._migrate_users_table(db)
                await self._migrate_error_logs_table(db)
                await self._migrate_bot_settings_table(db)
                await self._migrate_force_join_table(db)
                await db.commit()
                self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def _migrate_force_join_table(self, db: aiosqlite.Connection):
        """Ensure force_join_channels table exists"""
        try:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS force_join_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    channel_username TEXT,
                    channel_title TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception as e:
            self.logger.warning(f"Force join table migration warning: {e}")

    async def _migrate_bot_settings_table(self, db: aiosqlite.Connection):
        """Ensure bot_settings table exists"""
        try:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception as e:
            self.logger.warning(f"Bot settings table migration warning: {e}")

    async def _migrate_users_table(self, db: aiosqlite.Connection):
        """Migrate users table to add active_course column"""
        try:
            # Check if users table exists
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'") as cursor:
                table_exists = await cursor.fetchone()
            
            if table_exists:
                # Check if active_course column exists
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    if 'active_course' not in column_names:
                        await db.execute("ALTER TABLE users ADD COLUMN active_course INTEGER DEFAULT 1")
                        self.logger.info("✅ Added active_course column to users table")
        except Exception as e:
            self.logger.warning(f"Migration warning (may be normal): {e}")

    async def _migrate_error_logs_table(self, db: aiosqlite.Connection):
        """Ensure error_logs table exists"""
        try:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    error_message TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception as e:
            self.logger.warning(f"Error logs table migration warning: {e}")

    async def _migrate_subjects_table(self, db: aiosqlite.Connection):
        """Migrate subjects table to add course column"""
        try:
            # Check if subjects table exists
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subjects'") as cursor:
                table_exists = await cursor.fetchone()
            
            if table_exists:
                # Check if course column exists
                async with db.execute("PRAGMA table_info(subjects)") as cursor:
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    if 'course' not in column_names:
                        await db.execute("ALTER TABLE subjects ADD COLUMN course INTEGER DEFAULT 1")
                        self.logger.info("✅ Added course column to subjects table")
        except Exception as e:
            self.logger.warning(f"Migration warning (may be normal): {e}")
    
    async def _migrate_old_schema(self, db: aiosqlite.Connection):
        """Migrate old database schema to new simplified schema"""
        try:
            # Check if classes table exists
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='classes'") as cursor:
                table_exists = await cursor.fetchone()
            
            if not table_exists:
                # Table doesn't exist yet, will be created by _create_tables
                return
            
            # Check if old classes table has group_id column
            async with db.execute("PRAGMA table_info(classes)") as cursor:
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'group_id' in column_names:
                    self.logger.info("Migrating old classes table schema...")
                    
                    # Create new classes table with temp name
                    await db.execute("""
                        CREATE TABLE classes_new (
                            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            class_name TEXT NOT NULL UNIQUE,
                            manager_id INTEGER,
                            is_active INTEGER DEFAULT 1,
                            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (manager_id) REFERENCES users (user_id)
                        )
                    """)
                    
                    # Copy data from old table (without group_id)
                    try:
                        await db.execute("""
                            INSERT INTO classes_new (class_id, class_name, manager_id, is_active, created_date)
                            SELECT class_id, class_name, manager_id, is_active, created_date
                            FROM classes
                        """)
                    except Exception:
                        pass  # Table might be empty
                    
                    # Drop old table
                    await db.execute("DROP TABLE classes")
                    
                    # Rename new table
                    await db.execute("ALTER TABLE classes_new RENAME TO classes")
                    
                    await db.commit()
                    self.logger.info("Classes table migrated successfully")
            
            # Check and migrate exams table if it exists with old schema
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exams'") as cursor:
                exams_exists = await cursor.fetchone()
            
            if exams_exists:
                # Check if exams table has exam_type column
                async with db.execute("PRAGMA table_info(exams)") as cursor:
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    if 'exam_type' not in column_names:
                        self.logger.info("Old exams table found without exam_type, dropping...")
                        await db.execute("DROP TABLE exams")
                        await db.commit()
                        self.logger.info("Old exams table dropped, will be recreated")
                    
        except Exception as e:
            self.logger.warning(f"Migration warning (may be normal for new database): {e}")
            # Continue anyway, table creation will handle it
    
    async def _migrate_files_table(self, db: aiosqlite.Connection):
        """Migrate files table to add channel_message_id and file_type columns"""
        try:
            # Check if files table exists
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'") as cursor:
                table_exists = await cursor.fetchone()
            
            if table_exists:
                # Get existing columns
                async with db.execute("PRAGMA table_info(files)") as cursor:
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    # Add channel_message_id if missing
                    if 'channel_message_id' not in column_names:
                        await db.execute("ALTER TABLE files ADD COLUMN channel_message_id INTEGER")
                        self.logger.info("✅ Added channel_message_id column to files table")
                        
                    # Add file_type if missing
                    if 'file_type' not in column_names:
                        await db.execute("ALTER TABLE files ADD COLUMN file_type TEXT DEFAULT 'theory'")
                        self.logger.info("✅ Added file_type column to files table")
        except Exception as e:
            self.logger.warning(f"Migration warning (may be normal): {e}")
    
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
                active_course INTEGER DEFAULT 1,
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
                course INTEGER DEFAULT 1,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes (class_id),
                UNIQUE(class_id, subject_name)
            )
        """)
        
        # Class settings (per-class storage channel)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS class_settings (
                class_id INTEGER PRIMARY KEY,
                storage_channel_username TEXT,
                storage_channel_id INTEGER,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes (class_id)
            )
        """)
        
        # Files table (ملازم)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                telegram_file_id TEXT,
                channel_message_id INTEGER,
                file_name TEXT NOT NULL,
                uploaded_by INTEGER NOT NULL,
                upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects (subject_id),
                FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
            )
        """)
        
        # Exams table (امتحانات)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                exam_type TEXT NOT NULL CHECK (exam_type IN ('مد', 'كوز', 'نصف سنة', 'أخير سنة')),
                title TEXT NOT NULL,
                telegram_file_id TEXT,
                content_type TEXT,
                content_text TEXT,
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
        
        # Favorites table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
            )
        """)
        
        # Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_classes_manager ON classes(manager_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subjects_class ON subjects(class_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_files_subject ON files(subject_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_exams_subject ON exams(subject_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_class_settings_class ON class_settings(class_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_favorites_subject ON favorites(subject_id)")
        
        # Schema Migrations
        try:
            await db.execute("SELECT active_course FROM users LIMIT 1")
        except Exception:
            self.logger.info("Migrating schema: Adding active_course to users table")
            await db.execute("ALTER TABLE users ADD COLUMN active_course INTEGER DEFAULT 1")
    
    async def get_connection(self):
        """Get database connection"""
        return await aiosqlite.connect(self.db_path)
    
    # ========== FORCE JOIN ==========
    
    async def add_force_join_channel(self, channel_id: int, channel_username: str, channel_title: str):
        """Add a force join channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO force_join_channels (channel_id, channel_username, channel_title) VALUES (?, ?, ?)",
                    (channel_id, channel_username, channel_title)
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error adding force join channel: {e}")
            return False

    async def get_force_join_channels(self) -> List[Dict[str, Any]]:
        """Get all force join channels"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM force_join_channels ORDER BY created_at DESC") as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting force join channels: {e}")
            return []

    async def delete_force_join_channel(self, id: int) -> bool:
        """Delete a force join channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM force_join_channels WHERE id = ?", (id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error deleting force join channel: {e}")
            return False

    # ========== ANALYTICS & MONITORING ==========
    
    async def log_error(self, source: str, error_message: str, details: str = None):
        """Log an error"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO error_logs (source, error_message, details)
                    VALUES (?, ?, ?)
                """, (source, str(error_message), str(details) if details else None))
                await db.commit()
        except Exception as e:
            # Fallback logging if DB fails
            self.logger.error(f"Failed to log error to DB: {e}")

    async def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM error_logs ORDER BY timestamp DESC LIMIT ?", 
                    (limit,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting recent errors: {e}")
            return []

    async def get_analytics(self) -> Dict[str, Any]:
        """Get overall bot analytics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Total users
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    total_users = (await cursor.fetchone())[0]
                
                # New users
                async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= date('now', 'start of day')") as cursor:
                    new_today = (await cursor.fetchone())[0]
                    
                async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= date('now', '-7 days')") as cursor:
                    new_week = (await cursor.fetchone())[0]
                    
                async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= date('now', 'start of month')") as cursor:
                    new_month = (await cursor.fetchone())[0]
                
                # Active users
                async with db.execute("SELECT COUNT(*) FROM users WHERE last_activity >= date('now', 'start of day')") as cursor:
                    active_today = (await cursor.fetchone())[0]
                    
                async with db.execute("SELECT COUNT(*) FROM users WHERE last_activity >= date('now', '-7 days')") as cursor:
                    active_week = (await cursor.fetchone())[0]
                    
                async with db.execute("SELECT COUNT(*) FROM users WHERE last_activity >= date('now', 'start of month')") as cursor:
                    active_month = (await cursor.fetchone())[0]
                    
                return {
                    "total_users": total_users,
                    "new_users": {"today": new_today, "week": new_week, "month": new_month},
                    "active_users": {"today": active_today, "week": active_week, "month": active_month}
                }
        except Exception as e:
            self.logger.error(f"Error getting analytics: {e}")
            return {
                "total_users": 0, 
                "new_users": {"today": 0, "week": 0, "month": 0}, 
                "active_users": {"today": 0, "week": 0, "month": 0}
            }

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for admin dashboard (flat structure)"""
        try:
            analytics = await self.get_analytics()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Get total classes
                async with db.execute("SELECT COUNT(*) FROM classes") as cursor:
                    total_classes = (await cursor.fetchone())[0]
                    
                # Get total subjects
                async with db.execute("SELECT COUNT(*) FROM subjects") as cursor:
                    total_subjects = (await cursor.fetchone())[0]
                    
                # Get total files
                async with db.execute("SELECT COUNT(*) FROM files") as cursor:
                    total_files = (await cursor.fetchone())[0]
            
            return {
                "total_users": analytics["total_users"],
                "active_today": analytics["active_users"]["today"],
                "active_week": analytics["active_users"]["week"],
                "active_month": analytics["active_users"]["month"],
                "new_today": analytics["new_users"]["today"],
                "total_classes": total_classes,
                "total_subjects": total_subjects,
                "total_files": total_files
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}

    # ========== BROADCAST SUPPORT ==========

    async def get_all_users_for_admin_broadcast(self, filter_type: str = 'all') -> List[Dict[str, Any]]:
        """Get users for broadcast based on filter"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                query = "SELECT user_id, full_name, username FROM users WHERE is_blocked = 0"
                
                if filter_type == 'managers':
                    # Get users who manage at least one class
                    query = """
                        SELECT DISTINCT u.user_id, u.full_name, u.username 
                        FROM users u 
                        JOIN classes c ON u.user_id = c.manager_id 
                        WHERE u.is_blocked = 0
                    """
                elif filter_type == 'students':
                    # All users are effectively students
                    pass
                elif filter_type == 'owners':
                    query += " AND is_superadmin = 1"
                
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting broadcast users ({filter_type}): {e}")
            return []

    async def save_broadcast_message(self, sender_id: int, target_type: str, target_id: Optional[int], 
                                   message_text: Optional[str], message_type: str, file_id: Optional[str]):
        """Save broadcast message record"""
        try:
            # We don't have a specific table for broadcast history in the schema above,
            # so we'll just log it to the logs table for now.
            # If a detailed history is needed, we should create a broadcast_history table.
            
            details = f"Type: {message_type}, Target: {target_type}"
            if target_id:
                details += f", TargetID: {target_id}"
            if message_text:
                details += f", Text: {message_text[:50]}..."
                
            await self.add_log(sender_id, "broadcast_sent", details)
            
        except Exception as e:
            self.logger.error(f"Error saving broadcast message: {e}")

    async def add_log(self, user_id: int, action: str, details: str = None):
        """Add entry to logs table"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO logs (user_id, action, details)
                    VALUES (?, ?, ?)
                """, (user_id, action, details))
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error adding log: {e}")

    # ========== SETTINGS ==========


    async def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for broadcast"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT user_id FROM users") as cursor:
                    rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting all user IDs: {e}")
            return []
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting user {user_id}: {e}")
            return None

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
                    result = await cursor.fetchone()
                    return bool(result[0]) if result else False
        except Exception as e:
            self.logger.error(f"Error checking superadmin {user_id}: {e}")
            return False

    # ========== SETTINGS METHODS ==========
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get global setting value"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else default
        except Exception as e:
            self.logger.error(f"Error getting setting {key}: {e}")
            return default
            
    async def set_setting(self, key: str, value: str) -> bool:
        """Set global setting value"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, str(value)))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error setting setting {key}: {e}")
            return False

    # ========== ANALYTICS & MONITORING ==========
    
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

    async def get_user_active_course(self, user_id: int) -> int:
        """Get user's active course context (1 or 2)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT active_course FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row and row[0] else 1
        except Exception as e:
            self.logger.error(f"❌ Error getting active course for user {user_id}: {e}")
            return 1

    async def set_user_active_course(self, user_id: int, course: int) -> bool:
        """Set user's active course context"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "UPDATE users SET active_course = ? WHERE user_id = ?",
                    (course, user_id)
                )
                if cursor.rowcount == 0:
                    # User might not exist, create basic record
                    await db.execute(
                        "INSERT INTO users (user_id, full_name, active_course) VALUES (?, ?, ?)",
                        (user_id, "Unknown Admin", course)
                    )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error setting active course for user {user_id}: {e}")
            return False
    
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
    
    async def add_subject(self, class_id: int, subject_name: str, course: int = 1) -> Optional[int]:
        """Add subject (مادة) to class"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO subjects (class_id, subject_name, course)
                    VALUES (?, ?, ?)
                """, (class_id, subject_name, course))
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
    
    async def get_class_subjects(self, class_id: int, course: int = None) -> List[Dict[str, Any]]:
        """Get all subjects for a class, optionally filtered by course"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                query = "SELECT * FROM subjects WHERE class_id = ?"
                params = [class_id]
                
                if course:
                    query += " AND course = ?"
                    params.append(course)
                    
                query += " ORDER BY subject_name"
                
                async with db.execute(query, tuple(params)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting class subjects: {e}")
            return []
    
    async def update_subject_course(self, subject_id: int, new_course: int) -> bool:
        """Update subject course"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE subjects SET course = ? WHERE subject_id = ?",
                    (new_course, subject_id)
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error updating subject course: {e}")
            return False
    
    async def delete_subject(self, subject_id: int) -> bool:
        """Delete subject and all its files and exams"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Delete files first
                await db.execute("DELETE FROM files WHERE subject_id = ?", (subject_id,))
                # Delete exams
                await db.execute("DELETE FROM exams WHERE subject_id = ?", (subject_id,))
                # Delete subject
                await db.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting subject: {e}")
            return False
    
    # ========== CLASS SETTINGS ==========
    
    async def get_class_settings(self, class_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM class_settings WHERE class_id = ?", (class_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting class settings: {e}")
            return None
    
    async def set_class_storage_channel(self, class_id: int, username: str = None, channel_id: int = None) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO class_settings (class_id, storage_channel_username, storage_channel_id, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(class_id) DO UPDATE SET
                        storage_channel_username=excluded.storage_channel_username,
                        storage_channel_id=excluded.storage_channel_id,
                        updated_at=CURRENT_TIMESTAMP
                """, (class_id, username, channel_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error setting class storage channel: {e}")
            return False
    
    async def clear_class_storage_channel(self, class_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM class_settings WHERE class_id = ?", (class_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error clearing class storage channel: {e}")
            return False
    
    # ========== FILE METHODS ==========
    
    async def add_file(self, subject_id: int, file_name: str, uploaded_by: int, 
                      channel_message_id: int = None, telegram_file_id: str = None, file_type: str = 'theory') -> Optional[int]:
        """Add file to subject
        Either channel_message_id (new method) or telegram_file_id (old method) should be provided
        file_type: 'theory' (default) or 'practical'
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO files (subject_id, telegram_file_id, channel_message_id, file_name, uploaded_by, file_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (subject_id, telegram_file_id, channel_message_id, file_name, uploaded_by, file_type))
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
    
    async def get_subject_files(self, subject_id: int, file_type: str = None) -> List[Dict[str, Any]]:
        """Get all files for a subject, optionally filtered by type"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                if file_type:
                    query = "SELECT * FROM files WHERE subject_id = ? AND file_type = ? ORDER BY upload_date DESC"
                    params = (subject_id, file_type)
                else:
                    query = "SELECT * FROM files WHERE subject_id = ? ORDER BY upload_date DESC"
                    params = (subject_id,)
                    
                async with db.execute(query, params) as cursor:
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
    
    # ========== EXAM METHODS ==========
    
    async def add_exam(self, subject_id: int, exam_type: str, title: str, 
                      uploaded_by: int, telegram_file_id: str = None, 
                      content_type: str = None, content_text: str = None) -> Optional[int]:
        """Add exam to subject"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO exams (subject_id, exam_type, title, telegram_file_id, content_type, content_text, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (subject_id, exam_type, title, telegram_file_id, content_type, content_text, uploaded_by))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"❌ Error adding exam: {e}")
            return None
    
    async def get_exam(self, exam_id: int) -> Optional[Dict[str, Any]]:
        """Get exam by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting exam {exam_id}: {e}")
            return None
    
    async def get_subject_exams(self, subject_id: int) -> List[Dict[str, Any]]:
        """Get all exams for a subject"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM exams WHERE subject_id = ? ORDER BY exam_type, upload_date DESC",
                    (subject_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting subject exams: {e}")
            return []
    
    async def delete_exam(self, exam_id: int) -> bool:
        """Delete exam"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM exams WHERE exam_id = ?", (exam_id,))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error deleting exam: {e}")
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
    
    # ========== FAVORITES METHODS ==========
    
    async def add_favorite(self, user_id: int, subject_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO favorites (user_id, subject_id)
                    VALUES (?, ?)
                """, (user_id, subject_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error adding favorite: {e}")
            return False
    
    async def remove_favorite(self, user_id: int, subject_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM favorites WHERE user_id = ? AND subject_id = ?", (user_id, subject_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Error removing favorite: {e}")
            return False
    
    async def is_favorite(self, user_id: int, subject_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND subject_id = ?", (user_id, subject_id)) as cursor:
                    row = await cursor.fetchone()
                    return bool(row)
        except Exception as e:
            self.logger.error(f"❌ Error checking favorite: {e}")
            return False
    
    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT s.subject_id, s.subject_name, s.class_id, s.course
                    FROM favorites f
                    JOIN subjects s ON s.subject_id = f.subject_id
                    WHERE f.user_id = ?
                    ORDER BY s.subject_name
                """, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Error getting user favorites: {e}")
            return []

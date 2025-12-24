#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Automatic Backup System
"""

import os
import shutil
import gzip
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from utils.logger import get_logger

logger = get_logger(__name__)


class BackupManager:
    """نسْخَھِ احتياطيه تلقائيه"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # تنظیمات پشتیبان‌گیری
        self.backup_settings = config.get("settings", {}).get("backup", {})
        self.auto_backup = self.backup_settings.get("auto_backup", True)
        self.interval_hours = self.backup_settings.get("interval_hours", 24)
        self.keep_days = self.backup_settings.get("keep_days", 30)
        
        self.running = False
    
    async def start_auto_backup(self):
        """بدء النسخه الاحتياطيه"""
        if not self.auto_backup:
            logger.info("Auto backup is disabled")
            return
        
        self.running = True
        logger.info(f"🔄 Auto backup started (interval: {self.interval_hours}h)")
        
        while self.running:
            try:
                await self.create_backup()
                await self.cleanup_old_backups()
                
                await asyncio.sleep(self.interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in auto backup: {e}")
                await asyncio.sleep(300)  # 5 minutes wait on error
    
    def stop_auto_backup(self):
        """ايقاف النسخه الاحتياطيه"""
        self.running = False
        logger.info("⏹️ Auto backup stopped")
    
    async def create_backup(self, backup_type: str = "auto") -> str:
        """نسْخَھِ احتياطيه جديده"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"school_bot_backup_{backup_type}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            logger.info(f"📦 Creating backup: {backup_name}")
            
            await self._backup_database(backup_path)
            
            await self._backup_config(backup_path)
            
            await self._backup_logs(backup_path)
            
            await self._create_backup_info(backup_path, backup_type)
            
            compressed_path = await self._compress_backup(backup_path)
            
            shutil.rmtree(backup_path)
            
            logger.info(f"✅ Backup created: {compressed_path.name}")
            return str(compressed_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            raise
    
    async def _backup_database(self, backup_path: Path):
        """نسْخَھِ احتياطيه من الخزن"""
        try:
            db_path = Path(self.config.get("database_path", "school_bot.db"))
            if db_path.exists():
                target_path = backup_path / "database"
                target_path.mkdir(exist_ok=True)
                
                shutil.copy2(db_path, target_path / db_path.name)
                logger.debug(f"Database backed up: {db_path.name}")
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
    
    async def _backup_config(self, backup_path: Path):
        """نسْخَھِ احتياطيه من المعلومات الكونفينك"""
        try:
            config_files = ["config.json", "config.example.json"]
            target_path = backup_path / "config"
            target_path.mkdir(exist_ok=True)
            
            for config_file in config_files:
                config_path = Path(config_file)
                if config_path.exists():
                    shutil.copy2(config_path, target_path / config_file)
                    logger.debug(f"Config backed up: {config_file}")
        except Exception as e:
            logger.error(f"Error backing up config: {e}")
    
    async def _backup_logs(self, backup_path: Path):
        """نسْخَھِ من الاخطاء"""
        try:
            logs_dir = Path("logs")
            if logs_dir.exists():
                target_path = backup_path / "logs"
                target_path.mkdir(exist_ok=True)
                
                # فقط لاگ‌های 7 روز اخیر
                cutoff_date = datetime.now() - timedelta(days=7)
                
                for log_file in logs_dir.glob("*.log"):
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time > cutoff_date:
                        shutil.copy2(log_file, target_path / log_file.name)
                        logger.debug(f"Log backed up: {log_file.name}")
        except Exception as e:
            logger.error(f"Error backing up logs: {e}")
    
    async def _create_backup_info(self, backup_path: Path, backup_type: str):
        """نسْخَھِ احتياطيه من المعلومات"""
        try:
            info = {
                "backup_type": backup_type,
                "created_at": datetime.now().isoformat(),
                "bot_version": "1.0.0",
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                "files_included": {
                    "database": True,
                    "config": True,
                    "logs": True
                },
                "notes": f"Automatic backup created at {datetime.now()}"
            }
            
            info_path = backup_path / "backup_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error creating backup info: {e}")
    
    async def _compress_backup(self, backup_path: Path) -> Path:
        """ضغط النسخه الاحتياطيه"""
        try:
            compressed_path = backup_path.with_suffix('.tar.gz')
            
            import tarfile
            with tarfile.open(compressed_path, 'w:gz') as tar:
                tar.add(backup_path, arcname=backup_path.name)
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Error compressing backup: {e}")
            raise
    
    async def cleanup_old_backups(self):
        """مسح النسخ الاحتياطيه القديمه"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.keep_days)
            removed_count = 0
            
            for backup_file in self.backup_dir.glob("school_bot_backup_*.tar.gz"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old backup: {backup_file.name}")
            
            if removed_count > 0:
                logger.info(f"🗑️ Cleaned up {removed_count} old backups")
                
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    async def restore_backup(self, backup_path: str, restore_database: bool = True, 
                           restore_config: bool = False) -> bool:
        """استعادة النسخه الاحتياطيه"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            logger.info(f"🔄 Restoring from backup: {backup_file.name}")
            
            temp_dir = self.backup_dir / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                import tarfile
                with tarfile.open(backup_file, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                extracted_dirs = list(temp_dir.glob("school_bot_backup_*"))
                if not extracted_dirs:
                    logger.error("No backup data found in archive")
                    return False
                
                backup_data_dir = extracted_dirs[0]
                
                if restore_database:
                    await self._restore_database(backup_data_dir)
                
                # بازیابی کانفیگ
                if restore_config:
                    await self._restore_config(backup_data_dir)
                
                logger.info("✅ Backup restored successfully")
                return True
                
            finally:
                # پاک کردن پوشه موقت
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    
        except Exception as e:
            logger.error(f"❌ Error restoring backup: {e}")
            return False
    
    async def _restore_database(self, backup_data_dir: Path):
        """استعادة قاعدة البيانات"""
        try:
            db_backup_dir = backup_data_dir / "database"
            if db_backup_dir.exists():
                db_files = list(db_backup_dir.glob("*.db"))
                if db_files:
                    db_file = db_files[0]
                    target_path = Path(self.config.get("database_path", "school_bot.db"))
                    
                    # بکاپ از فایل فعلی
                    if target_path.exists():
                        backup_current = target_path.with_suffix(f".db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                        shutil.copy2(target_path, backup_current)
                        logger.info(f"Current database backed up to: {backup_current.name}")
                    
                    # بازیابی پایگاه داده
                    shutil.copy2(db_file, target_path)
                    logger.info("Database restored from backup")
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
    
    async def _restore_config(self, backup_data_dir: Path):
        """استعادة الكونفينك"""
        try:
            config_backup_dir = backup_data_dir / "config"
            if config_backup_dir.exists():
                config_files = list(config_backup_dir.glob("config*.json"))
                for config_file in config_files:
                    target_path = Path(config_file.name)
                    
                    # بکاپ از فایل فعلی
                    if target_path.exists():
                        backup_current = target_path.with_suffix(f".json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                        shutil.copy2(target_path, backup_current)
                    
                    # بازیابی کانفیگ
                    shutil.copy2(config_file, target_path)
                    logger.info(f"Config restored: {config_file.name}")
        except Exception as e:
            logger.error(f"Error restoring config: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """قائمة النسخ الاحتياطيه الموجوده"""
        try:
            backups = []
            
            for backup_file in sorted(self.backup_dir.glob("school_bot_backup_*.tar.gz"), reverse=True):
                file_stat = backup_file.stat()
                backup_info = {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / 1024 / 1024, 2),
                    "created_at": datetime.fromtimestamp(file_stat.st_mtime),
                    "age_days": (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
                }
                backups.append(backup_info)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """احصائيات النسخ الاحتياطيه"""
        try:
            backups = self.list_backups()
            total_size = sum(b["size"] for b in backups)
            
            return {
                "total_backups": len(backups),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "oldest_backup": backups[-1]["created_at"] if backups else None,
                "newest_backup": backups[0]["created_at"] if backups else None,
                "auto_backup_enabled": self.auto_backup,
                "backup_interval_hours": self.interval_hours,
                "keep_days": self.keep_days
            }
            
        except Exception as e:
            logger.error(f"Error getting backup stats: {e}")
            return {}


# CLI برای مدیریت پشتیبان‌ها
async def main():
    """توابع CLI"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="School Bot Backup Manager")
    parser.add_argument("action", choices=["create", "restore", "list", "cleanup", "stats"],
                       help="Action to perform")
    parser.add_argument("--backup-file", help="Backup file path for restore")
    parser.add_argument("--type", default="manual", help="Backup type")
    
    args = parser.parse_args()
    
    # بارگذاری کانفیگ
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    backup_manager = BackupManager(config)
    
    if args.action == "create":
        backup_path = await backup_manager.create_backup(args.type)
        print(f"Backup created: {backup_path}")
    
    elif args.action == "restore":
        if not args.backup_file:
            print("--backup-file required for restore")
            sys.exit(1)
        
        success = await backup_manager.restore_backup(args.backup_file)
        if success:
            print("Backup restored successfully")
        else:
            print("Backup restore failed")
    
    elif args.action == "list":
        backups = backup_manager.list_backups()
        if backups:
            print(f"{'Filename':<40} {'Size (MB)':<10} {'Created':<20} {'Age (days)':<10}")
            print("-" * 80)
            for backup in backups:
                print(f"{backup['filename']:<40} {backup['size_mb']:<10} "
                      f"{backup['created_at'].strftime('%Y-%m-%d %H:%M'):<20} {backup['age_days']:<10}")
        else:
            print("No backups found")
    
    elif args.action == "cleanup":
        await backup_manager.cleanup_old_backups()
        print("Old backups cleaned up")
    
    elif args.action == "stats":
        stats = backup_manager.get_backup_stats()
        print("Backup Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())

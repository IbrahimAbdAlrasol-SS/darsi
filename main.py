#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from database.db_manager import DatabaseManager
from handlers import setup_routers
from utils.logger import setup_logger
from middlewares.auth import AuthMiddleware
from middlewares.database import DatabaseMiddleware
from middlewares.force_join import ForceJoinMiddleware


async def main():
    """Main function to start the bot"""
    
    # Setup logging
    logger = setup_logger()
    logger.info("🚀 Starting School Management Bot...")
    
    try:
        # Load configuration
        config_path = Path("config.json")
        if not config_path.exists():
            logger.error("❌ config.json file not found!")
            sys.exit(1)
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        bot_token = config.get("bot_token")
        if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ Please set your bot token in config.json")
            sys.exit(1)
        
        # Initialize bot and dispatcher
        bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Initialize database
        db_manager = DatabaseManager(config.get("database_path", "school_bot.db"))
        await db_manager.init_database()
        
        # Setup middlewares
        dp.message.middleware(DatabaseMiddleware(db_manager))
        dp.callback_query.middleware(DatabaseMiddleware(db_manager))
        dp.message.middleware(AuthMiddleware(config))
        dp.callback_query.middleware(AuthMiddleware(config))
        
        # Setup ForceJoinMiddleware (after Auth to get user info, but before handlers)
        dp.message.middleware(ForceJoinMiddleware(config))
        dp.callback_query.middleware(ForceJoinMiddleware(config))
        
        # Add bot instance to dispatcher data for middlewares
        dp["bot"] = bot
        
        # Setup routers
        setup_routers(dp, config)
        
        # Add config to dispatcher for global access
        dp["config"] = config
        dp["db"] = db_manager
        
        logger.info("✅ Bot setup completed successfully!")
        
        # Start polling
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Critical error: {e}")

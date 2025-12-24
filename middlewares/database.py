#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.db_manager import DatabaseManager


class DatabaseMiddleware(BaseMiddleware):
    """Database middleware to inject database manager into handlers"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        # Inject database manager into handler data
        data["db"] = self.db_manager
        
        return await handler(event, data)

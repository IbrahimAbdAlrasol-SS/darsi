#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
import logging


class AuthMiddleware(BaseMiddleware):
    """Simplified authentication middleware"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        # Get user info from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if not user:
            return await handler(event, data)
        
        # Add user info to data
        data["user"] = user
        
        # Get database manager
        db = data.get("db")
        if not db:
            return await handler(event, data)
        
        try:
            # Add or update user in database
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if not full_name:
                full_name = user.username or f"User_{user.id}"
            
            await db.add_user(
                user_id=user.id,
                full_name=full_name,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Check superadmin status
            configured_superadmin = self.config.get("superadmin_id")
            if user.id == configured_superadmin:
                try:
                    await db.set_superadmin(user.id, True)
                except Exception:
                    pass
            
            is_superadmin = (user.id == configured_superadmin) or await db.is_superadmin(user.id)
            data["is_superadmin"] = is_superadmin
            
            # Check if user is class manager
            managed_classes = await db.get_user_managed_classes(user.id)
            data["is_class_manager"] = len(managed_classes) > 0
            data["managed_classes"] = managed_classes
            
        except Exception as e:
            self.logger.error(f"❌ Error in auth middleware: {e}")
        
        return await handler(event, data)

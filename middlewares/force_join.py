#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, InlineKeyboardMarkup, InlineKeyboardButton
import logging


class ForceJoinMiddleware(BaseMiddleware):
    """Force join channel middleware"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get force join settings from config (static fallback)
        self.config_channel_id = config.get("force_join", {}).get("channel_id")
        self.config_channel_username = config.get("force_join", {}).get("channel_username") or config.get("force_join_channel")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        # Get DB manager
        db = data.get("db")
        if not db:
            return await handler(event, data)

        # 1. Get channels from DB
        db_channels = await db.get_force_join_channels()
        
        # 2. Prepare active channels list
        active_channels = []
        if db_channels:
            for ch in db_channels:
                active_channels.append({
                    'id': ch['channel_id'],
                    'username': ch['channel_username'],
                    'title': ch['channel_title'] or "قناة"
                })
        else:
             # Fallback to old config if DB is empty
             config_id = self.config_channel_id
             config_username = self.config_channel_username
             if config_id or config_username:
                 active_channels.append({
                     'id': config_id,
                     'username': config_username,
                     'title': "قناة البوت"
                 })
        
        if not active_channels:
            return await handler(event, data)
        
        # Get user
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if not user:
            return await handler(event, data)
        
        # Skip for superadmins
        is_superadmin = data.get("is_superadmin", False)
        if is_superadmin:
            return await handler(event, data)
        
        # Enforce for ALL interactions
        bot = data.get("bot")
        if not bot:
            return await handler(event, data)
        
        missing_channels = []
        
        for channel in active_channels:
            try:
                # Prefer ID if available
                chat_id = channel['id'] if channel['id'] else channel['username']
                member = await bot.get_chat_member(chat_id, user.id)
                if member.status in ["left", "kicked"]:
                    missing_channels.append(channel)
            except Exception as e:
                self.logger.warning(f"Failed to check membership for {channel}: {e}")
                # To be safe, if we can't check, we assume they are not a member.
                missing_channels.append(channel)
                continue

        if not missing_channels:
            # User is subscribed to all channels, proceed with the original handler
            return await handler(event, data)
        else:
            # User is not subscribed, block them and send the force-join message.
            # We also want to answer the callback query if the event is a callback query.
            if isinstance(event, CallbackQuery):
                await event.answer()
            await self._send_force_join_message(event, user, bot, missing_channels)
            return
    
    async def _send_force_join_message(self, event, user, bot, channels):
        """Send force join message to user"""
        
        text = "🛑 **عذراً عزيزي**\n\n⚠️ يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
        
        keyboard_rows = []
        
        for ch in channels:
            title = ch['title']
            link = ""
            username = ch['username']
            
            if username and str(username).startswith("@"):
                 link = f"https://t.me/{username[1:]}"
            elif username and "t.me" in str(username):
                 link = str(username)
            
            if link:
                keyboard_rows.append([InlineKeyboardButton(text=f"📢 {title}", url=link)])
            else:
                text += f"• {title} (قناة خاصة - لا يمكن إنشاء رابط)\n"

        keyboard_rows.append([InlineKeyboardButton(text="✅ تم الاشتراك", callback_data="check_membership")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        # We try to answer the original message/callback with the force-join prompt.
        if isinstance(event, Message):
            try:
                await event.answer(text, reply_markup=keyboard)
            except Exception:
                pass
        elif isinstance(event, CallbackQuery):
            try:
                await event.message.answer(text, reply_markup=keyboard)
            except Exception:
                pass

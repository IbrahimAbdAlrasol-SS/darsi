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
        
        # Get force join settings from config
        self.force_join_enabled = config.get("force_join", {}).get("enabled", False)
        self.channel_id = config.get("force_join", {}).get("channel_id")
        self.channel_username = config.get("force_join", {}).get("channel_username", "")
        
        # Fallback to old config format
        if not self.channel_id and config.get("force_join_channel"):
            self.channel_username = config.get("force_join_channel")
            self.force_join_enabled = True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        # Skip if force join is disabled
        if not self.force_join_enabled or not (self.channel_id or self.channel_username):
            return await handler(event, data)
        
        # Get user and bot from event
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
        
        # Only check membership for specific bot interactions, not regular group chat messages
        should_check_membership = False
        
        if isinstance(event, Message):
            # Check for bot commands or private chat
            if event.chat.type == "private":
                should_check_membership = True
            elif event.text and (event.text.startswith('/') or event.text.startswith('@')):
                # Bot commands or mentions
                should_check_membership = True
        elif isinstance(event, CallbackQuery):
            # All callback queries should be checked
            should_check_membership = True
        
        if not should_check_membership:
            return await handler(event, data)
        
        # Get bot instance
        bot = data.get("bot")
        if not bot:
            return await handler(event, data)
        
        # Check if user is member of channel
        try:
            channel_to_check = self.channel_id or self.channel_username
            member = await bot.get_chat_member(channel_to_check, user.id)
            
            # If user is not a member or left the channel
            if member.status in ["left", "kicked"]:
                await self._send_force_join_message(event, user, bot)
                return  # Stop processing
                
        except Exception as e:
            # Handle specific Telegram errors
            error_str = str(e).lower()
            if "member list is inaccessible" in error_str or "bad request" in error_str:
                # Channel privacy settings prevent checking membership
                # In this case, we'll gracefully continue without blocking
                self.logger.warning(f"Cannot check membership for channel {channel_to_check}: {e}")
                return await handler(event, data)
            else:
                self.logger.warning(f"Failed to check channel membership for user {user.id}: {e}")
                # On other errors, continue without blocking (graceful degradation)
                return await handler(event, data)
        
        # User is member, continue processing
        return await handler(event, data)
    
    async def _send_force_join_message(self, event, user, bot):
        """Send force join message to user"""
        
        # Create join button
        channel_link = self.channel_username if self.channel_username.startswith("@") else f"@{self.channel_username}"
        if self.channel_id and self.channel_id.startswith("-100"):
            # Private channel, use t.me link
            channel_link = f"https://t.me/c/{self.channel_id[4:]}"
        elif self.channel_username:
            channel_link = f"https://t.me/{self.channel_username.lstrip('@')}"
        else:
            channel_link = "https://t.me/joinchat/invite_link"  # Fallback
        
        # Force join message
        text = f"""
⌔︙عليك الاشتراك في قناة البوت اولاً !

🔗 **القناة:** {self.channel_username or 'قناة البوت'}

"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 انضمام", url=channel_link)],
            [InlineKeyboardButton(text="✅ انضممت", callback_data="check_membership")]
        ])
        
        # Send message based on event type
        if isinstance(event, Message):
            try:
                await event.answer(text, reply_markup=keyboard)
            except Exception as e:
                self.logger.error(f"Failed to send force join message: {e}")
        elif isinstance(event, CallbackQuery):
            try:
                if event.message:
                    await event.message.edit_text(text, reply_markup=keyboard)
                else:
                    await event.answer("🔒 لأستخدام البوت عليك الاشتراك بلقناة اولا.", show_alert=True)
            except Exception as e:
                self.logger.error(f"Failed to edit force join message: {e}")
                try:
                    await event.answer("🔒 لأستخدام البوت عليك الاشتراك بلقناة اولا.", show_alert=True)
                except:
                    pass

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiogram import Dispatcher
from typing import Dict, Any

from .common import router as common_router
from .admin import router as admin_router
from .manager import router as manager_router


def setup_routers(dp: Dispatcher, config: Dict[str, Any]):
    """Setup all routers"""
    
    # Include routers in order of priority
    dp.include_router(admin_router)      # Admin handlers
    dp.include_router(manager_router)    # Manager handlers
    dp.include_router(common_router)     # Common handlers (lowest priority)
    
    # Store config in routers
    for router in [admin_router, manager_router, common_router]:
        router.config = config

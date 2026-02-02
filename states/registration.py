#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiogram.fsm.state import State, StatesGroup


class ClassManagementStates(StatesGroup):
    """States for class management"""
    
    waiting_for_class_name = State()
    waiting_for_manager_username = State()
    waiting_for_manager_id = State()
    waiting_for_storage_channel = State()
    waiting_for_test_message = State()


class SubjectStates(StatesGroup):
    """States for subject management"""
    
    waiting_for_subject_name = State()


class FileStates(StatesGroup):
    """States for file management"""
    
    waiting_for_message_id = State()
    waiting_for_file_name = State()
    waiting_for_group_base_name = State()
    waiting_for_group_forwards = State()
    #waiting_for_subject_id = State()


class ExamStates(StatesGroup):
    """States for exam management"""
    
    waiting_for_exam_type = State()
    waiting_for_exam_title = State()
    waiting_for_exam_content = State()


class BroadcastStates(StatesGroup):
    """States for broadcast system"""
    waiting_for_message = State()


class ForceJoinStates(StatesGroup):
    """States for force join management"""
    waiting_for_channel = State()

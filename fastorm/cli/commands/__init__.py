"""
FastORM CLI命令模块

包含所有可用的CLI命令实现。
"""

from .init_command import init
from .model_command import create_model  
from .migrate_command import migrate
from .database_command import database as db
from .serve_command import serve
from .setup_command import setup
from .convert_command import convert

__all__ = [
    'init',
    'create_model',
    'migrate', 
    'db',
    'serve',
    'setup',
    'convert'
] 
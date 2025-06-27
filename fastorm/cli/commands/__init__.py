"""
FastORM CLI命令模块

包含所有可用的CLI命令实现。
"""

from .convert_command import convert
from .database_command import database as db
from .init_command import init
from .migrate_command import migrate
from .model_command import create_model
from .serve_command import serve
from .setup_command import setup

__all__ = ["init", "create_model", "migrate", "db", "serve", "setup", "convert"]

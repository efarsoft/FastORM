"""
FastORM 模型模块

提供简洁如ThinkORM的模型基类。
"""

from fastorm.model.model import DeclarativeBase
from fastorm.model.model import Model

__all__ = ["Model", "DeclarativeBase"]

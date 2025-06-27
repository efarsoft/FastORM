"""
FastORM序列化装饰器模块

提供便捷的序列化配置装饰器：
- 字段序列化装饰器
- 模型序列化装饰器
- 关系序列化装饰器
- 自定义序列化器装饰器
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from .fields import FieldConfig
from .fields import FieldType
from .serializers import BaseSerializer
from .serializers import FieldSerializer
from .serializers import ModelSerializer
from .serializers import RelationSerializer


def serialize_field(
    alias: str | None = None,
    field_type: FieldType = FieldType.STRING,
    exclude_none: bool = True,
    exclude_empty: bool = False,
    format_string: str | None = None,
    transformer: Callable[[Any], Any] | None = None,
    **kwargs,
) -> Callable:
    """字段序列化装饰器"""

    def decorator(func_or_class):
        if hasattr(func_or_class, "__annotations__"):
            # 类属性装饰
            field_name = func_or_class.__name__
            config = FieldConfig(
                name=field_name,
                alias=alias,
                field_type=field_type,
                exclude_none=exclude_none,
                exclude_empty=exclude_empty,
                format_string=format_string,
                transformer=transformer,
                **kwargs,
            )

            # 将配置附加到函数/属性
            func_or_class._serialization_config = config
            return func_or_class
        else:
            # 方法装饰
            @wraps(func_or_class)
            def wrapper(*args, **kwargs):
                result = func_or_class(*args, **kwargs)

                # 应用转换器
                if transformer:
                    result = transformer(result)

                return result

            # 附加序列化配置
            wrapper._serialization_config = FieldConfig(
                name=func_or_class.__name__,
                alias=alias,
                field_type=field_type,
                exclude_none=exclude_none,
                exclude_empty=exclude_empty,
                format_string=format_string,
                transformer=transformer,
                **kwargs,
            )

            return wrapper

    return decorator


def serialize_model(
    exclude_fields: list[str] | None = None,
    include_fields: list[str] | None = None,
    serialize_relations: bool = True,
    max_depth: int = 3,
    alias_mapping: dict[str, str] | None = None,
    **kwargs,
) -> Callable:
    """模型序列化装饰器"""

    def decorator(cls):
        # 收集字段序列化器
        field_serializers = {}

        # 检查类属性和方法的序列化配置
        for attr_name in dir(cls):
            if not attr_name.startswith("_"):
                attr = getattr(cls, attr_name)
                if hasattr(attr, "_serialization_config"):
                    config = attr._serialization_config
                    field_serializers[attr_name] = FieldSerializer(
                        name=config.name,
                        field_type=object,  # 动态类型
                        serializer_func=lambda v, c: v,
                        description=config.description,
                    )

        # 应用别名映射
        if alias_mapping:
            for field_name, alias in alias_mapping.items():
                if hasattr(cls, field_name):
                    field = getattr(cls, field_name)
                    if hasattr(field, "_serialization_config"):
                        field._serialization_config.alias = alias

        # 创建模型序列化器
        serializer = ModelSerializer(
            name=f"{cls.__name__}_serializer",
            model_type=cls,
            field_serializers=field_serializers,
            exclude_fields=exclude_fields,
            include_fields=include_fields,
            description=f"{cls.__name__}模型序列化器",
        )

        # 将序列化器附加到类
        cls._model_serializer = serializer
        cls._serialization_config = {
            "serialize_relations": serialize_relations,
            "max_depth": max_depth,
            **kwargs,
        }

        return cls

    return decorator


def serialize_relation(
    relation_type: str,
    target_model: type | None = None,
    lazy: bool = True,
    max_depth: int = 2,
    exclude_fields: list[str] | None = None,
    **kwargs,
) -> Callable:
    """关系序列化装饰器"""

    def decorator(func_or_attr):
        relation_name = func_or_attr.__name__

        # 创建关系序列化器
        serializer = RelationSerializer(
            name=relation_name,
            relation_type=relation_type,
            lazy=lazy,
            max_depth=max_depth,
            description=f"{relation_name}关系序列化器",
        )

        if callable(func_or_attr):

            @wraps(func_or_attr)
            def wrapper(*args, **kwargs):
                result = func_or_attr(*args, **kwargs)
                return result

            wrapper._relation_serializer = serializer
            wrapper._relation_config = {
                "target_model": target_model,
                "exclude_fields": exclude_fields,
                **kwargs,
            }

            return wrapper
        else:
            # 属性装饰
            func_or_attr._relation_serializer = serializer
            func_or_attr._relation_config = {
                "target_model": target_model,
                "exclude_fields": exclude_fields,
                **kwargs,
            }

            return func_or_attr

    return decorator


def custom_serializer(
    serializer_func: Callable[[Any, Any], Any],
    name: str | None = None,
    description: str = "",
) -> Callable:
    """自定义序列化器装饰器"""

    def decorator(func_or_class):
        serializer_name = name or f"{func_or_class.__name__}_serializer"

        if callable(func_or_class):

            @wraps(func_or_class)
            def wrapper(*args, **kwargs):
                result = func_or_class(*args, **kwargs)
                return result

            # 创建自定义序列化器
            custom_ser = type(
                "CustomSerializer",
                (BaseSerializer,),
                {
                    "serialize": lambda self, value, context=None: serializer_func(
                        value, context
                    ),
                    "can_serialize": lambda self, value: True,
                },
            )(serializer_name, description)

            wrapper._custom_serializer = custom_ser
            return wrapper
        else:
            # 类装饰
            custom_ser = type(
                "CustomSerializer",
                (BaseSerializer,),
                {
                    "serialize": lambda self, value, context=None: serializer_func(
                        value, context
                    ),
                    "can_serialize": lambda self, value: isinstance(
                        value, func_or_class
                    ),
                },
            )(serializer_name, description)

            func_or_class._custom_serializer = custom_ser
            return func_or_class

    return decorator


def exclude_from_serialization(func_or_attr):
    """排除字段或方法从序列化中"""

    if callable(func_or_attr):

        @wraps(func_or_attr)
        def wrapper(*args, **kwargs):
            return func_or_attr(*args, **kwargs)

        wrapper._exclude_from_serialization = True
        return wrapper
    else:
        func_or_attr._exclude_from_serialization = True
        return func_or_attr


def serializable_property(
    alias: str | None = None, field_type: FieldType = FieldType.STRING, **kwargs
) -> Callable:
    """可序列化属性装饰器"""

    def decorator(func):
        @property
        @wraps(func)
        def wrapper(self):
            return func(self)

        # 添加序列化配置
        wrapper._serialization_config = FieldConfig(
            name=func.__name__, alias=alias, field_type=field_type, **kwargs
        )

        return wrapper

    return decorator


def async_serializer(timeout: float = 30.0, max_concurrent: int = 10) -> Callable:
    """异步序列化器装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._async_serialization_config = {
            "timeout": timeout,
            "max_concurrent": max_concurrent,
        }

        return wrapper

    return decorator


def conditional_serialization(condition: Callable[[Any], bool]) -> Callable:
    """条件序列化装饰器"""

    def decorator(func_or_attr):
        if callable(func_or_attr):

            @wraps(func_or_attr)
            def wrapper(*args, **kwargs):
                result = func_or_attr(*args, **kwargs)
                return result

            wrapper._serialization_condition = condition
            return wrapper
        else:
            func_or_attr._serialization_condition = condition
            return func_or_attr

    return decorator


def transform_on_serialize(transformer: Callable[[Any], Any]) -> Callable:
    """序列化时转换装饰器"""

    def decorator(func_or_attr):
        if callable(func_or_attr):

            @wraps(func_or_attr)
            def wrapper(*args, **kwargs):
                result = func_or_attr(*args, **kwargs)
                return transformer(result)

            return wrapper
        else:
            # 为属性添加转换器
            original_getter = getattr(func_or_attr, "fget", lambda self: func_or_attr)

            def transformed_getter(self):
                value = original_getter(self)
                return transformer(value)

            if isinstance(func_or_attr, property):
                return property(
                    transformed_getter,
                    func_or_attr.fset,
                    func_or_attr.fdel,
                    func_or_attr.__doc__,
                )
            else:
                return transformed_getter

    return decorator


def serialize_as_reference(id_field: str = "id") -> Callable:
    """序列化为引用装饰器（避免循环引用）"""

    def decorator(func_or_attr):
        reference_config = {"serialize_as_reference": True, "id_field": id_field}

        if callable(func_or_attr):

            @wraps(func_or_attr)
            def wrapper(*args, **kwargs):
                return func_or_attr(*args, **kwargs)

            wrapper._reference_config = reference_config
            return wrapper
        else:
            func_or_attr._reference_config = reference_config
            return func_or_attr

    return decorator


# 便捷的组合装饰器


def serializable_datetime(
    alias: str | None = None, format_string: str = "%Y-%m-%d %H:%M:%S"
) -> Callable:
    """可序列化日期时间装饰器"""
    return serialize_field(
        alias=alias, field_type=FieldType.DATETIME, format_string=format_string
    )


def serializable_decimal(alias: str | None = None, precision: int = 2) -> Callable:
    """可序列化小数装饰器"""
    return serialize_field(
        alias=alias, field_type=FieldType.DECIMAL, precision=precision
    )


def serializable_json(alias: str | None = None) -> Callable:
    """可序列化JSON装饰器"""
    return serialize_field(alias=alias, field_type=FieldType.JSON)


def one_to_many_relation(
    target_model: type | None = None, max_depth: int = 2
) -> Callable:
    """一对多关系装饰器"""
    return serialize_relation(
        relation_type="one_to_many", target_model=target_model, max_depth=max_depth
    )


def many_to_one_relation(
    target_model: type | None = None, max_depth: int = 2
) -> Callable:
    """多对一关系装饰器"""
    return serialize_relation(
        relation_type="many_to_one", target_model=target_model, max_depth=max_depth
    )


def many_to_many_relation(
    target_model: type | None = None, max_depth: int = 1
) -> Callable:
    """多对多关系装饰器"""
    return serialize_relation(
        relation_type="many_to_many", target_model=target_model, max_depth=max_depth
    )

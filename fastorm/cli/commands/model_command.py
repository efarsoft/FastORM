"""
FastORM模型代码生成命令

自动生成FastORM模型代码，支持字段定义、关系配置等。
"""

import re
import sys
from pathlib import Path
from typing import Any

import click


@click.command(name="create:model")
@click.argument("model_name")
@click.option("--table", "-t", help="表名 (默认为模型名的复数形式)")
@click.option(
    "--fields",
    "-f",
    multiple=True,
    help="字段定义: name:type:options (例: name:str:required)",
)
@click.option(
    "--output", "-o", default="app/models", help="输出目录 (默认: app/models)"
)
@click.option("--force", is_flag=True, help="覆盖已存在的文件")
@click.pass_context
def create_model(
    ctx, model_name: str, table: str, fields: tuple, output: str, force: bool
):
    """
    🏗️ 生成FastORM模型代码

    自动生成包含字段定义、索引、关系等的完整模型代码。

    \b
    字段类型支持:
        str, string     - String字段
        int, integer    - Integer字段
        float           - Float字段
        bool, boolean   - Boolean字段
        date            - Date字段
        datetime        - DateTime字段
        text            - Text字段(长文本)
        json            - JSON字段

    \b
    字段选项:
        required        - 不允许为空 (nullable=False)
        unique          - 唯一约束
        index           - 创建索引
        default:value   - 默认值
        length:n        - 字符串长度限制

    \b
    示例:
        fastorm create:model User
        fastorm create:model Blog -t blog_posts
        fastorm create:model Product -f "name:str:required" -f "price:float:required"
        fastorm create:model User -f "email:str:required,unique" -f "age:int:default:18"
    """
    verbose = ctx.obj.get("verbose", False)

    # 验证模型名称
    if not _is_valid_model_name(model_name):
        click.echo(
            "❌ 模型名称无效。请使用PascalCase格式，如: User, BlogPost", err=True
        )
        sys.exit(1)

    # 确定表名
    if not table:
        table = _pluralize_table_name(model_name)

    # 解析字段定义
    parsed_fields = []
    if fields:
        try:
            parsed_fields = _parse_field_definitions(fields)
        except ValueError as e:
            click.echo(f"❌ 字段定义错误: {e}", err=True)
            sys.exit(1)

    # 确定输出路径
    output_dir = Path(output)
    if not output_dir.exists():
        if click.confirm(f"📁 目录 '{output}' 不存在，是否创建？"):
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            click.echo("❌ 模型生成已取消")
            sys.exit(1)

    # 生成模型文件
    model_file = output_dir / f"{_snake_case(model_name)}.py"

    if model_file.exists() and not force:
        if not click.confirm(f"⚠️ 文件 '{model_file}' 已存在，是否覆盖？"):
            click.echo("❌ 模型生成已取消")
            sys.exit(1)

    try:
        # 生成模型代码
        model_code = _generate_model_code(model_name, table, parsed_fields)

        # 写入文件
        with open(model_file, "w", encoding="utf-8") as f:
            f.write(model_code)

        # 更新__init__.py
        _update_init_file(output_dir, model_name, verbose)

        # 显示成功信息
        click.echo(f"✅ 模型 '{model_name}' 生成成功!")
        click.echo(f"📄 文件位置: {model_file}")
        click.echo(f"📋 表名: {table}")

        if parsed_fields:
            click.echo(f"🔧 字段数量: {len(parsed_fields)}")

        # 提示下一步操作
        click.echo("\n📚 下一步操作:")
        click.echo("   fastorm migrate          # 生成并运行数据库迁移")

    except Exception as e:
        click.echo(f"❌ 模型生成失败: {e}", err=True)
        sys.exit(1)


def _is_valid_model_name(name: str) -> bool:
    """验证模型名称是否有效（PascalCase）"""
    pattern = r"^[A-Z][a-zA-Z0-9]*$"
    return bool(re.match(pattern, name))


def _snake_case(name: str) -> str:
    """将PascalCase转换为snake_case"""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _pluralize_table_name(model_name: str) -> str:
    """生成表名（简单复数形式）"""
    snake_name = _snake_case(model_name)

    # 简单的英文复数规则
    if snake_name.endswith("y"):
        return snake_name[:-1] + "ies"
    elif snake_name.endswith(("s", "sh", "ch", "x", "z")):
        return snake_name + "es"
    else:
        return snake_name + "s"


def _parse_field_definitions(fields: tuple) -> list[dict[str, Any]]:
    """解析字段定义"""
    parsed_fields = []

    for field_def in fields:
        parts = field_def.split(":")
        if len(parts) < 2:
            raise ValueError(f"字段定义格式错误: {field_def}")

        field_name = parts[0].strip()
        field_type = parts[1].strip()

        # 解析选项
        options = []
        if len(parts) > 2:
            options = parts[2].split(",")

        # 验证字段名
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", field_name):
            raise ValueError(f"字段名无效: {field_name}")

        # 解析字段配置
        field_config = _parse_field_config(field_type, options)
        field_config["name"] = field_name

        parsed_fields.append(field_config)

    return parsed_fields


def _parse_field_config(field_type: str, options: list[str]) -> dict[str, Any]:
    """解析字段配置"""
    # 标准化字段类型
    type_mapping = {
        "str": "String",
        "string": "String",
        "int": "Integer",
        "integer": "Integer",
        "float": "Float",
        "bool": "Boolean",
        "boolean": "Boolean",
        "date": "Date",
        "datetime": "DateTime",
        "text": "Text",
        "json": "JSON",
    }

    sqlalchemy_type = type_mapping.get(field_type.lower())
    if not sqlalchemy_type:
        raise ValueError(f"不支持的字段类型: {field_type}")

    config = {
        "type": sqlalchemy_type,
        "nullable": True,
        "unique": False,
        "index": False,
        "default": None,
        "length": None,
    }

    # 解析选项
    for option in options:
        option = option.strip()

        if option == "required":
            config["nullable"] = False
        elif option == "unique":
            config["unique"] = True
        elif option == "index":
            config["index"] = True
        elif option.startswith("default:"):
            default_value = option.split(":", 1)[1]
            config["default"] = _parse_default_value(default_value, sqlalchemy_type)
        elif option.startswith("length:"):
            try:
                config["length"] = int(option.split(":", 1)[1])
            except ValueError:
                raise ValueError(f"长度值无效: {option}")

    return config


def _parse_default_value(value: str, field_type: str) -> Any:
    """解析默认值"""
    if value.lower() == "null":
        return None
    elif value.lower() in ("true", "false") and field_type == "Boolean":
        return value.lower() == "true"
    elif field_type in ("Integer", "Float"):
        try:
            return int(value) if field_type == "Integer" else float(value)
        except ValueError:
            raise ValueError(f"数值默认值无效: {value}")
    else:
        return f"'{value}'"


def _generate_model_code(
    model_name: str, table_name: str, fields: list[dict[str, Any]]
) -> str:
    """生成模型代码"""

    # 导入语句
    imports = [
        "from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, Text, JSON",
        "from .base import AppBaseModel",
    ]

    # 需要的额外导入
    if any(f.get("default") for f in fields):
        imports.insert(0, "from datetime import datetime")

    # 生成字段代码
    field_lines = []
    if not fields:
        # 如果没有指定字段，添加基本字段示例
        field_lines = [
            "    name = Column(String(100), nullable=False)",
            "    # TODO: 添加更多字段",
        ]
    else:
        for field in fields:
            field_line = _generate_field_line(field)
            field_lines.append(f"    {field_line}")

    # 生成完整模型代码
    code = f'''"""
{model_name} model

Generated by FastORM CLI
"""

{chr(10).join(imports)}


class {model_name}(AppBaseModel):
    """
    {model_name} 模型
    """
    __tablename__ = "{table_name}"
    
{chr(10).join(field_lines)}
    
    def __repr__(self):
        return f"<{model_name}(id={{self.id}})>"
    
    class Config:
        """Pydantic配置"""
        from_attributes = True
'''

    return code


def _generate_field_line(field: dict[str, Any]) -> str:
    """生成字段定义代码行"""
    field_name = field["name"]
    field_type = field["type"]

    # 构建字段类型
    if field_type == "String" and field.get("length"):
        type_def = f"String({field['length']})"
    else:
        type_def = field_type

    # 构建字段选项
    options = []

    if not field["nullable"]:
        options.append("nullable=False")

    if field["unique"]:
        options.append("unique=True")

    if field["index"]:
        options.append("index=True")

    if field["default"] is not None:
        options.append(f"default={field['default']}")

    # 组合字段定义
    options_str = ", ".join(options)
    if options_str:
        return f"{field_name} = Column({type_def}, {options_str})"
    else:
        return f"{field_name} = Column({type_def})"


def _update_init_file(output_dir: Path, model_name: str, verbose: bool):
    """更新__init__.py文件，添加新模型导入"""
    init_file = output_dir / "__init__.py"

    # 生成导入语句
    module_name = _snake_case(model_name)
    import_line = f"from .{module_name} import {model_name}"

    # 读取现有内容
    existing_content = ""
    if init_file.exists():
        with open(init_file, encoding="utf-8") as f:
            existing_content = f.read()

    # 检查是否已经导入
    if import_line in existing_content:
        return

    # 添加导入
    if existing_content.strip():
        new_content = existing_content.rstrip() + "\n" + import_line + "\n"
    else:
        new_content = '"""Models package"""\n\n' + import_line + "\n"

    # 写入文件
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    if verbose:
        click.echo(f"  ✓ 更新 {init_file.name}")

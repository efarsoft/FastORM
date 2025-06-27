"""
现有模型转换命令

将现有的SQLAlchemy模型转换为FastORM模型。
"""

import ast
import re
import sys
from pathlib import Path

import click


@click.command()
@click.argument("source_path", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="fastorm_models", help="输出目录")
@click.option("--backup/--no-backup", default=True, help="是否备份原始文件")
@click.option("--force", is_flag=True, help="强制覆盖现有文件")
@click.option("--dry-run", is_flag=True, help="预览模式，不实际生成文件")
@click.pass_context
def convert(
    ctx, source_path: str, output_dir: str, backup: bool, force: bool, dry_run: bool
):
    """
    🔄 转换现有SQLAlchemy模型到FastORM

    分析现有的SQLAlchemy模型文件，生成对应的FastORM模型代码。
    支持自动转换字段定义、关系和约束。

    \b
    支持的转换:
        - Table/Column定义 → FastORM字段
        - 关系定义 → FastORM关系
        - 索引和约束 → FastORM约束
        - 自定义方法 → 保留原有逻辑

    \b
    参数:
        SOURCE_PATH  源模型文件或目录路径

    \b
    示例:
        fastorm convert models.py                    # 转换单个文件
        fastorm convert app/models/                  # 转换整个目录
        fastorm convert models.py -o new_models     # 指定输出目录
        fastorm convert models.py --dry-run         # 预览转换结果
    """
    verbose = ctx.obj.get("verbose", False)

    if dry_run:
        click.echo("🔍 预览模式 - 不会实际生成任何文件")

    try:
        source_path = Path(source_path)
        output_path = Path(output_dir)

        # 收集要转换的文件
        model_files = _collect_model_files(source_path, verbose)

        if not model_files:
            click.echo("❌ 未找到SQLAlchemy模型文件")
            sys.exit(1)

        click.echo(f"🔍 找到 {len(model_files)} 个模型文件")

        # 确认转换
        if not dry_run and not click.confirm("🔄 是否开始转换？"):
            click.echo("❌ 转换已取消")
            sys.exit(1)

        # 创建输出目录
        if not dry_run:
            output_path.mkdir(exist_ok=True)

        # 转换文件
        conversion_results = []
        for model_file in model_files:
            result = _convert_model_file(
                model_file, output_path, backup, force, dry_run, verbose
            )
            conversion_results.append(result)

        # 生成统计报告
        _show_conversion_summary(conversion_results, dry_run)

    except Exception as e:
        click.echo(f"❌ 转换失败: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def _collect_model_files(source_path: Path, verbose: bool) -> list[Path]:
    """收集要转换的模型文件"""
    model_files = []

    if source_path.is_file():
        if _is_sqlalchemy_model_file(source_path):
            model_files.append(source_path)
    elif source_path.is_dir():
        for py_file in source_path.rglob("*.py"):
            if _is_sqlalchemy_model_file(py_file):
                model_files.append(py_file)

    if verbose:
        click.echo(f"🔍 扫描路径: {source_path}")
        for file in model_files:
            click.echo(f"   - {file}")

    return model_files


def _is_sqlalchemy_model_file(file_path: Path) -> bool:
    """检查文件是否为SQLAlchemy模型文件"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 检查SQLAlchemy特征
        sqlalchemy_patterns = [
            r"from\s+sqlalchemy",
            r"import\s+.*Column",
            r"declarative_base",
            r"__tablename__\s*=",
            r"Column\s*\(",
            r"relationship\s*\(",
            r"ForeignKey\s*\(",
        ]

        return any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in sqlalchemy_patterns
        )

    except Exception:
        return False


def _convert_model_file(
    model_file: Path,
    output_path: Path,
    backup: bool,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """转换单个模型文件"""
    if verbose or dry_run:
        click.echo(f"\n🔄 转换文件: {model_file}")

    try:
        # 读取源文件
        with open(model_file, encoding="utf-8") as f:
            source_content = f.read()

        # 解析源代码
        parsed_models = _parse_sqlalchemy_models(source_content, verbose)

        # 生成FastORM代码
        fastorm_content = _generate_fastorm_code(parsed_models, source_content, verbose)

        # 确定输出文件路径
        output_file = output_path / f"fastorm_{model_file.name}"

        result = {
            "source_file": model_file,
            "output_file": output_file,
            "models_found": len(parsed_models),
            "success": True,
            "message": "",
            "backup_created": False,
        }

        if dry_run:
            result["message"] = "[预览] 将生成FastORM模型"
            click.echo(f"   [预览] → {output_file}")
            click.echo(f"   [预览] 检测到 {len(parsed_models)} 个模型")
            return result

        # 备份原文件
        if backup:
            backup_file = model_file.with_suffix(f".bak{model_file.suffix}")
            if not backup_file.exists():
                backup_file.write_text(source_content, encoding="utf-8")
                result["backup_created"] = True
                if verbose:
                    click.echo(f"   💾 已创建备份: {backup_file}")

        # 写入转换后的文件
        if not output_file.exists() or force:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(fastorm_content)

            result["message"] = f"成功转换 {len(parsed_models)} 个模型"
            if verbose:
                click.echo(f"   ✅ 已生成: {output_file}")
        else:
            result["success"] = False
            result["message"] = "输出文件已存在（使用 --force 强制覆盖）"
            if verbose:
                click.echo(f"   ⚠️ 文件已存在: {output_file}")

        return result

    except Exception as e:
        return {
            "source_file": model_file,
            "output_file": None,
            "models_found": 0,
            "success": False,
            "message": f"转换失败: {e}",
            "backup_created": False,
        }


def _parse_sqlalchemy_models(source_content: str, verbose: bool) -> list[dict]:
    """解析SQLAlchemy模型"""
    models = []

    try:
        # 使用AST解析Python代码
        tree = ast.parse(source_content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                model_info = _analyze_model_class(node, source_content)
                if model_info:
                    models.append(model_info)
                    if verbose:
                        click.echo(f"   📋 找到模型: {model_info['name']}")

    except Exception as e:
        if verbose:
            click.echo(f"   ⚠️ 解析失败: {e}")

    return models


def _analyze_model_class(class_node: ast.ClassDef, source_content: str) -> dict | None:
    """分析模型类"""
    model_info = {
        "name": class_node.name,
        "tablename": None,
        "columns": [],
        "relationships": [],
        "methods": [],
        "imports": [],
        "base_classes": [],
    }

    # 检查是否为SQLAlchemy模型
    if not _is_sqlalchemy_model_class(class_node, source_content):
        return None

    # 分析基类
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            model_info["base_classes"].append(base.id)
        elif isinstance(base, ast.Attribute):
            model_info["base_classes"].append(f"{base.value.id}.{base.attr}")

    # 分析类体
    for item in class_node.body:
        if isinstance(item, ast.Assign):
            _analyze_assignment(item, model_info, source_content)
        elif isinstance(item, ast.FunctionDef):
            if not item.name.startswith("_"):
                model_info["methods"].append(
                    {
                        "name": item.name,
                        "args": [arg.arg for arg in item.args.args],
                        "is_property": any(
                            isinstance(d, ast.Name) and d.id == "property"
                            for d in item.decorator_list
                        ),
                    }
                )

    return model_info


def _is_sqlalchemy_model_class(class_node: ast.ClassDef, source_content: str) -> bool:
    """检查是否为SQLAlchemy模型类"""
    # 检查是否有__tablename__属性
    for item in class_node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    return True

    # 检查是否有Column定义
    for item in class_node.body:
        if isinstance(item, ast.Assign):
            if isinstance(item.value, ast.Call):
                if _is_column_call(item.value):
                    return True

    return False


def _analyze_assignment(assign_node: ast.Assign, model_info: dict, source_content: str):
    """分析赋值语句"""
    for target in assign_node.targets:
        if isinstance(target, ast.Name):
            target_name = target.id

            if target_name == "__tablename__":
                # 提取表名
                if isinstance(assign_node.value, ast.Constant):
                    model_info["tablename"] = assign_node.value.value
                elif isinstance(assign_node.value, ast.Str):  # Python < 3.8
                    model_info["tablename"] = assign_node.value.s

            elif isinstance(assign_node.value, ast.Call):
                if _is_column_call(assign_node.value):
                    # Column定义
                    column_info = _analyze_column(
                        target_name, assign_node.value, source_content
                    )
                    model_info["columns"].append(column_info)
                elif _is_relationship_call(assign_node.value):
                    # Relationship定义
                    rel_info = _analyze_relationship(
                        target_name, assign_node.value, source_content
                    )
                    model_info["relationships"].append(rel_info)


def _is_column_call(call_node: ast.Call) -> bool:
    """检查是否为Column调用"""
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id == "Column"
    elif isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr == "Column"
    return False


def _is_relationship_call(call_node: ast.Call) -> bool:
    """检查是否为relationship调用"""
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id == "relationship"
    elif isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr == "relationship"
    return False


def _analyze_column(column_name: str, call_node: ast.Call, source_content: str) -> dict:
    """分析Column定义"""
    column_info = {
        "name": column_name,
        "type": None,
        "primary_key": False,
        "nullable": True,
        "unique": False,
        "default": None,
        "foreign_key": None,
        "index": False,
    }

    # 分析位置参数（类型）
    if call_node.args:
        type_arg = call_node.args[0]
        column_info["type"] = _extract_type_from_ast(type_arg)

    # 分析关键字参数
    for keyword in call_node.keywords:
        if keyword.arg == "primary_key":
            column_info["primary_key"] = _extract_bool_value(keyword.value)
        elif keyword.arg == "nullable":
            column_info["nullable"] = _extract_bool_value(keyword.value)
        elif keyword.arg == "unique":
            column_info["unique"] = _extract_bool_value(keyword.value)
        elif keyword.arg == "default":
            column_info["default"] = _extract_default_value(keyword.value)
        elif keyword.arg == "index":
            column_info["index"] = _extract_bool_value(keyword.value)

    # 检查ForeignKey
    for arg in call_node.args[1:]:  # 跳过类型参数
        if isinstance(arg, ast.Call) and _is_foreign_key_call(arg):
            column_info["foreign_key"] = _extract_foreign_key(arg)

    return column_info


def _analyze_relationship(
    rel_name: str, call_node: ast.Call, source_content: str
) -> dict:
    """分析relationship定义"""
    rel_info = {
        "name": rel_name,
        "target": None,
        "back_populates": None,
        "foreign_keys": None,
        "lazy": None,
    }

    # 分析位置参数（目标模型）
    if call_node.args:
        target_arg = call_node.args[0]
        if isinstance(target_arg, ast.Constant):
            rel_info["target"] = target_arg.value
        elif isinstance(target_arg, ast.Str):
            rel_info["target"] = target_arg.s
        elif isinstance(target_arg, ast.Name):
            rel_info["target"] = target_arg.id

    # 分析关键字参数
    for keyword in call_node.keywords:
        if keyword.arg == "back_populates":
            if isinstance(keyword.value, ast.Constant):
                rel_info["back_populates"] = keyword.value.value
            elif isinstance(keyword.value, ast.Str):
                rel_info["back_populates"] = keyword.value.s

    return rel_info


def _extract_type_from_ast(type_node: ast.AST) -> str:
    """从AST节点提取类型信息"""
    if isinstance(type_node, ast.Name):
        return type_node.id
    elif isinstance(type_node, ast.Attribute):
        return f"{type_node.value.id}.{type_node.attr}"
    elif isinstance(type_node, ast.Call):
        if isinstance(type_node.func, ast.Name):
            type_name = type_node.func.id
            if type_node.args:
                args = []
                for arg in type_node.args:
                    if isinstance(arg, ast.Constant):
                        args.append(str(arg.value))
                    elif isinstance(arg, ast.Num):  # Python < 3.8
                        args.append(str(arg.n))
                if args:
                    return f"{type_name}({', '.join(args)})"
            return type_name
    return "Unknown"


def _extract_bool_value(value_node: ast.AST) -> bool:
    """提取布尔值"""
    if isinstance(value_node, ast.Constant) or isinstance(value_node, ast.NameConstant):
        return bool(value_node.value)
    return False


def _extract_default_value(value_node: ast.AST) -> str:
    """提取默认值"""
    if isinstance(value_node, ast.Constant):
        return repr(value_node.value)
    elif isinstance(value_node, ast.Str):
        return repr(value_node.s)
    elif isinstance(value_node, ast.Num):
        return str(value_node.n)
    elif isinstance(value_node, ast.Name):
        return value_node.id
    elif isinstance(value_node, ast.Call):
        if isinstance(value_node.func, ast.Attribute):
            return f"{value_node.func.value.id}.{value_node.func.attr}()"
    return "None"


def _is_foreign_key_call(call_node: ast.Call) -> bool:
    """检查是否为ForeignKey调用"""
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id == "ForeignKey"
    elif isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr == "ForeignKey"
    return False


def _extract_foreign_key(fk_node: ast.Call) -> str:
    """提取外键信息"""
    if fk_node.args:
        fk_arg = fk_node.args[0]
        if isinstance(fk_arg, ast.Constant):
            return fk_arg.value
        elif isinstance(fk_arg, ast.Str):
            return fk_arg.s
    return None


def _generate_fastorm_code(
    models: list[dict], original_content: str, verbose: bool
) -> str:
    """生成FastORM代码"""
    lines = []

    # 文件头注释
    lines.append('"""')
    lines.append("FastORM模型")
    lines.append("")
    lines.append("此文件由FastORM转换工具自动生成。")
    lines.append("原始SQLAlchemy模型已转换为FastORM格式。")
    lines.append('"""')
    lines.append("")

    # 导入语句
    lines.extend(_generate_imports(models))
    lines.append("")

    # 生成每个模型
    for i, model in enumerate(models):
        if i > 0:
            lines.append("")
        lines.extend(_generate_model_code(model))

    # 添加原始代码的注释版本
    lines.append("")
    lines.append("")
    lines.append(
        "# ============================================================================="
    )
    lines.append("# 原始SQLAlchemy代码（已注释）")
    lines.append(
        "# ============================================================================="
    )
    lines.append("")
    for line in original_content.split("\n"):
        lines.append(f"# {line}")

    return "\n".join(lines)


def _generate_imports(models: list[dict]) -> list[str]:
    """生成导入语句"""
    imports = [
        "from fastorm import BaseModel",
        "from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey",
        "from sqlalchemy.orm import relationship",
        "from datetime import datetime",
        "from typing import Optional, List",
    ]

    # 根据模型中使用的类型添加额外导入
    used_types = set()
    for model in models:
        for column in model["columns"]:
            column_type = column["type"]
            if "Float" in column_type or "Numeric" in column_type:
                used_types.add("Float")
            if "JSON" in column_type:
                used_types.add("JSON")
            if "Date" in column_type and "DateTime" not in column_type:
                used_types.add("Date")

    if used_types:
        imports.append(f'from sqlalchemy import {", ".join(sorted(used_types))}')

    return imports


def _generate_model_code(model: dict) -> list[str]:
    """生成单个模型的代码"""
    lines = []

    # 类定义
    class_line = f'class {model["name"]}(BaseModel):'
    lines.append(class_line)

    # 文档字符串
    lines.append('    """')
    lines.append(f'    {model["name"]}模型')
    lines.append("    ")
    lines.append("    从SQLAlchemy模型自动转换而来。")
    lines.append('    """')

    # 表名
    if model["tablename"]:
        lines.append(f'    __tablename__ = "{model["tablename"]}"')
        lines.append("")

    # 列定义
    for column in model["columns"]:
        column_line = _generate_column_definition(column)
        lines.append(f"    {column_line}")

    if model["columns"]:
        lines.append("")

    # 关系定义
    for relationship in model["relationships"]:
        rel_line = _generate_relationship_definition(relationship)
        lines.append(f"    {rel_line}")

    if model["relationships"]:
        lines.append("")

    # 方法定义（简化版本）
    if model["methods"]:
        lines.append("    # 原始方法（需要手动适配）")
        for method in model["methods"]:
            if method["is_property"]:
                lines.append("    # @property")
                lines.append(f'    # def {method["name"]}(self):')
                lines.append("    #     # TODO: 实现属性逻辑")
                lines.append("    #     pass")
            else:
                args_str = ", ".join(method["args"]) if method["args"] else ""
                lines.append(f'    # def {method["name"]}({args_str}):')
                lines.append("    #     # TODO: 实现方法逻辑")
                lines.append("    #     pass")
            lines.append("")

    return lines


def _generate_column_definition(column: dict) -> str:
    """生成列定义"""
    parts = [f'{column["name"]} = Column(']

    # 类型
    type_str = _convert_sqlalchemy_type_to_fastorm(column["type"])
    parts.append(type_str)

    # 约束
    constraints = []
    if column["primary_key"]:
        constraints.append("primary_key=True")
    if not column["nullable"]:
        constraints.append("nullable=False")
    if column["unique"]:
        constraints.append("unique=True")
    if column["index"]:
        constraints.append("index=True")
    if column["default"] and column["default"] != "None":
        constraints.append(f'default={column["default"]}')

    if constraints:
        parts.append(", " + ", ".join(constraints))

    parts.append(")")

    return "".join(parts)


def _generate_relationship_definition(relationship: dict) -> str:
    """生成关系定义"""
    parts = [f'{relationship["name"]} = relationship(']

    # 目标模型
    if relationship["target"]:
        parts.append(f'"{relationship["target"]}"')

    # 反向引用
    if relationship["back_populates"]:
        parts.append(f', back_populates="{relationship["back_populates"]}"')

    parts.append(")")

    return "".join(parts)


def _convert_sqlalchemy_type_to_fastorm(sqlalchemy_type: str) -> str:
    """转换SQLAlchemy类型到FastORM类型"""
    # 基本类型映射
    type_mapping = {
        "Integer": "Integer",
        "String": "String",
        "Text": "Text",
        "Boolean": "Boolean",
        "DateTime": "DateTime",
        "Date": "Date",
        "Float": "Float",
        "JSON": "JSON",
    }

    # 处理带参数的类型
    for sql_type, fastorm_type in type_mapping.items():
        if sqlalchemy_type.startswith(sql_type):
            return sqlalchemy_type.replace(sql_type, fastorm_type)

    # 默认返回原类型
    return sqlalchemy_type


def _show_conversion_summary(results: list[dict], dry_run: bool):
    """显示转换摘要"""
    if dry_run:
        click.echo("\n🔍 转换预览完成")
        return

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    click.echo("\n📊 转换完成:")
    click.echo("=" * 50)
    click.echo(f"✅ 成功: {len(successful)} 个文件")
    click.echo(f"❌ 失败: {len(failed)} 个文件")

    total_models = sum(r["models_found"] for r in successful)
    click.echo(f"📋 转换模型: {total_models} 个")

    if successful:
        click.echo("\n✅ 成功转换的文件:")
        for result in successful:
            click.echo(f"   {result['source_file']} → {result['output_file']}")
            click.echo(f"      {result['message']}")

    if failed:
        click.echo("\n❌ 转换失败的文件:")
        for result in failed:
            click.echo(f"   {result['source_file']}: {result['message']}")

    if successful:
        click.echo("\n🚀 下一步操作:")
        click.echo("   1. 检查生成的FastORM模型代码")
        click.echo("   2. 手动调整复杂的方法和属性")
        click.echo("   3. 更新导入语句和依赖")
        click.echo("   4. 运行测试验证转换结果")
        click.echo("   5. 逐步替换原有模型使用")

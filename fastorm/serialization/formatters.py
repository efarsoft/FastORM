"""
FastORM序列化格式化器模块

提供多种输出格式的格式化器：
- JSON格式化器
- XML格式化器
- CSV格式化器
- 自定义格式化器支持
"""

import json
import csv
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, TextIO
from io import StringIO
from datetime import datetime, date
from decimal import Decimal

from .exceptions import FormatterError


class BaseFormatter(ABC):
    """格式化器基类"""
    
    def __init__(self, name: str, format_type: str, description: str = ""):
        self.name = name
        self.format_type = format_type
        self.description = description
    
    @abstractmethod
    def format(self, data: Any, **kwargs) -> str:
        """格式化数据"""
        pass
    
    @abstractmethod
    def parse(self, content: str, **kwargs) -> Any:
        """解析格式化的内容"""
        pass
    
    def supports_type(self, data_type: type) -> bool:
        """检查是否支持该数据类型"""
        return True
    
    def __call__(self, data: Any, **kwargs) -> str:
        """使格式化器可调用"""
        return self.format(data, **kwargs)


class JSONFormatter(BaseFormatter):
    """JSON格式化器"""
    
    def __init__(self):
        super().__init__("json", "application/json", "JSON格式化器")
    
    def format(
        self,
        data: Any,
        indent: Optional[int] = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
        **kwargs
    ) -> str:
        """格式化为JSON"""
        
        try:
            # 预处理数据
            processed_data = self._preprocess_data(data)
            
            return json.dumps(
                processed_data,
                indent=indent,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                default=self._json_default,
                **kwargs
            )
        except Exception as e:
            raise FormatterError(
                f"JSON格式化失败: {str(e)}",
                formatter_name=self.name,
                format_type=self.format_type
            )
    
    def parse(self, content: str, **kwargs) -> Any:
        """解析JSON内容"""
        
        try:
            return json.loads(content, **kwargs)
        except Exception as e:
            raise FormatterError(
                f"JSON解析失败: {str(e)}",
                formatter_name=self.name,
                format_type=self.format_type
            )
    
    def _preprocess_data(self, data: Any) -> Any:
        """预处理数据以支持JSON序列化"""
        
        if isinstance(data, dict):
            return {key: self._preprocess_data(value) for key, value in data.items()}
        elif isinstance(data, (list, tuple, set)):
            return [self._preprocess_data(item) for item in data]
        elif isinstance(data, (datetime, date)):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return float(data)
        elif hasattr(data, '__dict__'):
            # 对象转换为字典
            return self._preprocess_data(data.__dict__)
        else:
            return data
    
    def _json_default(self, obj: Any) -> Any:
        """JSON序列化默认处理器"""
        
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class XMLFormatter(BaseFormatter):
    """XML格式化器"""
    
    def __init__(self):
        super().__init__("xml", "application/xml", "XML格式化器")
    
    def format(
        self,
        data: Any,
        root_name: str = "root",
        item_name: str = "item",
        encoding: str = "utf-8",
        **kwargs
    ) -> str:
        """格式化为XML"""
        
        try:
            root = ET.Element(root_name)
            self._build_xml_element(root, data, item_name)
            
            # 格式化XML
            self._indent_xml(root)
            
            return ET.tostring(root, encoding="unicode", method="xml")
        except Exception as e:
            raise FormatterError(
                f"XML格式化失败: {str(e)}",
                formatter_name=self.name,
                format_type=self.format_type
            )
    
    def parse(self, content: str, **kwargs) -> Dict[str, Any]:
        """解析XML内容"""
        
        try:
            root = ET.fromstring(content)
            return self._parse_xml_element(root)
        except Exception as e:
            raise FormatterError(
                f"XML解析失败: {str(e)}",
                formatter_name=self.name,
                format_type=self.format_type
            )
    
    def _build_xml_element(
        self,
        parent: ET.Element,
        data: Any,
        item_name: str = "item"
    ) -> None:
        """构建XML元素"""
        
        if isinstance(data, dict):
            for key, value in data.items():
                # 确保键是有效的XML标签名
                tag_name = self._sanitize_tag_name(str(key))
                element = ET.SubElement(parent, tag_name)
                
                if isinstance(value, (dict, list)):
                    self._build_xml_element(element, value, item_name)
                else:
                    element.text = self._format_xml_value(value)
        
        elif isinstance(data, (list, tuple, set)):
            for item in data:
                element = ET.SubElement(parent, item_name)
                if isinstance(item, (dict, list)):
                    self._build_xml_element(element, item, item_name)
                else:
                    element.text = self._format_xml_value(item)
        
        else:
            parent.text = self._format_xml_value(data)
    
    def _parse_xml_element(self, element: ET.Element) -> Union[Dict[str, Any], str]:
        """解析XML元素"""
        
        # 如果有子元素
        if len(element) > 0:
            result = {}
            for child in element:
                tag = child.tag
                value = self._parse_xml_element(child)
                
                # 处理重复标签
                if tag in result:
                    if not isinstance(result[tag], list):
                        result[tag] = [result[tag]]
                    result[tag].append(value)
                else:
                    result[tag] = value
            
            return result
        else:
            # 叶子节点，返回文本内容
            return element.text or ""
    
    def _sanitize_tag_name(self, name: str) -> str:
        """清理标签名，确保符合XML规范"""
        
        # 移除非法字符
        import re
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        # 确保以字母开头
        if name and not name[0].isalpha():
            name = f"tag_{name}"
        
        return name or "element"
    
    def _format_xml_value(self, value: Any) -> str:
        """格式化XML值"""
        
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        else:
            return str(value)
    
    def _indent_xml(self, element: ET.Element, level: int = 0) -> None:
        """缩进XML以提高可读性"""
        
        indent = "\n" + "  " * level
        if len(element):
            if not element.text or not element.text.strip():
                element.text = indent + "  "
            if not element.tail or not element.tail.strip():
                element.tail = indent
            for child in element:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not element.tail or not element.tail.strip()):
                element.tail = indent


class CSVFormatter(BaseFormatter):
    """CSV格式化器"""
    
    def __init__(self):
        super().__init__("csv", "text/csv", "CSV格式化器")
    
    def format(
        self,
        data: Any,
        headers: Optional[List[str]] = None,
        delimiter: str = ",",
        quotechar: str = '"',
        **kwargs
    ) -> str:
        """格式化为CSV"""
        
        try:
            output = StringIO()
            
            # 预处理数据
            rows = self._prepare_csv_data(data)
            
            if not rows:
                return ""
            
            # 确定表头
            if headers is None:
                headers = self._extract_headers(rows)
            
            writer = csv.DictWriter(
                output,
                fieldnames=headers,
                delimiter=delimiter,
                quotechar=quotechar,
                **kwargs
            )
            
            writer.writeheader()
            for row in rows:
                # 确保行数据包含所有字段
                normalized_row = {header: row.get(header, "") for header in headers}
                writer.writerow(normalized_row)
            
            return output.getvalue()
        
        except Exception as e:
            raise FormatterError(
                f"CSV格式化失败: {str(e)}",
                formatter_name=self.name,
                format_type=self.format_type
            )
    
    def parse(
        self,
        content: str,
        delimiter: str = ",",
        quotechar: str = '"',
        **kwargs
    ) -> List[Dict[str, Any]]:
        """解析CSV内容"""
        
        try:
            input_stream = StringIO(content)
            reader = csv.DictReader(
                input_stream,
                delimiter=delimiter,
                quotechar=quotechar,
                **kwargs
            )
            
            return [dict(row) for row in reader]
        
        except Exception as e:
            raise FormatterError(
                f"CSV解析失败: {str(e)}",
                formatter_name=self.name,
                format_type=self.format_type
            )
    
    def _prepare_csv_data(self, data: Any) -> List[Dict[str, Any]]:
        """准备CSV数据"""
        
        if isinstance(data, dict):
            # 单个对象
            return [self._flatten_dict(data)]
        elif isinstance(data, (list, tuple)):
            # 对象列表
            rows = []
            for item in data:
                if isinstance(item, dict):
                    rows.append(self._flatten_dict(item))
                else:
                    rows.append({"value": str(item)})
            return rows
        else:
            # 单个值
            return [{"value": str(data)}]
    
    def _flatten_dict(
        self,
        data: Dict[str, Any],
        prefix: str = "",
        separator: str = "."
    ) -> Dict[str, str]:
        """扁平化字典"""
        
        result = {}
        
        for key, value in data.items():
            full_key = f"{prefix}{separator}{key}" if prefix else key
            
            if isinstance(value, dict):
                # 递归扁平化
                result.update(self._flatten_dict(value, full_key, separator))
            elif isinstance(value, (list, tuple)):
                # 列表转换为字符串
                result[full_key] = self._format_csv_value(value)
            else:
                result[full_key] = self._format_csv_value(value)
        
        return result
    
    def _extract_headers(self, rows: List[Dict[str, Any]]) -> List[str]:
        """提取表头"""
        
        headers = set()
        for row in rows:
            headers.update(row.keys())
        
        return sorted(list(headers))
    
    def _format_csv_value(self, value: Any) -> str:
        """格式化CSV值"""
        
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (list, tuple, set)):
            return "; ".join(str(item) for item in value)
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        else:
            return str(value)


class FormatterRegistry:
    """格式化器注册表"""
    
    def __init__(self):
        self._formatters: Dict[str, BaseFormatter] = {}
        self._mime_type_mapping: Dict[str, str] = {}
        
        # 注册内置格式化器
        self._register_builtin_formatters()
    
    def register_formatter(
        self,
        name: str,
        formatter: BaseFormatter,
        mime_types: Optional[List[str]] = None
    ) -> None:
        """注册格式化器"""
        
        self._formatters[name] = formatter
        
        # 注册MIME类型映射
        if mime_types:
            for mime_type in mime_types:
                self._mime_type_mapping[mime_type] = name
    
    def get_formatter(self, name: str) -> Optional[BaseFormatter]:
        """获取格式化器"""
        return self._formatters.get(name)
    
    def get_formatter_by_mime_type(self, mime_type: str) -> Optional[BaseFormatter]:
        """根据MIME类型获取格式化器"""
        formatter_name = self._mime_type_mapping.get(mime_type)
        if formatter_name:
            return self.get_formatter(formatter_name)
        return None
    
    def list_formatters(self) -> List[str]:
        """列出所有格式化器"""
        return list(self._formatters.keys())
    
    def list_supported_mime_types(self) -> List[str]:
        """列出支持的MIME类型"""
        return list(self._mime_type_mapping.keys())
    
    def format_data(
        self,
        data: Any,
        format_name: str,
        **kwargs
    ) -> str:
        """格式化数据"""
        
        formatter = self.get_formatter(format_name)
        if not formatter:
            raise FormatterError(
                f"未找到格式化器: {format_name}",
                formatter_name=format_name,
                format_type="unknown"
            )
        
        return formatter.format(data, **kwargs)
    
    def parse_data(
        self,
        content: str,
        format_name: str,
        **kwargs
    ) -> Any:
        """解析格式化的数据"""
        
        formatter = self.get_formatter(format_name)
        if not formatter:
            raise FormatterError(
                f"未找到格式化器: {format_name}",
                formatter_name=format_name,
                format_type="unknown"
            )
        
        return formatter.parse(content, **kwargs)
    
    def _register_builtin_formatters(self) -> None:
        """注册内置格式化器"""
        
        # JSON格式化器
        json_formatter = JSONFormatter()
        self.register_formatter("json", json_formatter, [
            "application/json",
            "text/json"
        ])
        
        # XML格式化器
        xml_formatter = XMLFormatter()
        self.register_formatter("xml", xml_formatter, [
            "application/xml",
            "text/xml"
        ])
        
        # CSV格式化器
        csv_formatter = CSVFormatter()
        self.register_formatter("csv", csv_formatter, [
            "text/csv",
            "application/csv"
        ])


# 全局格式化器注册表实例
formatter_registry = FormatterRegistry()


# 便捷函数

def format_as_json(data: Any, **kwargs) -> str:
    """格式化为JSON"""
    return formatter_registry.format_data(data, "json", **kwargs)


def format_as_xml(data: Any, **kwargs) -> str:
    """格式化为XML"""
    return formatter_registry.format_data(data, "xml", **kwargs)


def format_as_csv(data: Any, **kwargs) -> str:
    """格式化为CSV"""
    return formatter_registry.format_data(data, "csv", **kwargs)


def parse_json(content: str, **kwargs) -> Any:
    """解析JSON"""
    return formatter_registry.parse_data(content, "json", **kwargs)


def parse_xml(content: str, **kwargs) -> Any:
    """解析XML"""
    return formatter_registry.parse_data(content, "xml", **kwargs)


def parse_csv(content: str, **kwargs) -> Any:
    """解析CSV"""
    return formatter_registry.parse_data(content, "csv", **kwargs) 
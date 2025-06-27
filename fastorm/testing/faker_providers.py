"""
FastORM Faker集成

提供丰富的假数据生成功能，包括中文数据和企业级数据。

示例:
```python
from fastorm.testing import faker

# 基础使用
name = faker.name()
email = faker.email()

# 中文数据
chinese_name = faker.chinese_name()
chinese_phone = faker.chinese_phone()

# 企业数据
company_email = faker.company_email()
department = faker.department()
```
"""

from __future__ import annotations

import random
import string
from datetime import datetime
from datetime import timedelta

from faker import Faker
from faker.providers import BaseProvider


class ChineseProvider(BaseProvider):
    """中文数据提供者"""

    # 中文姓氏
    chinese_surnames = [
        "王",
        "李",
        "张",
        "刘",
        "陈",
        "杨",
        "赵",
        "黄",
        "周",
        "吴",
        "徐",
        "孙",
        "胡",
        "朱",
        "高",
        "林",
        "何",
        "郭",
        "马",
        "罗",
        "梁",
        "宋",
        "郑",
        "谢",
        "韩",
        "唐",
        "冯",
        "于",
        "董",
        "萧",
    ]

    # 中文名字
    chinese_given_names = [
        "伟",
        "芳",
        "娜",
        "敏",
        "静",
        "丽",
        "强",
        "磊",
        "军",
        "洋",
        "勇",
        "艳",
        "杰",
        "娟",
        "涛",
        "明",
        "超",
        "秀英",
        "霞",
        "平",
        "刚",
        "桂英",
        "华",
        "建华",
        "建国",
        "志强",
        "志明",
        "秀兰",
        "秀珍",
        "春梅",
        "玉兰",
        "玉梅",
        "桂芳",
        "秀芳",
        "丽娟",
        "丽华",
    ]

    # 中国城市
    chinese_cities = [
        "北京",
        "上海",
        "广州",
        "深圳",
        "杭州",
        "南京",
        "武汉",
        "成都",
        "西安",
        "重庆",
        "天津",
        "苏州",
        "长沙",
        "郑州",
        "青岛",
        "大连",
        "宁波",
        "厦门",
        "福州",
        "无锡",
        "合肥",
        "昆明",
        "哈尔滨",
        "济南",
        "佛山",
        "长春",
        "温州",
        "石家庄",
        "南宁",
        "常州",
        "泉州",
        "南昌",
    ]

    # 中国省份
    chinese_provinces = [
        "北京市",
        "天津市",
        "河北省",
        "山西省",
        "内蒙古",
        "辽宁省",
        "吉林省",
        "黑龙江省",
        "上海市",
        "江苏省",
        "浙江省",
        "安徽省",
        "福建省",
        "江西省",
        "山东省",
        "河南省",
        "湖北省",
        "湖南省",
        "广东省",
        "广西省",
        "海南省",
        "重庆市",
        "四川省",
        "贵州省",
        "云南省",
        "西藏",
        "陕西省",
        "甘肃省",
        "青海省",
        "宁夏",
        "新疆",
    ]

    def chinese_name(self) -> str:
        """生成中文姓名"""
        surname = self.random_element(self.chinese_surnames)
        given_name = self.random_element(self.chinese_given_names)
        return f"{surname}{given_name}"

    def chinese_phone(self) -> str:
        """生成中国手机号"""
        prefixes = [
            "130",
            "131",
            "132",
            "133",
            "134",
            "135",
            "136",
            "137",
            "138",
            "139",
            "150",
            "151",
            "152",
            "153",
            "155",
            "156",
            "157",
            "158",
            "159",
            "180",
            "181",
            "182",
            "183",
            "184",
            "185",
            "186",
            "187",
            "188",
            "189",
        ]
        prefix = self.random_element(prefixes)
        suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return f"{prefix}{suffix}"

    def chinese_id_number(self) -> str:
        """生成中国身份证号"""
        # 简化版本，仅用于测试
        area_code = random.randint(100000, 999999)
        birth_date = self.generator.date_between(
            start_date="-80y", end_date="-18y"
        ).strftime("%Y%m%d")
        sequence = random.randint(100, 999)

        # 简单的校验码计算（不完全准确，仅用于测试）
        check_digit = random.randint(0, 9)
        if check_digit == 10:
            check_digit = "X"

        return f"{area_code}{birth_date}{sequence}{check_digit}"

    def chinese_address(self) -> str:
        """生成中国地址"""
        province = self.random_element(self.chinese_provinces)
        city = self.random_element(self.chinese_cities)
        district = f"{self.random_element(['东', '西', '南', '北', '中'])}区"
        street = f"{self.random_element(['建设', '人民', '中山', '解放', '和平'])}路"
        number = random.randint(1, 999)
        return f"{province}{city}{district}{street}{number}号"

    def chinese_company(self) -> str:
        """生成中国公司名"""
        prefixes = ["北京", "上海", "深圳", "广州", "杭州", "成都"]
        types = ["科技", "信息", "网络", "软件", "电子", "智能"]
        suffixes = ["有限公司", "股份有限公司", "科技有限公司"]

        prefix = self.random_element(prefixes)
        middle = self.random_element(types)
        suffix = self.random_element(suffixes)

        return f"{prefix}{middle}{suffix}"


class CompanyProvider(BaseProvider):
    """企业级数据提供者"""

    # 部门名称
    departments = [
        "技术部",
        "产品部",
        "市场部",
        "销售部",
        "运营部",
        "人力资源部",
        "财务部",
        "法务部",
        "行政部",
        "客服部",
        "设计部",
        "测试部",
        "运维部",
        "数据部",
        "业务部",
        "项目部",
        "质量部",
        "采购部",
    ]

    # 职位名称
    positions = [
        "软件工程师",
        "高级软件工程师",
        "架构师",
        "技术经理",
        "技术总监",
        "产品经理",
        "高级产品经理",
        "产品总监",
        "项目经理",
        "运营经理",
        "市场经理",
        "销售经理",
        "人力资源经理",
        "财务经理",
        "UI设计师",
        "测试工程师",
        "运维工程师",
        "数据分析师",
        "业务分析师",
    ]

    # 技能标签
    skills = [
        "Python",
        "Java",
        "JavaScript",
        "React",
        "Vue",
        "Node.js",
        "Docker",
        "Kubernetes",
        "AWS",
        "Azure",
        "MySQL",
        "PostgreSQL",
        "Redis",
        "MongoDB",
        "Git",
        "Jenkins",
        "Linux",
        "Nginx",
    ]

    def department(self) -> str:
        """生成部门名称"""
        return self.random_element(self.departments)

    def position(self) -> str:
        """生成职位名称"""
        return self.random_element(self.positions)

    def skill_set(self, count: int = 3) -> list[str]:
        """生成技能集合"""
        return self.random_elements(self.skills, length=count, unique=True)

    def company_email(self, name: str | None = None) -> str:
        """生成企业邮箱"""
        if not name:
            name = self.generator.first_name().lower()

        domains = [
            "company.com",
            "corp.com",
            "tech.com",
            "group.com",
            "ltd.com",
            "inc.com",
            "enterprise.com",
        ]
        domain = self.random_element(domains)
        return f"{name}@{domain}"

    def employee_id(self) -> str:
        """生成员工ID"""
        prefix = self.random_element(["EMP", "STF", "USR"])
        number = random.randint(10000, 99999)
        return f"{prefix}{number}"

    def project_name(self) -> str:
        """生成项目名称"""
        prefixes = ["智能", "云端", "移动", "数字", "在线", "统一"]
        types = ["管理系统", "平台", "服务", "解决方案", "工具", "框架"]

        prefix = self.random_element(prefixes)
        type_name = self.random_element(types)
        return f"{prefix}{type_name}"

    def version_number(self) -> str:
        """生成版本号"""
        major = random.randint(1, 5)
        minor = random.randint(0, 9)
        patch = random.randint(0, 99)
        return f"{major}.{minor}.{patch}"


class TestDataProvider(BaseProvider):
    """测试数据提供者"""

    def test_email(self, domain: str = "test.com") -> str:
        """生成测试邮箱"""
        username = self.generator.user_name()
        return f"{username}@{domain}"

    def test_phone(self, country_code: str = "+86") -> str:
        """生成测试电话"""
        number = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return f"{country_code}138{number}"

    def test_url(self, scheme: str = "https") -> str:
        """生成测试URL"""
        domain = self.generator.domain_name()
        path = self.generator.uri_path()
        return f"{scheme}://{domain}/{path}"

    def api_key(self, length: int = 32) -> str:
        """生成API密钥"""
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    def jwt_token(self) -> str:
        """生成模拟JWT令牌"""
        header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

        # 生成模拟payload（base64编码）
        import base64
        import json

        payload_data = {
            "user_id": random.randint(1, 9999),
            "exp": int((datetime.now() + timedelta(hours=24)).timestamp()),
        }
        payload = (
            base64.b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
        )

        # 生成模拟签名
        signature = "".join(
            random.choice(string.ascii_letters + string.digits + "-_")
            for _ in range(43)
        )

        return f"{header}.{payload}.{signature}"

    def status_code(self) -> int:
        """生成HTTP状态码"""
        codes = [200, 201, 400, 401, 403, 404, 500, 502, 503]
        return self.random_element(codes)

    def boolean_string(self) -> str:
        """生成布尔字符串"""
        return self.random_element(["true", "false", "True", "False", "1", "0"])


# 创建全局faker实例并注册提供者
faker = Faker(["zh_CN", "en_US"])
faker.add_provider(ChineseProvider)
faker.add_provider(CompanyProvider)
faker.add_provider(TestDataProvider)


# 便捷函数
def chinese_name() -> str:
    """生成中文姓名"""
    return faker.chinese_name()


def chinese_phone() -> str:
    """生成中国手机号"""
    return faker.chinese_phone()


def company_email(name: str | None = None) -> str:
    """生成企业邮箱"""
    return faker.company_email(name)


def department() -> str:
    """生成部门名称"""
    return faker.department()


def employee_id() -> str:
    """生成员工ID"""
    return faker.employee_id()


def api_key(length: int = 32) -> str:
    """生成API密钥"""
    return faker.api_key(length)

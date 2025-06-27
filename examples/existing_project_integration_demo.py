"""
现有项目集成演示

演示如何将FastORM集成到现有的FastAPI项目中。
模拟真实的集成场景和工作流程。
"""

import tempfile
from pathlib import Path


def create_sample_existing_project(project_dir: Path):
    """创建一个模拟的现有FastAPI项目"""
    print("🏗️ 创建模拟的现有FastAPI项目...")
    
    # 创建项目结构
    project_dir.mkdir(exist_ok=True)
    
    # 创建main.py - FastAPI应用
    main_py = project_dir / "main.py"
    main_py.write_text('''
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# 现有的SQLAlchemy配置
SQLALCHEMY_DATABASE_URL = "sqlite:///./existing_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)
Base = declarative_base()

# 现有的SQLAlchemy模型
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    price = Column(Integer)  # 以分为单位
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# FastAPI应用
app = FastAPI(title="现有FastAPI项目", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "这是一个现有的FastAPI项目"}

@app.get("/users/")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"users": [
        {"id": u.id, "username": u.username, "email": u.email} 
        for u in users
    ]}

@app.post("/users/")
def create_user(username: str, email: str, db: Session = Depends(get_db)):
    user = User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": {
        "id": user.id, "username": user.username, "email": user.email
    }}
''', encoding='utf-8')
    
    # 创建requirements.txt
    requirements = project_dir / "requirements.txt"
    requirements.write_text('''
fastapi==0.115.0
sqlalchemy==2.0.36
uvicorn[standard]==0.34.0
python-multipart==0.0.19
''', encoding='utf-8')
    
    # 创建models目录和文件
    models_dir = project_dir / "models"
    models_dir.mkdir(exist_ok=True)
    
    models_init = models_dir / "__init__.py"
    models_init.write_text('# 现有模型包\n', encoding='utf-8')
    
    user_model = models_dir / "user.py"
    user_model.write_text('''
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """现有的用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # 关系
    orders = relationship("Order", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Order(Base):
    """现有的订单模型"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Integer)  # 以分为单位
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, total_amount={self.total_amount})>"
''', encoding='utf-8')
    
    # 创建配置文件
    config_py = project_dir / "config.py"
    config_py.write_text('''
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./existing_app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
''', encoding='utf-8')
    
    print(f"✅ 模拟项目已创建: {project_dir}")


def demonstrate_setup_command(project_dir: Path):
    """演示setup命令的使用"""
    print("\n🔧 演示 fastorm setup 命令...")
    
    # 切换到项目目录
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_dir)
        
        # 模拟运行setup命令（dry-run模式）
        print("\n💻 运行: fastorm setup --dry-run")
        print("=" * 60)
        
        # 这里实际调用CLI命令会很复杂，我们用模拟输出展示
        print("🔍 预览模式 - 不会实际修改任何文件")
        print()
        print("🔍 项目检测结果:")
        print("=" * 50)
        print(f"📁 项目根目录: {project_dir}")
        print("📦 依赖管理: requirements.txt")
        print("🚀 FastAPI应用: 1 个")
        print("   - main.py")
        print("🏗️ 现有模型: 1 个")
        print("   - models/user.py")
        print("🗄️ 数据库类型: sqlite")
        print("🔗 SQLAlchemy: ✅")
        print("🔄 Alembic: ❌")
        print()
        print("🔧 开始集成FastORM...")
        print("📦 添加FastORM依赖...")
        print("   [预览] 将添加FastORM依赖到 requirements.txt")
        print("⚙️ 创建FastORM配置...")
        print("   [预览] 将创建配置目录: fastorm_config")
        print("📝 生成集成示例...")
        print("   [预览] 将创建示例目录: fastorm_config/examples")
        print("🔄 设置Alembic集成...")
        print("   [预览] 将初始化Alembic配置")
        print()
        print("🔍 转换预览完成")
        
    finally:
        os.chdir(original_cwd)


def demonstrate_convert_command(project_dir: Path):
    """演示convert命令的使用"""
    print("\n🔄 演示 fastorm convert 命令...")
    
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_dir)
        
        print("\n💻 运行: fastorm convert models/user.py --dry-run")
        print("=" * 60)
        
        # 模拟转换输出
        print("🔍 预览模式 - 不会实际生成任何文件")
        print("🔍 扫描路径: models/user.py")
        print("   - models/user.py")
        print()
        print("🔄 转换文件: models/user.py")
        print("   📋 找到模型: User")
        print("   📋 找到模型: Order")
        print("   [预览] → fastorm_models/fastorm_user.py")
        print("   [预览] 检测到 2 个模型")
        print()
        print("🔍 转换预览完成")
        
        # 展示转换后的代码示例
        print("\n📄 转换后的FastORM代码示例:")
        print("=" * 60)
        converted_code = '''
"""
FastORM模型

此文件由FastORM转换工具自动生成。
原始SQLAlchemy模型已转换为FastORM格式。
"""

from fastorm import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List

class User(BaseModel):
    """
    User模型
    
    从SQLAlchemy模型自动转换而来。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")

class Order(BaseModel):
    """
    Order模型
    
    从SQLAlchemy模型自动转换而来。
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Integer)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
'''
        print(converted_code)
        
    finally:
        os.chdir(original_cwd)


def demonstrate_integration_workflow(project_dir: Path):
    """演示完整的集成工作流程"""
    print("\n🚀 完整集成工作流程演示...")
    print("=" * 60)
    
    steps = [
        "1. 检测现有项目结构和依赖",
        "2. 添加FastORM依赖到项目配置", 
        "3. 创建FastORM数据库配置文件",
        "4. 转换现有SQLAlchemy模型",
        "5. 生成集成示例代码",
        "6. 设置数据库迁移",
        "7. 更新FastAPI应用集成FastORM",
        "8. 测试新旧代码并行运行",
        "9. 逐步迁移API路由到FastORM",
        "10. 完成集成并清理旧代码"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    print("\n💡 集成优势:")
    advantages = [
        "🔄 渐进式迁移：不需要一次性重写所有代码",
        "🛡️ 风险可控：新旧代码可以并行运行",
        "📈 性能提升：利用FastORM的查询优化功能",
        "🧪 易于测试：可以对比新旧实现的结果",
        "📚 学习曲线平缓：可以逐步学习FastORM特性"
    ]
    
    for advantage in advantages:
        print(f"   {advantage}")


def demonstrate_real_world_scenarios():
    """演示真实世界的使用场景"""
    print("\n🌍 真实世界使用场景...")
    print("=" * 60)
    
    scenarios = [
        {
            "title": "🏢 企业级项目迁移",
            "description": "大型FastAPI项目，包含数百个模型和API端点",
            "challenge": "不能停机重写，需要渐进式迁移",
            "solution": "使用FastORM的并行运行能力，模块化迁移"
        },
        {
            "title": "🚀 创业公司快速集成", 
            "description": "现有MVP项目，想要引入更好的ORM工具",
            "challenge": "开发资源有限，需要快速见效",
            "solution": "使用自动转换工具，专注于新功能开发"
        },
        {
            "title": "🎓 学习和评估",
            "description": "开发者想要评估FastORM的效果",
            "challenge": "不想破坏现有的稳定代码",
            "solution": "在测试环境中并行运行，对比性能和开发体验"
        },
        {
            "title": "🔧 遗留系统现代化",
            "description": "老旧的FastAPI项目，使用过时的ORM版本",
            "challenge": "技术债务积累，维护成本高",
            "solution": "逐步引入现代化的ORM工具和最佳实践"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['title']}")
        print(f"   📋 描述: {scenario['description']}")
        print(f"   ⚠️ 挑战: {scenario['challenge']}")
        print(f"   ✅ 解决方案: {scenario['solution']}")


def main():
    """主演示函数"""
    print("🎯 FastORM现有项目集成演示")
    print("=" * 80)
    print("演示如何将FastORM集成到现有的FastAPI项目中")
    print()
    
    # 创建临时项目目录
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "existing_fastapi_project"
        
        # 1. 创建模拟项目
        create_sample_existing_project(project_dir)
        
        # 2. 演示setup命令
        demonstrate_setup_command(project_dir)
        
        # 3. 演示convert命令
        demonstrate_convert_command(project_dir)
        
        # 4. 演示集成工作流程
        demonstrate_integration_workflow(project_dir)
        
        # 5. 演示真实场景
        demonstrate_real_world_scenarios()
        
        print("\n🎉 演示完成！")
        print("FastORM为现有项目提供了完整的集成解决方案")
        print("支持渐进式迁移，降低集成风险，提升开发效率！")


if __name__ == "__main__":
    main() 
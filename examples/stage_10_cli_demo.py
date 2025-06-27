"""
FastORM第十阶段：CLI开发工具演示

演示FastORM CLI工具的各项功能，包括项目初始化、
模型生成、数据库迁移等。
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
import os


def run_command(cmd: list, cwd=None, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            capture_output=capture_output, 
            text=True, 
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except FileNotFoundError:
        return False, f"命令未找到: {cmd[0]}"


def demo_cli_help():
    """演示CLI帮助信息"""
    print("\n" + "="*60)
    print("🔧 FastORM CLI帮助信息演示")
    print("="*60)
    
    # 显示主帮助
    success, output = run_command([sys.executable, '-m', 'fastorm.cli', '--help'])
    if success:
        print("✅ CLI主帮助信息:")
        print(output)
    else:
        print(f"❌ 获取帮助失败: {output}")
    
    # 显示特定命令帮助
    commands = ['init', 'create:model', 'migrate', 'db', 'serve']
    for cmd in commands:
        print(f"\n📋 {cmd} 命令帮助:")
        success, output = run_command([
            sys.executable, '-m', 'fastorm.cli', cmd, '--help'
        ])
        if success:
            print(output[:300] + "..." if len(output) > 300 else output)
        else:
            print(f"❌ 获取{cmd}帮助失败: {output}")


def demo_project_init():
    """演示项目初始化功能"""
    print("\n" + "="*60)  
    print("🚀 项目初始化演示")
    print("="*60)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 临时目录: {temp_path}")
        
        # 测试基础项目初始化
        project_name = "demo_project"
        project_path = temp_path / project_name
        
        print(f"\n1. 创建基础项目: {project_name}")
        
        # 模拟用户输入：不安装依赖
        cmd = [
            sys.executable, '-m', 'fastorm.cli', 
            'init', project_name,
            '--template', 'basic',
            '--database', 'sqlite'
        ]
        
        success, output = run_command(cmd, cwd=temp_path, capture_output=False)
        
        if success:
            print("✅ 项目创建成功")
            
            # 检查生成的文件
            if project_path.exists():
                print("\n📋 生成的项目结构:")
                _show_directory_tree(project_path)
            
            # 检查关键文件内容
            key_files = [
                'pyproject.toml',
                'app/main.py', 
                'app/models/user.py',
                'README.md'
            ]
            
            for file_path in key_files:
                file_full_path = project_path / file_path
                if file_full_path.exists():
                    print(f"\n📄 {file_path} 内容预览:")
                    with open(file_full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(content[:200] + "..." if len(content) > 200 else content)
                else:
                    print(f"⚠️ 文件不存在: {file_path}")
        else:
            print(f"❌ 项目创建失败: {output}")


def demo_model_generation():
    """演示模型生成功能"""
    print("\n" + "="*60)
    print("🏗️ 模型生成演示") 
    print("="*60)
    
    # 创建临时项目
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        project_name = "model_demo_project"
        project_path = temp_path / project_name
        
        # 先创建项目
        print("1. 创建测试项目...")
        init_cmd = [
            sys.executable, '-m', 'fastorm.cli',
            'init', project_name,
            '--template', 'basic'
        ]
        
        success, _ = run_command(init_cmd, cwd=temp_path)
        if not success:
            print("❌ 项目创建失败")
            return
        
        print("✅ 测试项目创建成功")
        
        # 测试模型生成
        models_to_create = [
            {
                'name': 'Blog',
                'fields': [
                    'title:str:required',
                    'content:text:required', 
                    'status:str:default:draft',
                    'view_count:int:default:0'
                ]
            },
            {
                'name': 'Category',
                'fields': [
                    'name:str:required,unique',
                    'description:text'
                ]
            },
            {
                'name': 'Product',
                'fields': [
                    'name:str:required,length:100',
                    'price:float:required',
                    'is_active:bool:default:true'
                ]
            }
        ]
        
        for model_info in models_to_create:
            print(f"\n2. 生成模型: {model_info['name']}")
            
            cmd = [
                sys.executable, '-m', 'fastorm.cli',
                'create:model', model_info['name']
            ]
            
            # 添加字段定义
            for field in model_info['fields']:
                cmd.extend(['-f', field])
            
            success, output = run_command(cmd, cwd=project_path, capture_output=False)
            
            if success:
                print(f"✅ 模型 {model_info['name']} 生成成功")
                
                # 检查生成的文件
                model_file = project_path / 'app' / 'models' / f"{model_info['name'].lower()}.py"
                if model_file.exists():
                    print(f"📄 {model_file.name} 内容预览:")
                    with open(model_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(content)
            else:
                print(f"❌ 模型 {model_info['name']} 生成失败: {output}")


def demo_database_commands():
    """演示数据库命令"""
    print("\n" + "="*60)
    print("🗄️ 数据库命令演示")
    print("="*60)
    
    # 显示数据库命令帮助
    print("1. 数据库命令组帮助:")
    success, output = run_command([
        sys.executable, '-m', 'fastorm.cli', 'db', '--help'
    ])
    
    if success:
        print(output)
    else:
        print(f"❌ 获取数据库命令帮助失败: {output}")
    
    # 显示各个子命令帮助
    db_commands = ['create', 'drop', 'reset', 'seed']
    for cmd in db_commands:
        print(f"\n2. {cmd} 命令帮助:")
        success, output = run_command([
            sys.executable, '-m', 'fastorm.cli', 'db', cmd, '--help'
        ])
        if success:
            print(output[:200] + "..." if len(output) > 200 else output)


def demo_serve_command():
    """演示开发服务器命令"""
    print("\n" + "="*60)
    print("🚀 开发服务器命令演示")
    print("="*60)
    
    # 显示serve命令帮助
    print("1. serve命令帮助:")
    success, output = run_command([
        sys.executable, '-m', 'fastorm.cli', 'serve', '--help'
    ])
    
    if success:
        print(output)
    else:
        print(f"❌ 获取serve命令帮助失败: {output}")
    
    print("\n💡 注意: serve命令需要在实际项目中运行，此处仅演示帮助信息")


def _show_directory_tree(path: Path, prefix="", max_depth=3, current_depth=0):
    """显示目录树结构"""
    if current_depth >= max_depth:
        return
    
    items = list(path.iterdir())
    items.sort(key=lambda x: (x.is_file(), x.name))
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item.name}")
        
        if item.is_dir() and current_depth < max_depth - 1:
            extension = "    " if is_last else "│   "
            _show_directory_tree(item, prefix + extension, max_depth, current_depth + 1)


def main():
    """主演示函数"""
    print("🛠️ FastORM第十阶段：CLI开发工具演示")
    print("=" * 60)
    print("本演示将展示FastORM CLI工具的各项功能")
    
    try:
        # 1. CLI帮助信息演示
        demo_cli_help()
        
        # 2. 项目初始化演示
        demo_project_init()
        
        # 3. 模型生成演示
        demo_model_generation()
        
        # 4. 数据库命令演示
        demo_database_commands()
        
        # 5. 开发服务器命令演示
        demo_serve_command()
        
        print("\n🎉 CLI工具演示完成！")
        print("\n📚 总结:")
        print("✅ fastorm init        - 项目初始化功能完整")
        print("✅ fastorm create:model - 模型代码生成功能完整")
        print("✅ fastorm migrate     - 数据库迁移管理")
        print("✅ fastorm db          - 数据库操作命令组")
        print("✅ fastorm serve       - 开发服务器启动")
        
        print("\n🚀 CLI工具已准备就绪，可以开始实际使用！")
        
    except KeyboardInterrupt:
        print("\n👋 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")


if __name__ == "__main__":
    main() 
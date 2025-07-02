"""
测试 HasMany 一对多关系的高级功能
"""

import pytest
from uuid import uuid4
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession

from fastorm.model.model import Model
from fastorm.relations.has_many import HasMany

# 使用唯一前缀避免表名冲突
test_prefix = f"hma_{uuid4().hex[:8]}_"


class Author(Model):
    __tablename__ = f'{test_prefix}authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    
    # 一对多关系：作者拥有多本书
    books = HasMany('Book', foreign_key='author_id')


class Book(Model):
    __tablename__ = f'{test_prefix}books'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    author_id = Column(Integer, ForeignKey(f'{test_prefix}authors.id'))


class TestHasManyAdvanced:
    """测试HasMany一对多关系的高级功能"""

    @pytest.fixture
    async def setup_author_data(self, test_session: AsyncSession):
        """准备作者测试数据"""
        # 使用随机ID避免冲突
        author_id = 10000 + (int(uuid4().int) % 5000)  # 10000-14999范围
        author = Author(
            id=author_id,
            name=f"test_author_{uuid4().hex[:8]}"
        )
        test_session.add(author)
        await test_session.commit()
        return author

    async def test_has_many_load(self, setup_author_data, test_session: AsyncSession):
        """测试一对多关系加载"""
        author = setup_author_data
        
        # 创建关联的书籍
        book1 = Book(id=4001, title=f"book1_{uuid4().hex[:8]}", author_id=author.id)
        book2 = Book(id=4002, title=f"book2_{uuid4().hex[:8]}", author_id=author.id)
        
        test_session.add_all([book1, book2])
        await test_session.commit()
        
        # 加载关联的书籍
        books = await author.books.load(author, test_session)
        
        assert len(books) == 2
        book_titles = [book.title for book in books]
        assert book1.title in book_titles
        assert book2.title in book_titles

    async def test_foreign_key_auto_generation(self, setup_author_data):
        """测试外键名自动生成"""
        author = setup_author_data
        
        # 创建不指定foreign_key的关系
        auto_books = HasMany('Book')
        foreign_key = auto_books.get_foreign_key(author)
        
        assert foreign_key == "author_id"

    async def test_custom_foreign_key(self, setup_author_data):
        """测试自定义外键"""
        author = setup_author_data
        
        custom_books = HasMany('Book', foreign_key='writer_id')
        foreign_key = custom_books.get_foreign_key(author)
        
        assert foreign_key == "writer_id"

    async def test_create_operation_config(self, setup_author_data):
        """测试create操作的配置"""
        author = setup_author_data
        
        # 验证create操作的配置逻辑
        foreign_key = author.books.get_foreign_key(author)
        local_key_value = author.books.get_local_key_value(author)
        
        # 模拟create操作的属性设置
        attributes = {'title': 'New Book', 'isbn': '123456789'}
        attributes[foreign_key] = local_key_value
        
        assert foreign_key == 'author_id'
        assert local_key_value == author.id
        assert attributes['author_id'] == author.id
        assert attributes['title'] == 'New Book'

    async def test_save_operation_config(self, setup_author_data):
        """测试save操作的配置"""
        author = setup_author_data
        
        # 创建要保存的书籍实例
        book = Book(title=f"save_book_{uuid4().hex[:8]}")
        
        # 验证save操作的配置逻辑
        foreign_key = author.books.get_foreign_key(author)
        local_key_value = author.books.get_local_key_value(author)
        
        # 模拟设置外键值
        setattr(book, foreign_key, local_key_value)
        
        assert getattr(book, foreign_key) == author.id
        assert book.title.startswith("save_book_")

    async def test_save_many_operation_config(self, setup_author_data):
        """测试save_many操作的配置"""
        author = setup_author_data
        
        # 创建多个要保存的书籍实例
        books = [
            Book(title=f"batch_book_1_{uuid4().hex[:8]}"),
            Book(title=f"batch_book_2_{uuid4().hex[:8]}"),
            Book(title=f"batch_book_3_{uuid4().hex[:8]}")
        ]
        
        # 验证批量保存的配置逻辑
        foreign_key = author.books.get_foreign_key(author)
        local_key_value = author.books.get_local_key_value(author)
        
        # 模拟为每个实例设置外键
        for book in books:
            setattr(book, foreign_key, local_key_value)
        
        assert all(getattr(book, foreign_key) == author.id for book in books)
        assert len(books) == 3

    async def test_create_many_operation_config(self, setup_author_data):
        """测试create_many操作的配置"""
        author = setup_author_data
        
        # 创建批量记录数据
        records = [
            {'title': f'batch_title_1_{uuid4().hex[:8]}', 'isbn': '111'},
            {'title': f'batch_title_2_{uuid4().hex[:8]}', 'isbn': '222'},
            {'title': f'batch_title_3_{uuid4().hex[:8]}', 'isbn': '333'}
        ]
        
        # 验证批量创建的配置逻辑
        foreign_key = author.books.get_foreign_key(author)
        local_key_value = author.books.get_local_key_value(author)
        
        # 模拟为每条记录设置外键
        for record in records:
            record[foreign_key] = local_key_value
        
        assert all(record[foreign_key] == author.id for record in records)
        assert len(records) == 3
        assert all('batch_title_' in record['title'] for record in records)

    async def test_delete_all_operation_config(self, setup_author_data):
        """测试delete_all操作的配置"""
        author = setup_author_data
        
        # 验证删除所有关联记录的配置
        foreign_key = author.books.get_foreign_key(author)
        local_key_value = author.books.get_local_key_value(author)
        
        # 模拟构建删除条件
        delete_condition = f"{foreign_key} = {local_key_value}"
        
        assert foreign_key in delete_condition
        assert str(local_key_value) in delete_condition
        assert f"author_id = {author.id}" == delete_condition

    async def test_count_operation_config(self, setup_author_data):
        """测试count操作的配置"""
        author = setup_author_data
        
        # 验证计数操作的配置
        foreign_key = author.books.get_foreign_key(author)
        local_key_value = author.books.get_local_key_value(author)
        
        # 模拟构建计数查询条件
        count_condition = f"{foreign_key} = {local_key_value}"
        
        assert foreign_key in count_condition
        assert str(local_key_value) in count_condition

    async def test_load_empty_when_no_local_key(self, test_session: AsyncSession):
        """测试当本地键值为空时返回空列表"""
        author = Author(name="test_author")  # 没有ID
        books = await author.books.load(author, test_session)
        assert books == []

    async def test_has_many_relationship_configuration(self, setup_author_data):
        """测试HasMany关系的完整配置"""
        author = setup_author_data
        
        # 验证关系配置
        assert author.books.model_class.__name__ == 'Book'
        assert author.books.foreign_key == 'author_id'
        assert author.books.local_key == 'id'

    async def test_custom_local_key_configuration(self):
        """测试自定义本地键配置"""
        custom_books = HasMany(
            'Book',
            foreign_key='writer_uuid',
            local_key='uuid'
        )
        
        assert custom_books.foreign_key == 'writer_uuid'
        assert custom_books.local_key == 'uuid'

    async def test_relationship_with_different_model_types(self):
        """测试与不同模型类型的关系"""
        # 测试字符串模型类型
        string_books = HasMany('Book')
        # model_class属性会解析字符串为实际的类对象
        assert string_books.model_class == Book
        
        # 测试类模型类型
        class_books = HasMany(Book)
        assert class_books.model_class == Book

    async def test_load_with_existing_books(self, setup_author_data, test_session: AsyncSession):
        """测试加载已存在的书籍"""
        author = setup_author_data
        
        # 先创建一些书籍
        existing_books = [
            Book(title=f"existing_1_{uuid4().hex[:8]}", author_id=author.id),
            Book(title=f"existing_2_{uuid4().hex[:8]}", author_id=author.id),
            Book(title=f"existing_3_{uuid4().hex[:8]}", author_id=author.id)
        ]
        
        test_session.add_all(existing_books)
        await test_session.commit()
        
        # 加载关联的书籍
        loaded_books = await author.books.load(author, test_session)
        
        assert len(loaded_books) == 3
        loaded_titles = [book.title for book in loaded_books]
        for book in existing_books:
            assert book.title in loaded_titles

    async def test_local_key_value_retrieval(self, setup_author_data):
        """测试本地键值获取"""
        author = setup_author_data
        
        local_key_value = author.books.get_local_key_value(author)
        assert local_key_value == author.id
        
        # 测试没有ID的情况
        author_no_id = Author(name="no_id_author")
        local_key_value_none = author.books.get_local_key_value(author_no_id)
        assert local_key_value_none is None

    async def test_has_many_type_annotations(self):
        """测试HasMany类型注解"""
        books_relation = HasMany('Book')
        
        # 验证返回类型是列表
        assert hasattr(books_relation, 'load')
        # 这里我们无法直接测试类型注解，但可以验证方法存在 
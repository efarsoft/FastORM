from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Type, Callable, Any, Optional, List, Dict
from fastorm import Model


def get_primary_key_name(model: Type[Model]) -> str:
    """自动识别主键字段名，支持自定义主键"""
    for attr in dir(model):
        field = getattr(model, attr, None)
        if hasattr(field, "property") and hasattr(field.property, "columns"):
            for column in field.property.columns:
                if getattr(column, "primary_key", False):
                    return attr
    return "id"


def get_model_fields(model):
    return {c.name for c in model.__table__.columns}


def get_field_type(model, field):
    return model.__table__.columns[field].type.python_type


def get_model_relations(model):
    return {rel for rel in dir(model) if hasattr(getattr(model, rel), 'model_class')}


def create_crud_router(
    model: Type[Model],
    schema: Any = None,
    create_schema: Any = None,
    prefix: str = "",
    tags: Optional[List[str]] = None,
    page_size: int = 20,
    permission_dependency: Optional[Callable[..., Any]] = None,
    enable_batch: bool = True,
    enable_soft_delete: bool = True,
    enable_with_rel: bool = True,
) -> APIRouter:
    """
    FastORM官方增强版CRUD API自动生成器
    - 自动识别主键
    - 支持分页、批量、软删除、关系预加载
    - 可选权限钩子
    - 支持灵活API查询参数与QueryBuilder深度结合
    """
    router = APIRouter(prefix=prefix or f"/{model.__tablename__}", tags=tags or [model.__name__])

    Schema = schema or model.get_pydantic_schema()
    CreateSchema = create_schema or model.get_pydantic_schema(for_create=True)
    pk_name = get_primary_key_name(model)
    permission = permission_dependency or (lambda: None)
    model_fields = get_model_fields(model)
    relation_fields = get_model_relations(model)

    # ========== 基础CRUD ==========
    @router.post("/", response_model=Schema)
    async def create(data: CreateSchema, _=Depends(permission)) -> Any:
        obj = await model.create(**data.model_dump())
        return obj.to_pydantic()

    @router.get("/", response_model=Dict)
    async def list_all(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(page_size, ge=1, le=100, description="每页数量"),
        where: Optional[str] = Query(None, description="精确筛选，field:value,field2:value2"),
        order_by: Optional[str] = Query(None, description="排序，field:asc,field2:desc"),
        limit: Optional[int] = Query(None),
        offset: Optional[int] = Query(None),
        with_rel: Optional[str] = Query(None, description="逗号分隔的关系名"),
        search: Optional[str] = Query(None, description="模糊搜索，field:value或全局"),
        range_: Optional[str] = Query(None, alias="range", description="范围筛选，field:start-end"),
        only_trashed: bool = Query(False, description="仅查询已删除"),
        _=Depends(permission),
    ) -> dict:
        query = model.query()
        # 1. where
        if where:
            for cond in where.split(","):
                if ":" in cond:
                    field, value = cond.split(":", 1)
                    if field not in model_fields:
                        raise HTTPException(status_code=400, detail=f"非法字段: {field}")
                    py_type = get_field_type(model, field)
                    try:
                        value = py_type(value)
                    except Exception:
                        raise HTTPException(status_code=400, detail=f"{field}类型错误")
                    query = query.where(field, value)
        # 2. order_by
        if order_by:
            for cond in order_by.split(","):
                if ":" in cond:
                    field, direction = cond.split(":")
                    if field not in model_fields:
                        raise HTTPException(status_code=400, detail=f"非法字段: {field}")
                    if direction not in ("asc", "desc"):
                        raise HTTPException(status_code=400, detail=f"排序方向错误: {direction}")
                    query = query.order_by(field, direction)
        # 3. limit/offset
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        # 4. with_rel
        if enable_with_rel and with_rel:
            for rel in with_rel.split(","):
                if rel.strip() not in relation_fields:
                    raise HTTPException(status_code=400, detail=f"非法关系: {rel}")
                query = query.with_relations(rel.strip())
        # 5. search
        if search:
            if ":" in search:
                field, value = search.split(":", 1)
                if field not in model_fields:
                    raise HTTPException(status_code=400, detail=f"非法字段: {field}")
                query = query.where(field, "like", f"%{value}%")
            else:
                search_fields = getattr(model, "search_fields", [])
                for field in search_fields:
                    query = query.where(field, "like", f"%{search}%")
        # 6. range
        if range_:
            for cond in range_.split(","):
                if ":" in cond:
                    field, value = cond.split(":")
                    if field not in model_fields:
                        raise HTTPException(status_code=400, detail=f"非法字段: {field}")
                    if "-" in value:
                        start, end = value.split("-")
                        query = query.where(field, ">=", start).where(field, "<=", end)
                    elif "_" in value:
                        start, end = value.split("_")
                        query = query.where(field, ">=", start).where(field, "<=", end)
        # 7. 软删除
        if enable_soft_delete and only_trashed and hasattr(model, "only_trashed"):
            query = model.only_trashed()
        paginator = await query.paginate(page=page, per_page=per_page)
        return {
            "total": paginator.total,
            "items": [i.to_pydantic() for i in paginator.items],
            "page": paginator.current_page,
            "per_page": paginator.per_page,
        }

    @router.get(f"/{{{pk_name}}}", response_model=Schema)
    async def get_one(pk: int, _=Depends(permission)) -> Any:
        obj = await model.where(pk_name, pk).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        return obj.to_pydantic()

    @router.put(f"/{{{pk_name}}}", response_model=Schema)
    async def update(pk: int, data: CreateSchema, _=Depends(permission)) -> Any:
        obj = await model.where(pk_name, pk).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        await obj.update(**data.model_dump())
        return obj.to_pydantic()

    @router.delete(f"/{{{pk_name}}}")
    async def delete(pk: int, _=Depends(permission)) -> dict:
        obj = await model.where(pk_name, pk).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        await obj.delete()
        return {"success": True}

    # ========== 批量操作 ==========
    if enable_batch:

        @router.post("/batch", response_model=List[Schema])
        async def batch_create(data: List[CreateSchema], _=Depends(permission)) -> List[Any]:
            objs = await model.create_many([d.model_dump() for d in data])
            return [obj.to_pydantic() for obj in objs]

        @router.delete("/batch")
        async def batch_delete(ids: List[int] = Body(...), _=Depends(permission)) -> dict:
            count = await model.query().where(pk_name, "in", ids).delete()
            return {"deleted": count}

        @router.put("/batch")
        async def batch_update(ids: List[int] = Body(...), data: dict = Body(...), _=Depends(permission)) -> dict:
            count = await model.query().where(pk_name, "in", ids).update(**data)
            return {"updated": count}

    # ========== 软删除 ==========
    if enable_soft_delete and hasattr(model, "only_trashed"):

        @router.delete(f"/{{{pk_name}}}/soft")
        async def soft_delete(pk: int, _=Depends(permission)) -> dict:
            obj = await model.where(pk_name, pk).first()
            if not obj:
                raise HTTPException(status_code=404, detail="Not found")
            await obj.delete(force=False)
            return {"success": True}

        @router.post(f"/{{{pk_name}}}/restore")
        async def restore(pk: int, _=Depends(permission)) -> dict:
            obj = await model.with_trashed().where(pk_name, pk).first()
            if not obj:
                raise HTTPException(status_code=404, detail="Not found")
            await obj.restore()
            return {"success": True}

        @router.get("/trashed", response_model=Dict)
        async def list_trashed(page: int = Query(1, ge=1), per_page: int = Query(page_size, ge=1, le=100), with_rel: Optional[str] = Query(None, description="逗号分隔的关系名"), _=Depends(permission)) -> dict:
            query = model.only_trashed()
            if enable_with_rel and with_rel:
                for rel in with_rel.split(","):
                    query = query.with_relations(rel.strip())
            paginator = await query.paginate(page=page, per_page=per_page)
            return {
                "total": paginator.total,
                "items": [i.to_pydantic() for i in paginator.items],
                "page": paginator.current_page,
                "per_page": paginator.per_page,
            }

    return router

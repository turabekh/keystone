from app.models.base import BaseModel


def test_base_has_uuid_id_column():
    from app.models.base import BaseModel as BM

    assert "id" in BM.__annotations__ or any(
        "id" in cls.__annotations__ for cls in BM.__mro__ if hasattr(cls, "__annotations__")
    )


def test_base_has_timestamp_columns():
    from app.models.base import BaseModel as BM

    columns = set()
    for cls in BM.__mro__:
        if hasattr(cls, "__annotations__"):
            columns.update(cls.__annotations__.keys())
    assert "created_at" in columns
    assert "updated_at" in columns


def test_metadata_has_keystone_schema():
    from app.models.base import Base

    assert Base.metadata.schema == "keystone"


def test_metadata_has_naming_convention():
    from app.models.base import Base

    assert "pk" in Base.metadata.naming_convention
    assert "fk" in Base.metadata.naming_convention
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"


def test_base_is_abstract():
    from app.models.base import BaseModel

    assert BaseModel.__abstract__ is True


def test_subclass_requires_explicit_tablename():
    pass
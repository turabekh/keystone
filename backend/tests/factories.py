import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.county import County, CountyYearSetting


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"


class CountyFactory(BaseFactory):
    class Meta:
        model = County

    name = factory.Sequence(lambda n: f"County {n}")
    state = "PA"
    slug = factory.Sequence(lambda n: f"county-{n}")


class CountyYearSettingFactory(BaseFactory):
    class Meta:
        model = CountyYearSetting

    county = factory.SubFactory(CountyFactory)
    tax_year = 2026
    clr_factor = 30.0
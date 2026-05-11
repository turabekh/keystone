import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.county import County, CountyYearSetting
from app.models.property import Property, PropertyCategory
from app.models.sale import Sale


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


class PropertyFactory(BaseFactory):
    class Meta:
        model = Property

    county = factory.SubFactory(CountyFactory)
    parcel_id = factory.Sequence(lambda n: f"PARCEL-{n:08d}")
    address_full = factory.Sequence(lambda n: f"{n} TEST STREET PHILADELPHIA PA 19116")
    address_normalized = factory.LazyAttribute(lambda o: o.address_full.lower())
    street_number = factory.Sequence(lambda n: str(n))
    street_name = "TEST"
    street_suffix = "STREET"
    city = "PHILADELPHIA"
    state = "PA"
    zip_code = "19116"
    property_category = PropertyCategory.ROWHOUSE
    source_id = "test_source"
    payload_hash = factory.Sequence(lambda n: f"{n:064x}")


class SaleFactory(BaseFactory):
    class Meta:
        model = Sale

    property = factory.SubFactory(PropertyFactory)
    sale_date = factory.Faker("date_between", start_date="-5y", end_date="today")
    sale_price = factory.Faker("pyint", min_value=100000, max_value=800000)
    source_id = "test_source"
    payload_hash = factory.Sequence(lambda n: f"{n:064x}")
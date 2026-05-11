import pytest


@pytest.fixture
def sample_address_strings():
    return [
        "106 Overhill Ave, Philadelphia, PA 19116",
        "106 OVERHILL AVENUE PHILADELPHIA PA 19116",
        "106 overhill ave philadelphia pennsylvania",
    ]
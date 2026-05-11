def test_imports():
    import fastapi
    import sqlalchemy
    import psycopg
    import usaddress

    assert fastapi.__version__
    assert sqlalchemy.__version__
    assert psycopg.__version__
    assert usaddress.tag


def test_python_version():
    import sys

    assert sys.version_info >= (3, 12)
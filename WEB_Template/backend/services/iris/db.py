"""IRIS DB-API (intersystems-irispython). Spojení vždy zavírat, Community Edition má limit spojení (ARCH §4.6)."""
import os
from contextlib import contextmanager

import iris


DEFAULT_PASSWORD = 'SYS'      # výchozí heslo image IRIS; v produkci ho `iris_init` změní na IRIS_PASSWORD


@contextmanager
def connect(namespace: str | None = None, password: str | None = None):
    conn = iris.connect(
        os.environ.get('IRIS_HOST', 'iris'),
        int(os.environ.get('IRIS_PORT', '1972')),
        namespace or os.environ.get('IRIS_NAMESPACE', 'FHIRSERVER'),
        os.environ.get('IRIS_USER', 'SuperUser'),
        password or os.environ.get('IRIS_PASSWORD', DEFAULT_PASSWORD),
    )
    try:
        yield conn
    finally:
        conn.close()

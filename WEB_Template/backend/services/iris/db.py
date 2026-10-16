"""IRIS DB-API (intersystems-irispython). Spojení vždy zavírat, Community Edition má limit spojení (ARCH §4.6)."""
import os
from contextlib import contextmanager

import iris


@contextmanager
def connect(namespace: str | None = None):
    conn = iris.connect(
        os.environ.get('IRIS_HOST', 'iris'),
        int(os.environ.get('IRIS_PORT', '1972')),
        namespace or os.environ.get('IRIS_NAMESPACE', 'FHIRSERVER'),
        os.environ.get('IRIS_USER', 'SuperUser'),
        os.environ.get('IRIS_PASSWORD', 'SYS'),
    )
    try:
        yield conn
    finally:
        conn.close()

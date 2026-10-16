"""SQL projekce Observation (T-309): mapování řádků pohledu na ObservationSeries; živě se srovná s REST cestou."""
import pytest

from services import patients
from services.iris import projections
from services.iris.test_vector_store_integration import _iris_sql_up


class _Cursor:
    def __init__(self, rows):
        self.rows, self.sql, self.params = rows, None, None

    def execute(self, sql, params=()):
        self.sql, self.params = sql, params

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self._cursor


def test_rows_become_series(monkeypatch):
    rows = [("P03-lab01-hb", "718-7", "Hemoglobin", 121.0, "g/l", "2026-04-28T07:30:00+02:00", 135, 175, "L"),
            ("P03-lab02-hb", "718-7", "Hemoglobin", 119.0, "g/l", "2026-06-01T07:30:00+02:00", None, None, None)]
    cursor = _Cursor(rows)
    monkeypatch.setattr(projections.db, "connect", lambda *a, **k: _Conn(cursor))
    out = projections.observation_series("P03", {"718-7"})
    assert cursor.params == ["Patient/P03", "718-7"] and "Code IN (?)" in cursor.sql      # parametry přes ?
    assert out == [{"code": "718-7", "label": "Hemoglobin", "unit": "g/l", "points": [
        {"date": "2026-04-28", "value": 121, "citation": "P03-lab01-hb", "ref_low": 135, "ref_high": 175,
         "interpretation": "L"},
        {"date": "2026-06-01", "value": 119, "citation": "P03-lab02-hb"}]}]


@pytest.mark.integration
@pytest.mark.skipif(not _iris_sql_up(), reason='IRIS SQL nedostupný (dev.ps1 up)')
def test_sql_projection_matches_rest_in_live_iris():
    """Živé IRIS: pohled vrací pro P03 stejné body jako FHIR REST cesta (všechny kódované číselné řady)."""
    projections.ensure_view()
    sql = {s["code"]: s for s in projections.observation_series("P03")}
    rest = {s["code"]: s for s in patients.observations(patients.load_patient("P03")) if s["code"] in sql}
    assert {"718-7", "2039-6"} <= set(sql)
    for code, s in sql.items():
        expected = sorted(rest[code]["points"], key=lambda p: p["date"])
        assert [(p["citation"], p["value"]) for p in s["points"]] == [(p["citation"], p["value"]) for p in expected]

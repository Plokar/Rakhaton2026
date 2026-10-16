"""SQL projekce FHIR `Observation` v IRIS (T-309): pohled `MDT.ObservationSeries` nad úložištěm FHIR serveru.

Místo FHIR SQL Builderu (projekce se nastavuje ručně v portálu a synchronizuje) čte pohled přímo aktuální
resources z `HSFHIR_X0001_R.Rsrc` přes `JSON_TABLE`, takže je vždy aktuální a nic se nekopíruje. Řady
(laboratoř, markery, hmotnost, ECOG…) jdou dotazovat obyčejným SQL, např. v Management Portalu:

    SELECT * FROM MDT.ObservationSeries WHERE PatientRef = 'Patient/P03' AND Code = '718-7' ORDER BY EffectiveDate

`observation_series()` vrací stejný tvar jako REST cesta (`ObservationSeries` §8.2) pro číselné pozorování s kódem.
"""
from __future__ import annotations

import os
from collections import defaultdict

from services.iris import db

VIEW = "MDT.ObservationSeries"


def _rsrc_table() -> str:
    # ponytail: X0001 = první FHIR repository v namespace; jiná instalace → env IRIS_FHIR_RSRC_TABLE
    return os.environ.get("IRIS_FHIR_RSRC_TABLE", "HSFHIR_X0001_R.Rsrc")


def view_sql() -> str:
    return f"""SELECT r.ResourceId AS EvidenceId, jt.subj AS PatientRef, jt.code AS Code, jt.label AS Label,
       jt.val AS ValueNumber, jt.unit AS Unit, jt.dt AS EffectiveDate, jt.low AS RefLow, jt.high AS RefHigh,
       jt.interp AS Interpretation
FROM {_rsrc_table()} r,
     JSON_TABLE(r.ResourceString, '$' COLUMNS(
        code VARCHAR(40) PATH '$.code.coding[0].code',
        label VARCHAR(250) PATH '$.code.text',
        val NUMERIC(14,4) PATH '$.valueQuantity.value',
        unit VARCHAR(40) PATH '$.valueQuantity.unit',
        dt VARCHAR(40) PATH '$.effectiveDateTime',
        low NUMERIC(14,4) PATH '$.referenceRange[0].low.value',
        high NUMERIC(14,4) PATH '$.referenceRange[0].high.value',
        interp VARCHAR(10) PATH '$.interpretation[0].coding[0].code',
        subj VARCHAR(60) PATH '$.subject.reference')) jt
WHERE r.ResourceType = 'Observation' AND r.Deleted = 0 AND jt.val IS NOT NULL AND jt.code IS NOT NULL"""


def ensure_view() -> None:
    """Založí pohled, když chybí (idempotentní; volá `iris_init`)."""
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
                       VIEW.split("."))
        if not cursor.fetchone()[0]:
            cursor.execute(f"CREATE VIEW {VIEW} AS {view_sql()}")
            conn.commit()


def _num(value):
    if value is None:
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def observation_series(patient_id: str, codes: set[str] | None = None) -> list[dict]:
    """Řady pacienta z pohledu (SQL), tvar `ObservationSeries[]`; pořadí podle data."""
    sql = (f"SELECT EvidenceId, Code, Label, ValueNumber, Unit, EffectiveDate, RefLow, RefHigh, Interpretation "
           f"FROM {VIEW} WHERE PatientRef = ?")
    params: list = [f"Patient/{patient_id}"]
    if codes:
        sql += f" AND Code IN ({', '.join('?' * len(codes))})"
        params += sorted(codes)
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(sql + " ORDER BY EffectiveDate", params)
        rows = cursor.fetchall()
    series: dict[str, dict] = defaultdict(lambda: {"points": []})
    for evidence_id, code, label, value, unit, date, low, high, interp in rows:
        s = series[code]
        s.setdefault("label", label or code)
        s.setdefault("unit", unit)
        point = {"date": (date or "")[:10], "value": _num(value), "citation": evidence_id}
        if low is not None or high is not None:
            point.update(ref_low=_num(low), ref_high=_num(high))
        if interp:
            point["interpretation"] = interp
        s["points"].append(point)
    return [{"code": code, **s} for code, s in series.items()]

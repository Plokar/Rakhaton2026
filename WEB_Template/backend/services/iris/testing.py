"""In-memory náhrada IRIS SQL pro testy bez IRIS (fixture ``fake_iris`` v ``services/conftest.py``).

Nahrazuje ``services.iris.db.connect``, takže funguje ``services/iris/vector_store.py`` i
``services/ai/guidelines.py:load_guidelines``. Umí jen podmnožinu SQL, kterou tyto moduly posílají:
``CREATE TABLE`` / ``CREATE INDEX`` / ``DROP TABLE`` / ``ALTER TABLE … ADD``, ``INSERT … TO_VECTOR(?, DOUBLE)``,
``DELETE … WHERE``, ``SELECT [TOP n] … [VECTOR_COSINE(…) AS Score] … WHERE a = ? AND b IN (?, ?)
[ORDER BY Score DESC]``, ``GROUP BY [%EXACT(]sloupec[)]`` (bez ``%EXACT`` vrací velká písmena jako kolace
SQLUPPER v IRIS) a dotazy na ``INFORMATION_SCHEMA.TABLES`` / ``COLUMNS``.
Neznámý příkaz, tabulka nebo sloupec vyhodí ``FakeIrisError`` (jako chyba SQL v IRIS).

Hlídá i zavírání spojení (``open_connections``): Community Edition má limit spojení (AGENTS.md).
"""
import json
import math
import re
from contextlib import contextmanager


class FakeIrisError(Exception):
    pass


def _split_top_level(text: str) -> list[str]:
    parts, depth, current = [], 0, ''
    for ch in text:
        if ch == ',' and depth == 0:
            parts.append(current.strip())
            current = ''
            continue
        depth += ch == '('
        depth -= ch == ')'
        current += ch
    return parts + [current.strip()] if current.strip() else parts


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


_CREATE = re.compile(r'CREATE TABLE (\w+)\.(\w+) \((.*)\)$', re.S)
_INDEX = re.compile(r'CREATE INDEX \w+ ON (\w+)\.(\w+) \((\w+)\)$')
_DROP = re.compile(r'DROP TABLE (\w+)\.(\w+)$')
_INSERT = re.compile(r'INSERT INTO (\w+)\.(\w+) \((.*?)\) VALUES \((.*)\)$', re.S)
_DELETE = re.compile(r'DELETE FROM (\w+)\.(\w+)(?: WHERE (.*))?$', re.S)
_SELECT = re.compile(
    r'SELECT (?:TOP (\d+) )?(.*?) FROM (\w+)\.(\w+)(?: WHERE (.*?))?(?: GROUP BY (%EXACT\(\w+\)|\w+))?'
    r'(?: ORDER BY (\w+) DESC)?$', re.S,
)
_SCORE = 'VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Score'
_EXISTS = 'SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?'
_COLUMNS = 'SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?'
_ALTER_ADD = re.compile(r'ALTER TABLE (\w+)\.(\w+) ADD (\w+) (.+)$')


class FakeIris:
    def __init__(self):
        self.tables: dict[str, dict] = {}        # "MDT.EvidenceChunk" → {"columns": [...], "dim": 1536, "rows": [...]}
        self.statements: list[str] = []
        self.open_connections = 0

    def rows(self, table: str) -> list[dict]:
        return self.tables[table]['rows']

    @contextmanager
    def connect(self, namespace=None):
        self.open_connections += 1
        try:
            yield _Connection(self)
        finally:
            self.open_connections -= 1

    # ── vykonání jednoho příkazu ──
    def execute(self, sql: str, params) -> list[tuple]:
        sql = ' '.join(sql.split())
        params = list(params or [])
        self.statements.append(sql)
        if sql == _EXISTS:
            return [(1 if f'{params[0]}.{params[1]}' in self.tables else 0,)]
        if sql == _COLUMNS:
            table = self.tables.get(f'{params[0]}.{params[1]}')
            return [(c,) for c in table['columns']] if table else []
        if m := _ALTER_ADD.match(sql):
            table = self._table(m[1], m[2])
            if m[3] in table['columns']:
                raise FakeIrisError(f'Sloupec {m[3]} už existuje')
            table['columns'].append(m[3])
            return []
        if m := _CREATE.match(sql):
            name = f'{m[1]}.{m[2]}'
            if name in self.tables:
                raise FakeIrisError(f'Tabulka {name} už existuje')
            columns, dim = [], None
            for col in _split_top_level(m[3]):
                col_name, col_type = col.split(' ', 1)
                columns.append(col_name)
                if vm := re.match(r'VECTOR\(DOUBLE, (\d+)\)', col_type):
                    dim = int(vm[1])
            self.tables[name] = {'columns': columns, 'dim': dim, 'rows': []}
            return []
        if m := _INDEX.match(sql):
            self._column(self._table(m[1], m[2]), m[3])
            return []
        if m := _DROP.match(sql):
            self._table(m[1], m[2])
            del self.tables[f'{m[1]}.{m[2]}']
            return []
        if m := _INSERT.match(sql):
            return self._insert(self._table(m[1], m[2]), m[3], m[4], params)
        if m := _DELETE.match(sql):
            table = self._table(m[1], m[2])
            keep = [r for r in table['rows'] if not self._where(table, m[3], list(params))(r)]
            table['rows'] = keep
            return []
        if m := _SELECT.match(sql):
            return self._select(m, params)
        raise FakeIrisError(f'Fake IRIS neumí příkaz: {sql}')

    def _table(self, schema, name) -> dict:
        full = f'{schema}.{name}'
        if full not in self.tables:
            raise FakeIrisError(f'Tabulka {full} neexistuje (SQLCODE -30)')
        return self.tables[full]

    def _column(self, table, col):
        if col not in table['columns']:
            raise FakeIrisError(f'Sloupec {col} neexistuje')
        return col

    def _insert(self, table, cols_sql, values_sql, params):
        cols = [self._column(table, c.strip()) for c in cols_sql.split(',')]
        values = _split_top_level(values_sql)
        if len(cols) != len(values) or len(params) != len(values):
            raise FakeIrisError('Počet sloupců, hodnot a parametrů nesedí')
        row = {}
        for col, value_sql, param in zip(cols, values, params):
            if value_sql == 'TO_VECTOR(?, DOUBLE)':
                vector = json.loads(param)
                if len(vector) != table['dim']:
                    raise FakeIrisError(f"Vektor má {len(vector)} dimenzí, sloupec {table['dim']}")
                row[col] = vector
            elif value_sql == '?':
                row[col] = param
            else:
                raise FakeIrisError(f'Neznámá hodnota {value_sql}')
        table['rows'].append(row)
        return []

    def _where(self, table, where_sql, params):
        """Vrátí predikát; spotřebuje parametry z ``params`` (seznam se mění na místě)."""
        tests = []
        for clause in (where_sql.split(' AND ') if where_sql else []):
            if m := re.fullmatch(r'(\w+) = \?', clause):
                col, value = self._column(table, m[1]), params.pop(0)
                tests.append(lambda r, c=col, v=value: r.get(c) == v)
            elif m := re.fullmatch(r'(\w+) IN \(([?, ]+)\)', clause):
                col, n = self._column(table, m[1]), m[2].count('?')
                values = {params.pop(0) for _ in range(n)}
                tests.append(lambda r, c=col, vs=values: r.get(c) in vs)
            else:
                raise FakeIrisError(f'Fake IRIS neumí podmínku: {clause}')
        return lambda row: all(t(row) for t in tests)

    def _select(self, m, params):
        top, select_sql, schema, name, where_sql, group_by, order_by = m.groups()
        table = self._table(schema, name)
        with_score = _SCORE in select_sql
        query = json.loads(params.pop(0)) if with_score else None
        cols = [c.strip() for c in select_sql.replace(_SCORE, '').split(',') if c.strip()]
        predicate = self._where(table, where_sql, params)
        rows = [r for r in table['rows'] if predicate(r)]
        if group_by:
            # jako IRIS: GROUP BY vrací hodnotu v kolaci SQLUPPER, přesnou jen přes %EXACT(…) (Q16)
            exact = group_by.startswith('%EXACT(')
            col = self._column(table, group_by[len('%EXACT('):-1] if exact else group_by)
            counts: dict = {}
            for r in rows:
                value = r[col] if exact or not isinstance(r[col], str) else r[col].upper()
                counts[value] = counts.get(value, 0) + 1
            return list(counts.items())
        out = []
        for r in rows:
            values = [r.get(self._column(table, c)) for c in cols]
            if with_score:
                values.append(_cosine(r['Embedding'], query))
            out.append(tuple(values))
        if order_by:
            if order_by != 'Score' or not with_score:
                raise FakeIrisError(f'Fake IRIS řadí jen podle Score, ne {order_by}')
            out.sort(key=lambda v: v[-1], reverse=True)
        return out[:int(top)] if top else out


class _Connection:
    def __init__(self, iris: FakeIris):
        self.iris = iris
        self.commits = 0

    def cursor(self):
        return _Cursor(self.iris)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


class _Cursor:
    def __init__(self, iris: FakeIris):
        self.iris = iris
        self._rows: list[tuple] = []

    def execute(self, sql, params=None):
        self._rows = self.iris.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        for params in seq_of_params:
            self.iris.execute(sql, params)
        self._rows = []

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def close(self):
        pass

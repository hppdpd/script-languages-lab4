from typing import Any

import psycopg
from psycopg import errors
from psycopg.rows import dict_row

from lab4.domain import Laureate
from lab4.repository import ConflictError, LaureateRepository, NotFoundError

SELECT_LAUREATES = """
SELECT l.id, l.full_name, l.email, l.birth_year, l.country_id,
       COALESCE(
           array_agg(lp.prize_id ORDER BY lp.prize_id)
               FILTER (WHERE lp.prize_id IS NOT NULL),
           ARRAY[]::int[]
       ) AS prize_ids
FROM laureates l
LEFT JOIN laureate_prizes lp ON lp.laureate_id = l.id
"""


def _to_laureate(row: dict[str, Any]) -> Laureate:
    return Laureate(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        birth_year=row["birth_year"],
        country_id=row["country_id"],
        prize_ids=list(row["prize_ids"]),
    )


class PgLaureateRepository(LaureateRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> "psycopg.Connection[dict[str, Any]]":
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def list_all(self, limit: int, offset: int) -> list[Laureate]:
        query = SELECT_LAUREATES + " GROUP BY l.id ORDER BY l.id LIMIT %s OFFSET %s"
        with self._connect() as conn:
            rows = conn.execute(query, (limit, offset)).fetchall()
        return [_to_laureate(r) for r in rows]

    def get(self, laureate_id: int) -> Laureate:
        query = SELECT_LAUREATES + " WHERE l.id = %s GROUP BY l.id"
        with self._connect() as conn:
            row = conn.execute(query, (laureate_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Laureate {laureate_id} not found")
        return _to_laureate(row)

    @staticmethod
    def _set_prizes(
        conn: "psycopg.Connection[dict[str, Any]]",
        laureate_id: int,
        prize_ids: list[int],
    ) -> None:
        conn.execute(
            "DELETE FROM laureate_prizes WHERE laureate_id = %s", (laureate_id,)
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO laureate_prizes (laureate_id, prize_id) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                [(laureate_id, p) for p in prize_ids],
            )

    def create(self, laureate: Laureate) -> Laureate:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "INSERT INTO laureates (full_name, email, birth_year, country_id) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (
                        laureate.full_name,
                        laureate.email,
                        laureate.birth_year,
                        laureate.country_id,
                    ),
                ).fetchone()
                assert row is not None
                new_id: int = row["id"]
                self._set_prizes(conn, new_id, laureate.prize_ids)
        except errors.UniqueViolation as exc:
            raise ConflictError("Email already exists") from exc
        except errors.ForeignKeyViolation as exc:
            raise ConflictError("Country or prize does not exist") from exc
        return self.get(new_id)

    def update(self, laureate_id: int, laureate: Laureate) -> Laureate:
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "UPDATE laureates SET full_name = %s, email = %s, "
                    "birth_year = %s, country_id = %s WHERE id = %s",
                    (
                        laureate.full_name,
                        laureate.email,
                        laureate.birth_year,
                        laureate.country_id,
                        laureate_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise NotFoundError(f"Laureate {laureate_id} not found")
                self._set_prizes(conn, laureate_id, laureate.prize_ids)
        except errors.UniqueViolation as exc:
            raise ConflictError("Email already exists") from exc
        except errors.ForeignKeyViolation as exc:
            raise ConflictError("Country or prize does not exist") from exc
        return self.get(laureate_id)

    def delete(self, laureate_id: int) -> None:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM laureates WHERE id = %s", (laureate_id,))
            if cur.rowcount == 0:
                raise NotFoundError(f"Laureate {laureate_id} not found")

"""Small safe SQL query builder for common repository operations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SelectQuery:
    """Composable SELECT query with parameter binding."""

    table: str
    columns: tuple[str, ...] = ("*",)
    where_clauses: list[str] = field(default_factory=list)
    params: list[object] = field(default_factory=list)
    order_by_clause: str | None = None
    limit_value: int | None = None

    def where(self, clause: str, *params: object) -> "SelectQuery":
        self.where_clauses.append(clause)
        self.params.extend(params)
        return self

    def order_by(self, column: str, direction: str | None = None) -> "SelectQuery":
        """
        Supports both:
            order_by("id", "DESC")
        and:
            order_by("id DESC")
        """

        if direction is None:
            # Already supplied as a complete clause
            self.order_by_clause = column.strip()
        else:
            direction = direction.upper().strip()
            if direction not in ("ASC", "DESC"):
                raise ValueError("direction must be ASC or DESC")
            self.order_by_clause = f"{column.strip()} {direction}"

        return self

    def limit(self, limit: int) -> "SelectQuery":
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        self.limit_value = limit
        return self

    def build(self) -> tuple[str, tuple[object, ...]]:
        sql = f"SELECT {', '.join(self.columns)} FROM {self.table}"
        params = list(self.params)

        if self.where_clauses:
            sql += " WHERE " + " AND ".join(self.where_clauses)

        if self.order_by_clause:
            sql += f" ORDER BY {self.order_by_clause}"

        if self.limit_value is not None:
            sql += " LIMIT ?"
            params.append(self.limit_value)

        return sql, tuple(params)


def build_insert(table: str, values: dict[str, object]) -> tuple[str, tuple[object, ...]]:
    """Build an INSERT OR IGNORE statement with bound parameters.
    OR IGNORE means duplicate rows (e.g. same device_id + sequence_number
    after a firmware reboot) are silently skipped instead of raising
    UNIQUE constraint errors that flood the log.
    """

    if not values:
        raise ValueError("values must not be empty")

    columns = tuple(values.keys())
    parameter_marks = ", ".join("?" for _ in columns)

    sql = (
        f"INSERT OR REPLACE INTO {table} "
        f"({', '.join(columns)}) "
        f"VALUES ({parameter_marks})"
    )

    return sql, tuple(values[column] for column in columns)


def build_update(
    table: str,
    values: dict[str, object],
    where_clause: str,
    where_params: tuple[object, ...],
) -> tuple[str, tuple[object, ...]]:
    """Build an UPDATE statement with bound parameters."""

    if not values:
        raise ValueError("values must not be empty")

    assignments = ", ".join(f"{column} = ?" for column in values)

    sql = f"UPDATE {table} SET {assignments} WHERE {where_clause}"

    return sql, tuple(values.values()) + where_params
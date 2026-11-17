from collections.abc import Iterable
from enum import StrEnum

from sqlalchemy import CheckConstraint


def enum_check(column: str, allowed: Iterable[str] | type[StrEnum], name: str) -> CheckConstraint:
    """Build a CHECK constraint limiting a text column to a closed set of values.

    Args:
        column: Column name the constraint applies to.
        allowed: Allowed values, or a StrEnum whose members are allowed.
        name: Constraint name (without the naming-convention prefix).

    Returns:
        A CHECK constraint of the form ``column IN ('a', 'b')``.
    """
    values = [member.value for member in allowed] if isinstance(allowed, type) else list(allowed)
    quoted = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=name)

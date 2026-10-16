"""Classify potentially expensive SQL queries for user confirmation."""

from sqlglot import exp, parse_one

from src.sql_safety import validate_sql


def requires_confirmation(sql: str) -> bool:
    """Return True for expensive queries or anything that cannot be validated."""
    try:
        safe_sql = validate_sql(sql)
        query = parse_one(safe_sql, read="sqlite")
    except Exception:
        # Fail closed: invalid SQL must never be classified as low risk.
        return True

    if not isinstance(query, (exp.Select, exp.Union)):
        return True

    joins = list(query.find_all(exp.Join))
    has_filter = query.find(exp.Where) is not None
    has_grouping = query.find(exp.Group) is not None
    has_subquery = query.find(exp.Subquery) is not None
    has_limit = query.args.get("limit") is not None

    if len(joins) >= 3:
        return True

    if has_grouping and not has_filter:
        return True

    if has_subquery:
        return True

    if len(joins) >= 2 and not has_limit:
        return True

    return False
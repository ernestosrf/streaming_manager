from datetime import datetime, timezone


def utcnow():
    """UTC atual sem tzinfo, compatível com as colunas DateTime (naive) existentes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

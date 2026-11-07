def parse_callback_id(data: str) -> int | None:
    """
    Безопасно достать числовой id из callback data вида «prefix:<id>».

    Возвращает None вместо исключения на мусоре («srch:abc», «npage:»),
    чтобы хендлер не падал с ValueError и не слал алерт админу.
    """
    try:
        return int(data.split(":")[1])
    except (IndexError, ValueError):
        return None
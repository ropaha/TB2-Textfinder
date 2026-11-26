"""Locale-independent German display formatting."""


def format_number(value, decimals=0):
    return format(value, f",.{decimals}f").translate(str.maketrans(",.", ".,"))

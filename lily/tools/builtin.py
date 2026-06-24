"""Built-in tools that ship with every Lily. Kept tiny — bigger capabilities live in agents."""

from datetime import datetime

from . import tool


@tool(description="Get the current local date and time. Use whenever the user asks about now, today, the date, or the time.")
def get_datetime() -> str:
    return datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")

from datetime import date, datetime


class SimpleDate(date):
    """A date restricted to 'YYYY-MM-DD' string form, matching the yaml manifest convention
    that dates must be quoted strings to avoid the yaml parser's native date handling."""

    FORMAT = "%Y-%m-%d"

    def __new__(cls, value):
        if isinstance(value, str):
            try:
                parsed = datetime.strptime(value, cls.FORMAT).date()
            except ValueError as e:
                raise ValueError(f"Cannot parse as date '{value}'") from e
            return super().__new__(cls, parsed.year, parsed.month, parsed.day)
        if isinstance(value, date):
            return super().__new__(cls, value.year, value.month, value.day)
        raise TypeError(f"Unsupported type for SimpleDate: {type(value)}")

    def __str__(self) -> str:
        return self.strftime(self.FORMAT)

from datetime import date, timedelta


def current_date(): 
    """Get the current date in YYYY-MM-DD format."""
    return date.today().strftime("%Y-%m-%d")

def previous_date(date_str = None):
    """Get the previous working day (Monday-Friday) in YYYY-MM-DD format."""
    if date_str is None:
        reference_date = date.today()
    else:
        reference_date = date.fromisoformat(date_str)
    previous_day = reference_date - timedelta(days = 1)

    # If Saturday (5), go back to Friday
    # If Sunday (6), go back to Friday
    while previous_day.weekday() >= 5:
        previous_day = previous_day - timedelta(days = 1)

    return previous_day.strftime("%Y-%m-%d")


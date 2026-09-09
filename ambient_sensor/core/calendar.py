import calendar

MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def get_max_days(year: int, month: int) -> int:
    if month == 2 and calendar.isleap(year):
        return 29
    return MONTH_DAYS[month - 1]
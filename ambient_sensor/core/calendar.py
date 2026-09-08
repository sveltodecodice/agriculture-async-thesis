MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
LEAP_DAYS = 29

def is_leap(year):
    if year % 4 == 0:
            return True
    else:
        return False
    
def get_max_days(year, month):
    
    idx = month - 1
    days = MONTH_DAYS[idx] if not (is_leap(year) and month == 2) else LEAP_DAYS
    
    return days

days = list(range(1, 32))
months = list(range(1, 13))
years = list(range(2026, 2036))

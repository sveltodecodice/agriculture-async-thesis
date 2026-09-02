def is_leap(year):
    if year % 4 == 0:
        if year % 100 == 0:
            if year % 400 == 0:
                return True
            else:
                return False
        else:
            return True
    else:
        return False
    
def get_max_days(year, month):
    if is_leap(year) and month == 2:
        return 29
    
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return month_days[month-1]

days = list(range(1, 32))
months = list(range(1, 13))
years = list(range(2026, 2036))

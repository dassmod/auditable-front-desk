from datetime import datetime, timedelta

DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4
}

def parse_booking(text, now):
    words = text.lower().split()

    if len(words) != 3:
        return None

    verb, day, time_text = words

    if verb != "book":
        return None

    target = DAYS.get(day)
    if target == None:
        return None

    try:
        clock = datetime.strptime(time_text, "%H:%M")
    except ValueError:
        return None

    now = datetime.fromisoformat(now)
    today = now.weekday()

    ahead = (target - today) % 7
    if ahead == 0:
        ahead = 7

    date = now.date() + timedelta(days=ahead)
    return date.isoformat() + "T" + clock.strftime("%H:%M")
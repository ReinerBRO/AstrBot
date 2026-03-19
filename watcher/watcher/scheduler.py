from datetime import datetime, time, timedelta


def in_window(now: datetime, start: time, end: time) -> bool:
    if start <= end:
        return start <= now.time() <= end
    return now.time() >= start or now.time() <= end


def seconds_until_start(now: datetime, start: time) -> int:
    today_start = datetime.combine(now.date(), start)
    if now <= today_start:
        return int((today_start - now).total_seconds())
    tomorrow_start = today_start + timedelta(days=1)
    return int((tomorrow_start - now).total_seconds())

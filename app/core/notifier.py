import threading
from datetime import datetime, timedelta

from plyer import notification

from app.core.schedule_manager import get_manager
from app.core.timeutil import now_kst

_scheduled_timers: list[threading.Timer] = []


def _notify(title: str, message: str):
    notification.notify(title=title, message=message, timeout=10, app_name="근무 스케쥴러")


def send_test_notification():
    _notify("근무 스케쥴러", "테스트 알림입니다. 정상적으로 동작하고 있습니다.")


def schedule_all_today_alarms(minutes_before: int):
    for timer in _scheduled_timers:
        timer.cancel()
    _scheduled_timers.clear()

    now = now_kst()
    for shift in get_manager().get_todays_shifts():
        fire_at = datetime.combine(shift.date, shift.start_time) - timedelta(minutes=minutes_before)
        delay = (fire_at - now).total_seconds()
        if delay <= 0:
            continue

        timer = threading.Timer(
            delay,
            _notify,
            args=("근무 시작 알림", f"{shift.employee_name}님 근무가 {minutes_before}분 후 시작됩니다."),
        )
        timer.daemon = True
        timer.start()
        _scheduled_timers.append(timer)

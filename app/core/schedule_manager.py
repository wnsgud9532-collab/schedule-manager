from datetime import date
from typing import List, Dict
from app.models.schedule import Shift, Employee
import app.core.database as db


class ScheduleManager:
    def get_todays_shifts(self) -> List[Shift]:
        return db.get_shifts_for_date(date.today())

    def get_monthly_shifts(self, year: int, month: int) -> List[Shift]:
        return db.get_shifts_for_month(year, month)

    def get_shifts_by_date(self, target_date: date) -> List[Shift]:
        return db.get_shifts_for_date(target_date)

    def get_monthly_by_day(self, year: int, month: int) -> Dict[int, List[Shift]]:
        shifts = self.get_monthly_shifts(year, month)
        result: Dict[int, List[Shift]] = {}
        for shift in shifts:
            day = shift.date.day
            result.setdefault(day, []).append(shift)
        return result

    def get_employees(self) -> List[Employee]:
        return db.get_all_employees()

    def import_shifts(self, shifts: List[Shift], year: int, month: int, replace: bool = True):
        if replace:
            db.delete_shifts_for_month(year, month)
        db.insert_shifts_bulk(shifts)


_manager = ScheduleManager()


def get_manager() -> ScheduleManager:
    return _manager

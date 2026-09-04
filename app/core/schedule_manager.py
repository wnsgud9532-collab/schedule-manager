from datetime import date, time, timedelta
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

    def get_weekly_schedule(self, week_start: date) -> Dict[str, Dict[date, list]]:
        """로컬 DB(엑셀로 가져온 데이터) 기준 주간 근무/휴무 데이터.

        Returns: {
            'work': {date: [(name, hour), ...]},  # 시간대별 근무자
            'off':  {date: [name, ...]},          # 그날 근무 기록이 없는 직원
        }
        """
        days = [week_start + timedelta(days=i) for i in range(7)]
        all_names = {e.name for e in self.get_employees()}

        work: Dict[date, list] = {}
        off: Dict[date, list] = {}
        for d in days:
            shifts = self.get_shifts_by_date(d)
            work[d] = [(s.employee_name, s.start_time.hour) for s in shifts]
            worked_names = {s.employee_name for s in shifts}
            off[d] = sorted(all_names - worked_names)

        return {"work": work, "off": off}

    # ── 근무 수정 ──────────────────────────────────────────────────────
    def get_shift_for_employee(self, employee_name: str, target_date: date) -> List[Shift]:
        return db.get_shifts_for_employee_date(employee_name, target_date)

    def edit_shift_time(self, shift_id: int, start_time: time, end_time: time):
        """근무 시간 변경 (최초 수정 시 원본은 자동 보존됨)."""
        db.update_shift(shift_id, start_time, end_time, note="")

    def mark_shift_off(self, shift_id: int):
        """휴무로 변경 (소프트 삭제 — 원본 보존, 언제든 복구 가능)."""
        db.delete_shift(shift_id)

    def add_shift(self, employee_name: str, target_date: date, start_time: time, end_time: time):
        """휴무였던 날짜에 새 근무를 등록."""
        db.insert_shifts_bulk([Shift(
            id=None, employee_id=0, employee_name=employee_name,
            date=target_date, start_time=start_time, end_time=end_time,
        )])

    def get_modified_shifts(self) -> List[dict]:
        """수정/휴무 처리된 근무 기록 전체 (원본 정보 포함)."""
        return db.get_modified_shifts()

    def restore_shift(self, shift_id: int) -> bool:
        """개별 수정 기록을 원본으로 되돌림."""
        return db.restore_shift_original(shift_id)

    def restore_all_shifts(self) -> int:
        """모든 수정 기록을 원본으로 되돌림. 되돌린 건수 반환."""
        return db.restore_all_originals()


_manager = ScheduleManager()


def get_manager() -> ScheduleManager:
    return _manager

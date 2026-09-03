from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from typing import Optional


@dataclass
class Employee:
    id: int
    name: str


@dataclass
class Shift:
    id: Optional[int]
    employee_id: int
    employee_name: str
    date: date
    start_time: time
    end_time: time
    note: str = ""

    def is_active_at(self, dt: datetime) -> bool:
        shift_start = datetime.combine(self.date, self.start_time)
        shift_end = datetime.combine(self.date, self.end_time)
        if self.end_time <= self.start_time:
            shift_end += timedelta(days=1)
        return shift_start <= dt < shift_end

    def duration_hours(self) -> float:
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        if self.end_time <= self.start_time:
            end_dt += timedelta(days=1)
        return (end_dt - start_dt).seconds / 3600

    def start_str(self) -> str:
        return self.start_time.strftime("%H:%M")

    def end_str(self) -> str:
        return self.end_time.strftime("%H:%M")

    def time_range_str(self) -> str:
        return f"{self.start_str()} ~ {self.end_str()}"

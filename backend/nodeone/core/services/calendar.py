"""CalendarService — agenda compartida (Etapa 11 stub)."""

from __future__ import annotations


class CalendarServiceNotReadyError(NotImplementedError):
    pass


class CalendarService:
    @staticmethod
    def list_availability(*_args, **_kwargs):
        raise CalendarServiceNotReadyError(
            'CalendarService unificado pendiente; usar EAppointments/ecalendar hasta convergencia.'
        )

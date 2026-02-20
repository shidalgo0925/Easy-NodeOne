#!/usr/bin/env python3
"""
Asigna todos los asesores activos a todos los tipos de cita (servicios de citas).
Así en el catálogo de servicios aparecerán todos los asesores disponibles.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Service, AppointmentType, AppointmentAdvisor, Advisor


def run():
    with app.app_context():
        types = AppointmentType.query.filter_by(is_active=True).order_by(AppointmentType.display_order).all()
        advisors = Advisor.query.filter_by(is_active=True).all()

        if not types:
            print("No hay tipos de cita activos.")
            return
        if not advisors:
            print("No hay asesores activos.")
            return

        print(f"Tipos de cita: {len(types)}")
        print(f"Asesores activos: {len(advisors)}")
        print()

        total_added = 0
        total_reactivated = 0

        for at in types:
            for advisor in advisors:
                existing = AppointmentAdvisor.query.filter_by(
                    appointment_type_id=at.id,
                    advisor_id=advisor.id,
                ).first()
                if not existing:
                    db.session.add(AppointmentAdvisor(
                        appointment_type_id=at.id,
                        advisor_id=advisor.id,
                        priority=1,
                        is_active=True,
                    ))
                    total_added += 1
                    print(f"  + {at.name} ← {advisor.user.first_name} {advisor.user.last_name}" if advisor.user else f"  + {at.name} ← advisor_id={advisor.id}")
                elif not getattr(existing, "is_active", True):
                    existing.is_active = True
                    total_reactivated += 1

        db.session.commit()
        print()
        print(f"Listo: {total_added} asignaciones nuevas, {total_reactivated} reactivadas.")
        print("Todos los servicios (tipos de cita) tienen ahora todos los asesores disponibles.")


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""
Actualiza membership_plan (org 1) a los planes IIUS: Personal, Emprendedor, Ejecutivo.
Desactiva y elimina slugs legacy pro/premium/deluxe/corporativo (sin FK a membership_plan).
Ejecutar desde el directorio backend con la misma DB que NodeOne:

  cd /opt/easynodeone/app/backend && python3 tools/apply_iius_membership_plans.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime

DB = '/opt/easynodeone/app/instance/NodeOne.db'
ORG = 1

DESC_PERSONAL = """Inicia tu crecimiento. Talleres, programas y contenidos exclusivos para ayudarte a alcanzar tus objetivos profesionales.

• 149 USD anuales
• 1 encuentro mensual en vivo
• Acceso a talleres exclusivos para miembros
• Acceso a desarrollo profesional y contenido seleccionado
• Descuento del 20% en cualquier curso o diplomado
• Acceso a la Revista International de ICI"""

DESC_EMPRENDEDOR = """Desarrolla tu negocio. Únete al grupo de emprendedores y accede a programas y recursos exclusivos para el crecimiento empresarial.

• 449 USD anuales
• 2 encuentros mensuales en vivo
• Círculos de Coaching Empresarial
• Acceso a expertos y mentores en crecimiento empresarial
• Acceso a recursos y plantillas para el crecimiento empresarial
• Publica tu emprendimiento o artículos en la revista Internacional de ICI (1/2 página)
• Descuentos del 30% para empresas miembros seleccionadas"""

DESC_EJECUTIVO = """Únete al grupo de Ejecutivos y accede a programas y recursos exclusivos para el crecimiento empresarial.

• 949 USD anuales
• Únete a la Liga Empresarial
• 1 encuentro mensual personal con tu coach de preferencia
• 1 encuentro mensual en vivo
• Círculo de Coaching Empresarial
• Campaña de Destacados Empresariales en la revista International
• Expertos disponibles para subvenciones y certificaciones de empresas propiedad de minorías
• Acceso a expertos y mentores en crecimiento empresarial
• Acceso a recursos y plantillas para el crecimiento empresarial
• Publica tu emprendimiento o artículos en la revista Internacional de ICI (artículos científicos o publicidad 1 página)
• Eventos empresariales exclusivos para miembros
• Descuentos exclusivos para empresas (confirmar condiciones con el instituto)"""


def main() -> int:
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute(
        'DELETE FROM membership_plan WHERE organization_id = ? AND slug IN (?,?,?,?)',
        (ORG, 'pro', 'premium', 'deluxe', 'corporativo'),
    )

    # ``basic`` no es un plan de venta: solo valor técnico en código; no debe existir fila en catálogo.
    cur.execute('DELETE FROM membership_plan WHERE organization_id = ? AND slug = ?', (ORG, 'basic'))

    for slug, name, desc, yearly, monthly, dorder, lvl, badge, color in (
        (
            'personal',
            'Membresía Personal',
            DESC_PERSONAL,
            149.0,
            round(149 / 12, 2),
            10,
            1,
            'Inicia tu crecimiento',
            'bg-success',
        ),
        (
            'emprendedor',
            'Membresía Emprendedor',
            DESC_EMPRENDEDOR,
            449.0,
            round(449 / 12, 2),
            20,
            2,
            'Desarrolla tu negocio',
            'bg-info',
        ),
        (
            'ejecutivo',
            'Membresía Ejecutivo',
            DESC_EJECUTIVO,
            949.0,
            round(949 / 12, 2),
            30,
            3,
            'Liga Empresarial',
            'bg-primary',
        ),
    ):
        cur.execute('SELECT id FROM membership_plan WHERE organization_id = ? AND slug = ?', (ORG, slug))
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE membership_plan SET name=?, description=?, price_yearly=?, price_monthly=?,
                display_order=?, level=?, badge=?, color=?, is_active=1, updated_at=?
                WHERE organization_id=? AND slug=?
                """,
                (name, desc, yearly, monthly, dorder, lvl, badge, color, now, ORG, slug),
            )
        else:
            cur.execute(
                """
                INSERT INTO membership_plan (
                    slug, name, description, price_yearly, price_monthly, display_order, level,
                    badge, color, is_active, created_at, updated_at, organization_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (slug, name, desc, yearly, monthly, dorder, lvl, badge, color, 1, now, now, ORG),
            )

    cur.execute(
        'UPDATE membership_plan SET display_order = 99, level = 99, updated_at = ? WHERE organization_id = ? AND slug = ?',
        (now, ORG, 'admin'),
    )

    cur.execute(
        """
        UPDATE benefit SET membership_type = 'ejecutivo'
        WHERE organization_id = ? AND membership_type IN ('pro','premium','deluxe','corporativo')
        """,
        (ORG,),
    )

    cur.execute(
        "DELETE FROM membership_discount WHERE membership_type IN "
        "('pro','premium','deluxe','corporativo','personal','emprendedor','ejecutivo')"
    )
    for slug, pct in (('personal', 20.0), ('emprendedor', 30.0), ('ejecutivo', 40.0)):
        for pt in ('service', 'event'):
            cur.execute(
                """
                INSERT INTO membership_discount (
                    membership_type, product_type, discount_percentage, is_active, created_at, updated_at
                ) VALUES (?,?,?,?,?,?)
                """,
                (slug, pt, pct, 1, now, now),
            )

    con.commit()
    print('OK — membership_plan actualizado para organization_id=', ORG)
    for r in cur.execute(
        'SELECT slug, name, price_yearly, level, is_active FROM membership_plan WHERE organization_id = ? ORDER BY display_order, id',
        (ORG,),
    ):
        print(' ', r)
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Script para eliminar registros duplicados de la base de datos
"""
import sqlite3
import os
from datetime import datetime

# Usar la base de datos principal
db_path = 'instance/membership_legacy.db'
if not os.path.exists(db_path):
    db_path = '../instance/membership_legacy.db'

if not os.path.exists(db_path):
    print("❌ No se encontró la base de datos")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== Eliminando registros duplicados ===\n")

# 1. Eliminar usuarios duplicados (mantener el más reciente)
print("1. Eliminando usuarios duplicados...")
cursor.execute("""
    DELETE FROM user 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM user 
        GROUP BY email
    )
""")
deleted_users = cursor.rowcount
print(f"   ✅ Eliminados {deleted_users} usuarios duplicados")

# 2. Eliminar pagos duplicados (mantener el más reciente)
print("\n2. Eliminando pagos duplicados...")
cursor.execute("""
    DELETE FROM payment 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM payment 
        GROUP BY stripe_payment_intent_id
    )
""")
deleted_payments = cursor.rowcount
print(f"   ✅ Eliminados {deleted_payments} pagos duplicados")

# 3. Eliminar membresías duplicadas (mantener la más reciente)
print("\n3. Eliminando membresías duplicadas...")
cursor.execute("""
    DELETE FROM membership 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM membership 
        GROUP BY user_id, membership_type, DATE(start_date)
    )
""")
deleted_memberships = cursor.rowcount
print(f"   ✅ Eliminadas {deleted_memberships} membresías duplicadas")

# 4. Eliminar suscripciones duplicadas (mantener la más reciente)
print("\n4. Eliminando suscripciones duplicadas...")
cursor.execute("""
    DELETE FROM subscription 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM subscription 
        GROUP BY user_id, payment_id
    )
""")
deleted_subscriptions = cursor.rowcount
print(f"   ✅ Eliminadas {deleted_subscriptions} suscripciones duplicadas")

# 5. Limpiar referencias huérfanas
print("\n5. Limpiando referencias huérfanas...")

# Eliminar membresías sin usuario
cursor.execute("""
    DELETE FROM membership 
    WHERE user_id NOT IN (SELECT id FROM user)
""")
orphan_memberships = cursor.rowcount
print(f"   ✅ Eliminadas {orphan_memberships} membresías huérfanas")

# Eliminar pagos sin usuario
cursor.execute("""
    DELETE FROM payment 
    WHERE user_id NOT IN (SELECT id FROM user)
""")
orphan_payments = cursor.rowcount
print(f"   ✅ Eliminados {orphan_payments} pagos huérfanos")

# Eliminar suscripciones sin usuario o sin pago
cursor.execute("""
    DELETE FROM subscription 
    WHERE user_id NOT IN (SELECT id FROM user)
    OR payment_id NOT IN (SELECT id FROM payment)
""")
orphan_subscriptions = cursor.rowcount
print(f"   ✅ Eliminadas {orphan_subscriptions} suscripciones huérfanas")

# Confirmar cambios
conn.commit()

# Mostrar resumen final
print("\n=== Resumen ===")
cursor.execute("SELECT COUNT(*) FROM user")
users = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM membership")
memberships = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM payment")
payments = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM subscription")
subscriptions = cursor.fetchone()[0]

print(f"Usuarios: {users}")
print(f"Membresías: {memberships}")
print(f"Pagos: {payments}")
print(f"Suscripciones: {subscriptions}")

conn.close()
print("\n✅ Proceso completado")




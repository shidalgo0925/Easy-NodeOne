#!/usr/bin/env python3
"""
Script para buscar un pago específico por código EBOWR
"""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

try:
    from app import app, db, Payment, User, Cart, CartItem
    import json
    
    with app.app_context():
        print("\n" + "="*70)
        print("🔍 BUSCANDO PAGO CON CÓDIGO EBOWR-38807178")
        print("="*70 + "\n")
        
        codigo_buscado = "EBOWR-38807178"
        codigo_sin_prefijo = "38807178"
        
        # Buscar en diferentes campos
        print("1️⃣ Buscando por referencia exacta...")
        print("-" * 70)
        
        # Buscar por referencia exacta
        payment_exact = Payment.query.filter(
            Payment.payment_reference == codigo_buscado
        ).first()
        
        if payment_exact:
            print(f"✅ ENCONTRADO por referencia exacta:")
            user = User.query.get(payment_exact.user_id)
            print(f"   ID: {payment_exact.id}")
            print(f"   Usuario: {user.email if user else 'N/A'}")
            print(f"   Monto: ${payment_exact.amount / 100:.2f}")
            print(f"   Estado: {payment_exact.status}")
            print(f"   Referencia: {payment_exact.payment_reference}")
            print(f"   Método: {payment_exact.payment_method}")
            print(f"   Creado: {payment_exact.created_at}")
        else:
            print("❌ No encontrado por referencia exacta")
        
        print()
        
        # Buscar por código parcial (sin prefijo)
        print("2️⃣ Buscando por código parcial (38807178)...")
        print("-" * 70)
        
        payments_partial = Payment.query.filter(
            Payment.payment_reference.like(f'%{codigo_sin_prefijo}%')
        ).all()
        
        if payments_partial:
            print(f"✅ Encontrados {len(payments_partial)} pagos con código parcial:")
            for p in payments_partial:
                user = User.query.get(p.user_id)
                print(f"   ID: {p.id} | Referencia: {p.payment_reference} | Estado: {p.status} | Usuario: {user.email if user else 'N/A'}")
        else:
            print("❌ No encontrado por código parcial")
        
        print()
        
        # Buscar en payment_url
        print("3️⃣ Buscando en payment_url...")
        print("-" * 70)
        
        payments_url = Payment.query.filter(
            Payment.payment_url.like(f'%{codigo_buscado}%')
        ).all()
        
        if not payments_url:
            payments_url = Payment.query.filter(
                Payment.payment_url.like(f'%{codigo_sin_prefijo}%')
            ).all()
        
        if payments_url:
            print(f"✅ Encontrados {len(payments_url)} pagos en URL:")
            for p in payments_url:
                user = User.query.get(p.user_id)
                print(f"   ID: {p.id} | URL: {p.payment_url[:80]}... | Estado: {p.status} | Usuario: {user.email if user else 'N/A'}")
        else:
            print("❌ No encontrado en payment_url")
        
        print()
        
        # Buscar en metadata (si existe)
        print("4️⃣ Buscando en metadata...")
        print("-" * 70)
        
        all_payments = Payment.query.filter(
            Payment.payment_method == 'yappy'
        ).all()
        
        found_in_metadata = []
        for p in all_payments:
            if hasattr(p, 'metadata') and p.metadata:
                try:
                    metadata_str = str(p.metadata)
                    if codigo_buscado in metadata_str or codigo_sin_prefijo in metadata_str:
                        found_in_metadata.append(p)
                except:
                    pass
        
        if found_in_metadata:
            print(f"✅ Encontrados {len(found_in_metadata)} pagos en metadata:")
            for p in found_in_metadata:
                user = User.query.get(p.user_id)
                print(f"   ID: {p.id} | Metadata: {str(p.metadata)[:100]}... | Estado: {p.status} | Usuario: {user.email if user else 'N/A'}")
        else:
            print("❌ No encontrado en metadata")
        
        print()
        
        # Buscar TODOS los pagos de Yappy pendientes
        print("5️⃣ TODOS los pagos pendientes de Yappy:")
        print("-" * 70)
        
        all_yappy_pending = Payment.query.filter(
            Payment.payment_method == 'yappy',
            Payment.status.in_(['pending', 'awaiting_confirmation'])
        ).order_by(Payment.created_at.desc()).all()
        
        if all_yappy_pending:
            print(f"📋 Encontrados {len(all_yappy_pending)} pagos pendientes de Yappy:\n")
            for p in all_yappy_pending:
                user = User.query.get(p.user_id)
                print(f"   ID: {p.id}")
                print(f"   Referencia: {p.payment_reference}")
                print(f"   URL: {p.payment_url[:100] if p.payment_url else 'N/A'}...")
                print(f"   Estado: {p.status}")
                print(f"   Usuario: {user.email if user else 'N/A'}")
                print(f"   Creado: {p.created_at}")
                print()
        else:
            print("ℹ️ No hay pagos pendientes de Yappy")
        
        print()
        
        # Buscar si hay alguna transformación del código
        print("6️⃣ Verificando transformaciones del código...")
        print("-" * 70)
        
        # Verificar si el código EBOWR puede ser transformado
        print(f"   Código original: {codigo_buscado}")
        print(f"   Código sin prefijo: {codigo_sin_prefijo}")
        print(f"   Posibles variaciones:")
        print(f"      - {codigo_buscado.lower()}")
        print(f"      - {codigo_buscado.replace('-', '')}")
        print(f"      - YAPPY-{codigo_sin_prefijo}")
        
        # Buscar con variaciones
        variations = [
            codigo_buscado.lower(),
            codigo_buscado.replace('-', ''),
            f"YAPPY-{codigo_sin_prefijo}",
            codigo_sin_prefijo
        ]
        
        found_variations = []
        for var in variations:
            p = Payment.query.filter(
                Payment.payment_reference.like(f'%{var}%')
            ).first()
            if p:
                found_variations.append((var, p))
        
        if found_variations:
            print(f"\n   ✅ Encontrado con variaciones:")
            for var, p in found_variations:
                user = User.query.get(p.user_id)
                print(f"      Variación '{var}': Pago ID {p.id} - {p.payment_reference} - {user.email if user else 'N/A'}")
        else:
            print(f"\n   ❌ No encontrado con ninguna variación")
        
        print()
        
        # Resumen final
        print("="*70)
        print("📊 RESUMEN")
        print("="*70)
        
        total_found = len(payments_partial) + len(payments_url) + len(found_in_metadata)
        if payment_exact:
            total_found += 1
        
        if total_found == 0:
            print(f"❌ NO se encontró ningún pago con el código {codigo_buscado}")
            print(f"\n💡 Posibles razones:")
            print(f"   1. El código es de Yappy pero no está guardado en nuestra BD")
            print(f"   2. El pago se creó con otra referencia (YAPPY-XXXXXXXX)")
            print(f"   3. El código EBOWR es el código de comprobante de Yappy, no nuestra referencia interna")
            print(f"\n💡 Solución:")
            print(f"   - El usuario debe usar el código EBOWR-38807178 en el endpoint de verificación")
            print(f"   - El sistema buscará en pagos pendientes y actualizará la referencia")
        else:
            print(f"✅ Se encontraron {total_found} coincidencias")
        
        print("\n" + "="*70 + "\n")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

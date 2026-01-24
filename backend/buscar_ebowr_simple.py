#!/usr/bin/env python3
"""
Buscar pago específico con código EBOWR-38807178
"""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

try:
    from app import app, db, Payment, User
    
    codigo = "EBOWR-38807178"
    codigo_num = "38807178"
    
    with app.app_context():
        print("\n" + "="*70)
        print(f"🔍 BUSCANDO PAGO: {codigo}")
        print("="*70 + "\n")
        
        # Buscar en payment_reference
        print("1. Buscando en payment_reference...")
        p1 = Payment.query.filter(Payment.payment_reference == codigo).first()
        if not p1:
            p1 = Payment.query.filter(Payment.payment_reference.like(f'%{codigo_num}%')).first()
        
        # Buscar en payment_url
        print("2. Buscando en payment_url...")
        p2 = Payment.query.filter(Payment.payment_url.like(f'%{codigo}%')).first()
        if not p2:
            p2 = Payment.query.filter(Payment.payment_url.like(f'%{codigo_num}%')).first()
        
        # Buscar TODOS los pagos de Yappy para revisar
        print("3. Revisando TODOS los pagos de Yappy...")
        todos_yappy = Payment.query.filter(Payment.payment_method == 'yappy').order_by(Payment.created_at.desc()).all()
        
        encontrado = None
        
        if p1:
            encontrado = p1
            print(f"✅ ENCONTRADO en payment_reference!")
        elif p2:
            encontrado = p2
            print(f"✅ ENCONTRADO en payment_url!")
        else:
            # Buscar en todos los campos
            print("4. Buscando en todos los campos de pagos Yappy...")
            for p in todos_yappy:
                ref = str(p.payment_reference or '')
                url = str(p.payment_url or '')
                if codigo in ref or codigo_num in ref or codigo in url or codigo_num in url:
                    encontrado = p
                    print(f"✅ ENCONTRADO en pago ID {p.id}!")
                    break
        
        if encontrado:
            user = User.query.get(encontrado.user_id)
            print("\n" + "="*70)
            print("📄 DETALLES DEL PAGO ENCONTRADO:")
            print("="*70)
            print(f"ID: {encontrado.id}")
            print(f"Usuario: {user.email if user else 'N/A'} ({user.first_name} {user.last_name if user else ''})")
            print(f"Monto: ${encontrado.amount / 100:.2f}")
            print(f"Estado: {encontrado.status}")
            print(f"Referencia: {encontrado.payment_reference}")
            print(f"URL: {encontrado.payment_url}")
            print(f"Creado: {encontrado.created_at}")
            print(f"Pagado: {encontrado.paid_at if encontrado.paid_at else 'No pagado'}")
            print("="*70 + "\n")
        else:
            print("\n" + "="*70)
            print(f"❌ NO SE ENCONTRÓ ningún pago con código {codigo}")
            print("="*70)
            print(f"\n📋 Total de pagos Yappy en BD: {len(todos_yappy)}")
            if todos_yappy:
                print("\nÚltimos 5 pagos de Yappy:")
                for p in todos_yappy[:5]:
                    user = User.query.get(p.user_id)
                    print(f"  - ID {p.id}: {p.payment_reference} | Estado: {p.status} | Usuario: {user.email if user else 'N/A'}")
            print()
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

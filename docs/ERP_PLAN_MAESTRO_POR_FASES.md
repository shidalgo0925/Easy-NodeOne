# Plan Maestro ERP Easy NodeOne

## Objetivo general
Convertir Easy NodeOne en un ERP modular con:

- Contabilidad general
- Facturación
- Cuentas por cobrar
- Pagos
- Bancos
- Conciliación bancaria
- Cuentas por pagar
- Impuestos
- Reportes financieros

Regla principal:

**Todo movimiento financiero debe terminar en un asiento contable balanceado.**

## Orden estricto de desarrollo

1. Fase 0 - Preparación
2. Fase 1 - Motor contable
3. Fase 2 - Facturación contable
4. Fase 3 - CxC
5. Fase 4 - Pagos
6. Fase 5 - Bancos y caja
7. Fase 6 - Conciliación bancaria
8. Fase 7 - CxP
9. Fase 8 - Impuestos Panamá
10. Fase 9 - Reportes financieros

No avanzar a la siguiente fase si la anterior no cumple su criterio de aceptación.

---

## FASE 0 - Preparación y reglas base

### Objetivo
Ordenar el desarrollo antes de tocar código crítico.

### Alcance
- Revisar modelos actuales de cotizaciones, facturas, clientes, pagos.
- Identificar tablas reutilizables.
- No borrar lógica existente.
- Separar módulos: `accounting`, `invoicing`, `payments`, `banking`, `reconciliation`, `purchases`.

### Entregable
Documento técnico corto con:
- Tablas existentes
- Tablas nuevas
- Tablas a modificar
- Riesgos

### Criterio de aceptación
Debe quedar claro:
- Qué existe
- Qué falta
- Qué se tocará
- Qué no se tocará

---

## FASE 1 - Motor contable

### Objetivo
Crear el corazón del ERP.

### Modelos mínimos
- `Account`
- `Journal`
- `JournalEntry`
- `JournalItem`

### Reglas obligatorias
- No publicar si `debit != credit`.
- Asiento publicado no se edita.
- Corrección por reversión.
- Todo asiento pertenece a una organización.
- Todo asiento tiene diario.
- En una línea no se permiten débito y crédito simultáneos.
- No se aceptan valores negativos.

### Pantallas mínimas
- Plan de cuentas
- Diarios
- Asientos
- Detalle de asiento

### Botones mínimos
- Crear asiento
- Guardar borrador
- Publicar
- Reversar

### Criterio de aceptación
- Crear cuentas
- Crear diarios
- Crear asiento manual
- Validar balance
- Publicar
- Reversar
- Ver asiento publicado sin edición

---

## FASE 2 - Facturación conectada a contabilidad

### Objetivo
Toda factura validada debe generar asiento automático.

### Flujo
Cotización aprobada -> Factura borrador -> Factura validada -> Asiento automático -> CxC creada

### Regla contable base
- Venta:
  - Debe: CxC
  - Haber: Ingresos
- Con impuesto:
  - Debe: CxC
  - Haber: Ingresos
  - Haber: ITBMS por pagar

### Criterio de aceptación
- Cotización genera factura
- Validación genera asiento cuadrado
- Saldo pendiente calculado
- Factura validada no editable (solo nota/cancelación controlada)

---

## FASE 3 - Cuentas por cobrar (CxC)

### Objetivo
Formalizar saldo pendiente por cliente.

### Modelo sugerido
`AccountReceivable` con estados `open`, `partial`, `paid`, `overdue`.

### Reglas
- Toda factura validada crea CxC.
- Saldo CxC = saldo factura.
- Pago parcial -> `partial`.
- Pago total -> `paid`.
- Vencida con saldo -> `overdue`.

### Criterio de aceptación
Ver deuda por cliente, origen, saldo y vencidos.

---

## FASE 4 - Pagos de clientes

### Objetivo
Registrar pagos contra facturas.

### Modelo
`Payment` con métodos (`cash`, `bank_transfer`, `card`, `online`, `yappy`, `paypal`, `other`).

### Regla contable
Al confirmar pago:
- Debe: Banco/Caja
- Haber: CxC

### Criterio de aceptación
Pago desde factura, parcial/total, saldo actualizado, asiento visible.

---

## FASE 5 - Bancos y caja

### Objetivo
Gestionar cuentas bancarias/caja y movimientos.

### Modelos
- `BankAccount`
- `BankTransaction`

### Criterio de aceptación
Crear bancos/caja, asociar cuenta contable, ver movimientos y relación con pagos.

---

## FASE 6 - Conciliación bancaria

### Objetivo
Cruzar movimientos de banco contra sistema.

### Matching automático
- Mismo monto
- Fecha cercana
- Referencia similar
- Cliente relacionado cuando aplique

### Estados
- No conciliado
- Sugerido
- Conciliado
- Diferencia pendiente

### Criterio de aceptación
Ver no conciliados, sugerencias, conciliación manual, evitar doble conciliación.

---

## FASE 7 - Cuentas por pagar (CxP)

### Objetivo
Agregar compras y obligaciones con proveedores.

### Flujo
Factura proveedor -> CxP -> Pago proveedor -> Banco -> Conciliación

### Modelo
`VendorBill`

### Asientos
- Factura proveedor:
  - Debe: Gasto/Inventario/Activo
  - Debe: ITBMS crédito fiscal
  - Haber: CxP
- Pago proveedor:
  - Debe: CxP
  - Haber: Banco/Caja

### Criterio de aceptación
Registrar factura, generar CxP, pagar parcial/total y ver saldo proveedor.

---

## FASE 8 - Impuestos Panamá

### Objetivo
Soporte fiscal de ITBMS.

### Incluye
- Configuración de impuestos
- ITBMS 7%
- Exento
- No sujeto
- Reporte de impuesto cobrado/pagado

### Modelo
`Tax` con tipo `sale`/`purchase`.

### Criterio de aceptación
Aplicar impuesto en venta/compra, asiento correcto, resumen fiscal.

---

## FASE 9 - Reportes financieros

### Objetivo
Reportes ERP reales derivados de asientos.

### Reportes mínimos
- Balance general
- Estado de resultados
- Libro diario
- Mayor general
- CxC por cliente
- CxP por proveedor
- Aging CxC
- Aging CxP
- Flujo de caja
- Bancos conciliados/no conciliados

### Criterio de aceptación
Todos los reportes salen desde asientos contables, no desde facturas aisladas.

---

## Instrucción directa para implementación

- Arquitectura contable modular, no monolítica.
- No mezclar todo en una sola tabla.
- No resolver con estados manuales desconectados.
- Primero motor contable (fase 1), luego conexión progresiva por fases.
- Cada fase debe cerrarse funcional y probada antes de avanzar.

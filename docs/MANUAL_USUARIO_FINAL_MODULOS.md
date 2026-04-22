# Manual de Usuario Final

## Modulos cubiertos

- Usuarios
- Taller
- Cotizaciones
- Facturas

Este manual esta pensado para operacion diaria. Los nombres de botones pueden variar levemente segun permisos o configuracion de tu organizacion.

---

## 1) Modulo de Usuarios

### Objetivo
Crear, editar y administrar miembros internos de la organizacion (incluye vendedores).

### Paso a paso: crear un usuario

1. Entra al panel de administracion.
2. Ve a **Usuarios**.
3. Haz clic en **Nuevo usuario** (o boton similar de alta).
4. Completa los campos obligatorios:
   - Nombre
   - Apellido
   - Correo
   - Estado activo/inactivo
5. Si ese usuario tambien sera vendedor, activa la opcion **Es vendedor**.
6. Guarda.
7. Verifica que el usuario aparezca en el listado.

### Paso a paso: editar un usuario

1. En **Usuarios**, ubica el registro en la tabla.
2. Haz clic en **Editar**.
3. Actualiza los campos necesarios.
4. Guarda cambios.
5. Confirma que los datos nuevos se reflejen en el listado.

### Paso a paso: desactivar un usuario

1. Abre el usuario en modo edicion.
2. Cambia el estado a **Inactivo**.
3. Guarda.
4. Verifica que ya no aparezca como activo en buscadores operativos.

### Buenas practicas

- Usa correos reales y unicos.
- Marca **Es vendedor** solo para quienes cotizan/venden.
- No elimines historicos si hay documentos asociados; mejor desactiva.

---

## 2) Modulo de Taller

### Objetivo
Registrar y gestionar ordenes de trabajo de taller de principio a fin.

### Paso a paso: crear una orden de taller

1. Ve a **Taller** > **Ordenes**.
2. Haz clic en **Nueva orden**.
3. Selecciona o busca al cliente.
4. Registra los datos del vehiculo.
5. Agrega servicios o conceptos a la orden.
6. Guarda la orden en estado inicial (por ejemplo: borrador/abierta).

### Paso a paso: actualizar avance de la orden

1. Abre la orden desde el listado.
2. Cambia los campos de proceso (estado, notas internas, observaciones).
3. Si aplica, actualiza servicios y montos.
4. Guarda cambios.

### Paso a paso: cerrar orden

1. Verifica que los trabajos esten completos.
2. Revisa totales y observaciones finales.
3. Cambia el estado a **Finalizada/Cerrada**.
4. Guarda.

### Buenas practicas

- Siempre vincula la orden a un cliente correcto.
- Usa notas internas para trazabilidad de decisiones.
- Evita cerrar sin validar servicios y total final.

---

## 3) Modulo de Cotizaciones

### Objetivo
Preparar propuestas comerciales editables para el cliente.

### Paso a paso: crear una cotizacion

1. Ve a **Ventas** > **Cotizaciones**.
2. Haz clic en **Nueva cotizacion**.
3. Selecciona cliente.
4. Selecciona vendedor (si aplica).
5. Define fecha de validez y terminos de pago.
6. Agrega lineas:
   - Producto/servicio
   - Descripcion
   - Cantidad
   - Precio unitario
   - Impuesto
7. Guarda.

### Paso a paso: editar cotizacion (estilo Odoo)

1. Desde el listado, abre la cotizacion.
2. Edita cabecera (cliente, vendedor, validez, terminos) si esta en borrador.
3. Edita lineas:
   - Puedes agregar, quitar o cambiar lineas.
   - Puedes agregar notas o secciones.
4. Revisa subtotal, impuestos y total.
5. Guarda.

### Paso a paso: enviar cotizacion por correo

1. Abre la cotizacion.
2. Haz clic en **Enviar por correo**.
3. Completa:
   - Para
   - Asunto
   - Mensaje
4. (Opcional) Mantener activo **Adjuntar PDF**.
5. Envia y confirma mensaje de exito.

### Paso a paso: confirmar cotizacion

1. Asegura que las lineas y montos sean correctos.
2. Haz clic en **Confirmar**.
3. Verifica cambio de estado.

### Buenas practicas

- No confirmes cotizaciones incompletas.
- Usa impuestos correctos segun tipo de venta.
- Mantener vendedor correcto mejora reportes.

---

## 4) Modulo de Facturas

### Objetivo
Emitir, editar y gestionar facturas con flujo operativo completo.

### Paso a paso: crear factura

Opciones comunes:

- Desde cotizacion confirmada: usar **Crear factura**.
- Desde listado de facturas: **Crear factura** manual.

Pasos:

1. Entra a **Facturas**.
2. Crea factura nueva o desde cotizacion.
3. Abre la ficha de factura.
4. Completa/valida:
   - Cliente
   - Vendedor (si aplica)
   - Fecha
   - Vencimiento
   - Lineas e impuestos
5. Guarda en **borrador**.

### Paso a paso: editar factura

1. Abre la factura desde listado.
2. Si esta en **borrador**, puedes editar cabecera y lineas.
3. Ajusta cantidades, precios e impuestos.
4. Guarda.

Nota: fuera de borrador, la edicion es limitada por reglas de negocio.

### Paso a paso: contabilizar (postear) factura

1. Revisa que todo este correcto.
2. Haz clic en **Contabilizar** (o **Post**).
3. Verifica cambio de estado a contabilizada/publicada.

### Paso a paso: registrar pago

1. Abre factura contabilizada.
2. Haz clic en **Registrar pago** (o **Pagar**).
3. Verifica estado final **Pagada**.

### Paso a paso: cancelar factura

1. Abre la factura.
2. Haz clic en **Cancelar factura**.
3. Confirma la accion.
4. Verifica estado **Cancelada**.

### Paso a paso: eliminar factura

1. Solo aplica para facturas en borrador.
2. Haz clic en **Eliminar**.
3. Confirma.

### Buenas practicas

- Factura borrador: etapa de correccion.
- Factura contabilizada: no alterar sin criterio contable.
- Evitar eliminar historicos; preferir estados y trazabilidad.

---

## 5) Datos fiscales de la empresa (impacta cotizacion y factura)

Para que salgan bien los datos del emisor:

1. Ve a **Empresas** (o **Identidad** segun tu rol).
2. Completa perfil fiscal:
   - Razon social
   - RUC/NIT
   - Regimen fiscal
   - Direccion fiscal
   - Ciudad/Estado/Pais
   - Telefono y email fiscal
3. Guarda.
4. Verifica en vista de cotizacion/factura y en PDF.

---

## 6) Checklist operativo diario

- Usuarios:
  - Nuevo usuario con correo correcto
  - Vendedor marcado cuando corresponda
- Taller:
  - Orden abierta con cliente y vehiculo correctos
  - Estado actualizado durante el proceso
- Cotizaciones:
  - Total e impuestos revisados
  - Enviada y/o confirmada cuando aplique
- Facturas:
  - Borrador validado
  - Contabilizada y luego pagada segun flujo

---

## 7) Problemas comunes y solucion rapida

### No veo un modulo en menu

- Revisa permisos del usuario.
- Revisa que el modulo SaaS este habilitado para tu organizacion.

### No puedo editar una cotizacion/factura

- Verifica estado del documento.
- Normalmente solo en borrador se puede editar todo.

### No aparece vendedor en busqueda

- Validar que el usuario este activo y tenga marcado **Es vendedor**.

### No salen datos fiscales en documentos

- Completar perfil fiscal de empresa y guardar.
- Recargar la vista del documento.

---

## 8) Sugerencia para version Word

Cuando lo pases a Word:

- Agrega portada con logo y fecha de version.
- Usa estilos de titulo (Titulo 1, Titulo 2).
- Inserta capturas de pantalla por cada paso clave.
- Deja una pagina final con contactos de soporte.


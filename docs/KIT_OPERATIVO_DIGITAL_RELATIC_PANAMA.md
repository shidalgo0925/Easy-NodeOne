# KIT OPERATIVO DIGITAL — Easy NodeOne

Documento base para formalizar la operación tecnológica y garantizar autonomía institucional.

---

## 1. DOCUMENTO DE FORMALIZACIÓN DEL ROL TECNOLÓGICO

### 1.1 Cargo

**Arquitecto Digital / Director Tecnológico**

### 1.2 Objetivo del Rol

Diseñar, implementar y estructurar la plataforma digital institucional garantizando estabilidad, escalabilidad y documentación operativa.

### 1.3 Alcance de Responsabilidades

- Diseño de arquitectura tecnológica.
- Configuración y mantenimiento de la plataforma.
- Implementación de automatizaciones.
- Gestión de infraestructura digital.
- Seguridad y respaldos.
- Supervisión técnica de eventos digitales.
- Documentación operativa.

### 1.4 Funciones Excluidas

- Atención individual a usuarios finales.
- Soporte operativo básico documentado.
- Gestión administrativa interna.
- Comunicación institucional.

### 1.5 Dedicación

- **Modalidad:** Estratégica / Proyecto.
- **Tiempo estimado:** Definir horas mensuales.
- Soporte adicional sujeto a acuerdo.

### 1.6 Modelo de Vinculación

Seleccionar una opción formal:

**A. Prestación de Servicios**

- Honorario mensual.
- SLA definido.
- Alcance delimitado.

**B. Participación Estratégica**

- Porcentaje sobre membresías digitales.
- Participación en ingresos por eventos.
- Compensación diferida documentada.

---

## 2. PROPIEDAD TECNOLÓGICA

Debe quedar definido por escrito:

| Activo | Definición |
|--------|------------|
| Titularidad del dominio | Quién es el titular registrado. |
| Titularidad del hosting | Quién contrata y paga el servidor. |
| Propiedad del código | Repositorio y licencia institucional. |
| Custodia de base de datos | Quién administra y respalda. |
| Accesos root o superadmin | Listado y control de accesos. |
| Control de cuentas institucionales | Correos, redes, APIs. |

**Recomendación:** Todos los activos deben estar a nombre institucional con acceso controlado.

---

## 3. MANUAL DEL ADMINISTRADOR

### 3.1 Acceso al Sistema

1. Ingresar a la URL del portal.
2. Introducir usuario institucional.
3. Activar verificación si aplica.
4. Acceder al panel administrativo.

### 3.2 Aprobación de Miembros

1. Ir a módulo de **Miembros** (o Gestión → Usuarios/Miembros).
2. Revisar solicitudes pendientes.
3. Validar pago o documentación.
4. Aprobar / Rechazar.
5. Confirmar envío automático de correo.

### 3.3 Generación de Certificados

1. Acceder al módulo de **Eventos**.
2. Seleccionar evento.
3. Ver lista de asistentes confirmados.
4. Generar certificados.
5. Validar envío automático.

### 3.4 Revisión de Pagos

1. Acceder al módulo financiero (Pagos / Historial).
2. Filtrar por fecha o evento.
3. Verificar conciliación.
4. Exportar reporte en PDF o Excel.

### 3.5 Reportes

- Reporte de miembros activos.
- Reporte de ingresos.
- Reporte por evento.
- Reporte histórico anual.

### 3.6 Recuperación de Contraseña

1. Usuario usa “Olvidé contraseña”.
2. Verificar envío de correo automático.
3. Confirmar restablecimiento exitoso.

---

## 4. MANUAL DE EVENTO INTERNACIONAL

### 4.1 Checklist Previo

- [ ] Confirmar fecha y zona horaria.
- [ ] Crear evento en plataforma.
- [ ] Configurar formulario de inscripción.
- [ ] Configurar certificado automático.
- [ ] Configurar correo automático.
- [ ] Probar registro con usuario demo.
- [ ] Probar emisión de certificado.
- [ ] Activar recordatorio 24 horas antes.
- [ ] Confirmar grabación habilitada.
- [ ] Realizar backup previo al evento.

### 4.2 Durante el Evento

- Verificar asistencia.
- Confirmar estabilidad de la plataforma.
- Validar generación de constancias.

### 4.3 Después del Evento

- Exportar lista final.
- Enviar certificado a no descargados.
- Generar reporte de participación.
- Archivar grabación.

---

## 5. ESTRUCTURA DE ROLES

| Rol | Responsabilidades |
|-----|-------------------|
| **Administrador General** | Aprobar miembros. Gestionar certificados. Publicar eventos. Supervisar reportes. |
| **Coordinador de Eventos** | Crear eventos. Gestionar inscripciones. Confirmar asistencia. Coordinar horarios internacionales. |
| **Comunicación** | Enviar correos masivos. Publicar en redes. Seguimiento a inscritos. Confirmar recordatorios. |
| **Soporte Técnico** (si aplica) | Mantenimiento del sistema. Respaldo. Actualizaciones. Seguridad. |

---

## 6. MAPA DEL SISTEMA

### 6.1 Si opera sobre Odoo Community

- **CRM** → Gestión de contactos.
- **Portal** → Acceso miembros.
- **Ventas** → Inscripciones pagas.
- **Automatizaciones** → Correos y certificados.
- **Reportes** → Análisis financiero.
- **Base de datos** → Información centralizada.

**Dependencias:** Portal depende de CRM. Certificados dependen de evento confirmado. Reportes dependen de conciliación financiera.

### 6.2 Si opera sobre NodeOne / plataforma actual

- **Dashboard** → Panel de control y estado del usuario.
- **Gestión** → Miembros, Usuarios, Planes, Roles.
- **Servicios** → Catálogo, Citas, Disponibilidad.
- **Comunicaciones** → Correo institucional, SMTP, Notificaciones.
- **Eventos** → Creación, inscripciones, certificados.
- **Beneficios / Normativas** → Contenido y políticas.
- **Configuración** → Identidad, Email, Pagos, Respaldos.

**Dependencias:** Certificados y correos dependen de evento confirmado y configuración SMTP. Reportes dependen de datos de pagos y miembros.

---

## 7. CENTRALIZACIÓN DE CREDENCIALES

Debe existir un repositorio institucional que contenga:

- Acceso hosting.
- Dominio.
- Plataforma.
- Base de datos.
- Correos institucionales.
- APIs externas.
- Backup automatizado.

**Acceso compartido mínimo:** Presidencia + Dirección Tecnológica.

---

## 8. POLÍTICA DE SOPORTE

- Procesos documentados no se atienden individualmente.
- Consultas deben referenciar manual.
- Definir horario de atención.
- Definir canal oficial (correo o ticket).
- Establecer tiempos de respuesta.

---

## RESULTADO ESPERADO

Con esta estructura:

- Se elimina dependencia técnica informal.
- Se establece gobernanza digital.
- Se protege la propiedad tecnológica.
- Se profesionaliza la operación internacional.

---

*Documento base. Puede convertirse en: contrato formal, PDF institucional con diseño corporativo, manual detallado con índice expandido, o versión adaptada a junta directiva.*

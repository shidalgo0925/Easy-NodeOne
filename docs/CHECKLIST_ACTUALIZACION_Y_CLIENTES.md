# Checklist: despliegue y comunicación a clientes

Documento para **consultar en cada actualización** que llegue a clientes (o a sus entornos).  
Complementa la política técnica de [`REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) (solo desarrollo en dev, Git como fuente, pull por silo).

---

## Antes de tocar producción

1. **Código** mergeado y pusheado según el flujo acordado (p. ej. `develop` → `main`).
2. **Staging** actualizado (`git pull` en `staging/app`), dependencias y **migraciones** aplicadas si corresponde, **servicio reiniciado**.
3. **Validación en staging** hecha (flujos críticos que usan los clientes afectados).
4. Anotar **commit o tag** que vas a llevar a prod (para rastreo y rollback mental).

## Al actualizar prod (y relatic si aplica)

1. Ventana acordada (si los clientes son sensibles al downtime).
2. En `prod/app` (y `relatic/app` si toca): `git pull` al commit/tag acordado.
3. **Migraciones** si hubo cambios de esquema.
4. **Reinicio** del servicio systemd correspondiente.
5. **Verificación mínima** (login, pantalla clave, API crítica).
6. Registrar en tu bitácora interna: **fecha**, **entorno**, **commit**, **quién**.

## Antes de avisar a clientes

- Confirmar que **prod** (y otros entornos que usen) está estable tras el reinicio.
- Tener claro **qué cambió en lenguaje de negocio** (no hace falta tecnicismos).
- Definir **si hay acción requerida** por parte del cliente (cambiar contraseña, nueva URL, etc.).

## Plantilla breve para el mensaje al cliente

Puedes copiar y completar:

```text
Asunto: Actualización del sistema [nombre producto / Easy NodeOne] – [fecha]

Hemos publicado una actualización con las siguientes mejoras o correcciones:
- [punto 1, beneficio claro]
- [punto 2]

[Si aplica] Deben [acción concreta].
[Si no aplica] No necesitan hacer nada especial.

Si notan algún inconveniente, [canal de soporte acordado].
```

## Dónde guardar el texto “para clientes”

- Para **comunicados largos o histórico**: podés usar `docs/root/` con nombre fechado, p. ej. `ANUNCIO_ACTUALIZACION_YYYY-MM-DD.md`, o el proceso que ya usen para anuncios.
- Este archivo (**`docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`**) es la **checklist fija**; los anuncios concretos pueden ser archivos aparte por release.

## Resumen en una frase

**No avisar a clientes hasta** que staging esté validado, prod actualizado y verificado; **dejar escrito** qué versión salió y qué les comunicaste.

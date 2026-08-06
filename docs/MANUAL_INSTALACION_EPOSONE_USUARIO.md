# EPosOne — Manual oficial de instalación (usuario / administrador)

| Campo | Valor |
|-------|--------|
| Audiencia | Dueño del negocio / admin que instala la tablet |
| No es para | Cajero día a día → ver [`MANUAL_CAJERO_EPOSONE_USUARIO.md`](MANUAL_CAJERO_EPOSONE_USUARIO.md) |
| Versión | 1.0 |
| Fecha | 6 ago 2026 |
| Flujo oficial | Onboarding V2 (ADR-027) — **siempre con cuenta EN1** |

**Principio:** primero te registrás en EN1; después vinculás la tablet. Standalone no significa “sin EN1”: significa que no sincronizás operación cloud día a día.

---

## 1. Qué vas a lograr

Pasar de “no conozco EPosOne” a “la tablet está lista para que el cajero entre con PIN”.

---

## 2. Camino recomendado (nuevo negocio)

| Paso | Dónde | Qué hacés |
|------|--------|-----------|
| 1 | Navegador | Entrá al sitio EPosOne → **`/start`** |
| 2 | `/start` | Tipo de negocio → plan (Standalone o Connected) → cuenta → negocio → legales |
| 3 | Pantalla final | Anotá el **código** o abrí **Panel de instalación** |
| 4 | Tablet | Descargá la app (Play / enlace del panel) |
| 5 | Tablet | Pegá o escaneá el **código** (o QR) |
| 6 | Tablet | Esperá la configuración (bootstrap) |
| 7 | EN1 | Creá cajeros con PIN (si aún no) |
| 8 | Tablet | El cajero entra con PIN y abre turno |

Panel web: **`/admin/eposone/install`** (también en el menú «Instalar dispositivo»).

---

## 3. Si ya tenés cuenta EN1

1. Abrí la app → **Tengo cuenta** (cuando Gate 2 APK esté listo) **o** usá el panel web.  
2. Iniciá sesión con el email del negocio.  
3. Elegí organización / caja.  
4. Generá código (o usá el del panel) → vinculá tablet → PIN.

---

## 4. Código y QR

| Concepto | Uso |
|----------|-----|
| **Código de aprovisionamiento** | Vincula **esta tablet** a **esta caja** · un solo uso · caduca (~30 min) |
| **QR técnico** | Contiene **solo** ese código · escanear = pegar el código |
| **PIN de cajero** | No es el código de instalación |

Si el código expiró: en el panel → **Renovar código** / **Generar código**.

---

## 5. Standalone vs Connected

| Modalidad | En la práctica |
|-----------|----------------|
| **Standalone** | Cuenta + org + suscripción en EN1; la tablet **no** depende de sync cloud operativa diaria |
| **Connected** | Igual registro + sincronización con EN1 (catálogo, config, operación) |

Ambas se contratan y se instalan igual. La diferencia es cómo opera el POS después.

---

## 6. Reemplazo o reinstalación de tablet

1. Entrá al panel de instalación (o «Tengo cuenta» en la app).  
2. Generá un **código nuevo** para la misma caja.  
3. En la tablet nueva/reinstalada: URL del servidor + código.  
4. La licencia es de la **caja**, no de la tablet anterior.

---

## 7. Problemas frecuentes

| Situación | Qué hacer |
|-----------|-----------|
| Código no sirve | Renovar en el panel; no reutilizar uno viejo |
| «Sin licencia» | Admin: licencia de la **caja** en EN1 |
| Olvidé el email de `/start` | Recuperación de cuenta EN1 / soporte |
| App pide código otra vez | Tablet no quedó vinculada o se reinstaló → nuevo código |
| Cajero no puede entrar | Crear cajero + PIN en EN1; no confundir con código de install |

---

## 8. Checklist rápido

- [ ] Completé `/start` (o ya tengo org en EN1)  
- [ ] Descargué la app  
- [ ] Código o QR vigentes  
- [ ] Tablet muestra caja vinculada  
- [ ] Hay al menos un cajero con PIN  
- [ ] Probé abrir turno  

---

## Referencias técnicas (equipo)

| Tema | Doc |
|------|-----|
| Freeze HTTP Gate 1 (LOCAL) | `Doc/EN1_ONBOARDING_P0/GATE1_HTTP_FROZEN_FOR_LOCAL.md` · tag `eposone-onboarding-p0-v1.3` |
| Contratos | `docs/eposone-onboarding/` |
| Manual cajero | [`MANUAL_CAJERO_EPOSONE_USUARIO.md`](MANUAL_CAJERO_EPOSONE_USUARIO.md) |

*Los nombres de botones pueden variar levemente según versión de la app.*

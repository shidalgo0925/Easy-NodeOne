# Plantillas modelo para email marketing (HTML con estilos inline, compatibles con clientes de correo)
# Variables soportadas: {{ nombre }}, {{ email }}, {{ unsubscribe_url }}, {{ base_url }}

TEMPLATE_MODELS = [
    {
        "id": "blank",
        "name": "En blanco",
        "description": "Contenido mínimo para empezar desde cero",
        "html": """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: #fff;">
<tr><td style="padding: 24px;">
<p>Hola {{ nombre }},</p>
<p>Tu contenido aquí.</p>
<p style="font-size: 12px; color: #666;"><a href="{{ unsubscribe_url }}">Darse de baja</a></p>
</td></tr>
</table>
</body>
</html>""",
    },
    {
        "id": "newsletter",
        "name": "Newsletter simple",
        "description": "Una columna, título, texto y botón CTA",
        "html": """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: #ffffff;">
<tr><td style="padding: 32px 24px; border-bottom: 3px solid #0d6efd;">
<h1 style="margin:0; font-size: 24px; color: #333;">Título del newsletter</h1>
</td></tr>
<tr><td style="padding: 24px;">
<p style="margin: 0 0 16px; font-size: 16px; line-height: 1.5; color: #333;">Hola {{ nombre }},</p>
<p style="margin: 0 0 24px; font-size: 16px; line-height: 1.5; color: #555;">Escribe aquí el contenido principal de tu newsletter. Puedes usar varias líneas.</p>
<table cellpadding="0" cellspacing="0"><tr><td style="background-color: #0d6efd; padding: 14px 28px; border-radius: 6px;">
<a href="#" style="color: #fff; text-decoration: none; font-weight: bold;">Ver más</a>
</td></tr></table>
</td></tr>
<tr><td style="padding: 16px 24px; background: #f8f9fa; font-size: 12px; color: #666;">
Si no deseas recibir estos correos, <a href="{{ unsubscribe_url }}" style="color: #0d6efd;">darse de baja</a>.
</td></tr>
</table>
</body>
</html>""",
    },
    {
        "id": "promo",
        "name": "Promoción / Oferta",
        "description": "Destacado para ofertas y descuentos",
        "html": """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: #fff;">
<tr><td style="padding: 24px; background: linear-gradient(135deg, #198754 0%, #20c997 100%); background-color: #198754;">
<h1 style="margin:0; font-size: 22px; color: #fff;">Oferta especial</h1>
<p style="margin: 8px 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">Solo por tiempo limitado</p>
</td></tr>
<tr><td style="padding: 24px;">
<p style="margin: 0 0 16px; font-size: 16px; color: #333;">Hola {{ nombre }},</p>
<p style="margin: 0 0 20px; font-size: 16px; color: #555;">Te ofrecemos un descuento exclusivo. Aprovecha esta oportunidad.</p>
<table cellpadding="0" cellspacing="0"><tr><td style="background-color: #198754; padding: 16px 32px; border-radius: 6px;">
<a href="#" style="color: #fff; text-decoration: none; font-weight: bold; font-size: 16px;">Aprovechar oferta</a>
</td></tr></table>
</td></tr>
<tr><td style="padding: 16px 24px; background: #f8f9fa; font-size: 12px; color: #666;">
<a href="{{ unsubscribe_url }}">Cancelar suscripción</a>
</td></tr>
</table>
</body>
</html>""",
    },
    {
        "id": "announcement",
        "name": "Anuncio institucional",
        "description": "Formato formal para comunicados",
        "html": """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; font-family: Georgia, serif; background-color: #f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: #fff;">
<tr><td style="padding: 28px 24px; border-bottom: 1px solid #dee2e6;">
<h1 style="margin:0; font-size: 20px; color: #212529; font-weight: 600;">Comunicado oficial</h1>
</td></tr>
<tr><td style="padding: 28px 24px;">
<p style="margin: 0 0 12px; font-size: 15px; color: #333;">Estimado/a {{ nombre }},</p>
<p style="margin: 0 0 16px; font-size: 15px; line-height: 1.6; color: #495057;">Por medio del presente les informamos el siguiente anuncio. Redacte aquí el contenido del comunicado.</p>
<p style="margin: 0; font-size: 15px; color: #495057;">Atentamente,<br>El equipo</p>
</td></tr>
<tr><td style="padding: 16px 24px; background: #f8f9fa; font-size: 12px; color: #6c757d;">
<a href="{{ unsubscribe_url }}">Dejar de recibir estos correos</a>
</td></tr>
</table>
</body>
</html>""",
    },
    {
        "id": "event",
        "name": "Evento / Invitación",
        "description": "Fecha, lugar y botón de confirmación",
        "html": """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: #fff;">
<tr><td style="padding: 24px; background-color: #6f42c1;">
<h1 style="margin:0; font-size: 22px; color: #fff;">Invitación al evento</h1>
</td></tr>
<tr><td style="padding: 24px;">
<p style="margin: 0 0 16px; font-size: 16px; color: #333;">Hola {{ nombre }},</p>
<p style="margin: 0 0 20px; font-size: 16px; color: #555;">Te invitamos a nuestro evento.</p>
<table width="100%" cellpadding="12" cellspacing="0" style="background: #f8f9fa; border-radius: 6px; margin-bottom: 20px;">
<tr><td style="font-size: 14px; color: #333;"><strong>Fecha:</strong> [Indique fecha]</td></tr>
<tr><td style="font-size: 14px; color: #333;"><strong>Lugar:</strong> [Indique lugar]</td></tr>
</table>
<table cellpadding="0" cellspacing="0"><tr><td style="background-color: #6f42c1; padding: 14px 28px; border-radius: 6px;">
<a href="#" style="color: #fff; text-decoration: none; font-weight: bold;">Confirmar asistencia</a>
</td></tr></table>
</td></tr>
<tr><td style="padding: 16px 24px; background: #f8f9fa; font-size: 12px; color: #666;">
<a href="{{ unsubscribe_url }}">Darse de baja</a>
</td></tr>
</table>
</body>
</html>""",
    },
    {
        "id": "event_flyer",
        "name": "Evento con flyer (Capacitación O365)",
        "description": "Incluye imagen del flyer desde espacio público",
        "html": """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: #fff;">
<tr><td style="padding: 0;">
<a href="{{ reunion_url }}" style="display:block; text-decoration:none;"><img src="{{ base_url }}/static/public/emails/imagenes/capacitacion-mar26-o365.png" alt="Capacitación Office 365" width="600" style="max-width:100%; height:auto; display:block;"></a>
</td></tr>
<tr><td style="padding: 16px 24px;">
<table cellpadding="0" cellspacing="0"><tr><td style="background-color: #0d6efd; padding: 14px 28px; border-radius: 6px;"><a href="{{ reunion_url }}" style="color: #fff; text-decoration: none; font-weight: bold;">Unirse a la reunión</a></td></tr></table>
<p class="small text-muted mt-2 mb-0" style="margin-top: 12px; font-size: 12px; color: #666;">Hola {{ nombre }}, te compartimos la invitación. <a href="{{ unsubscribe_url }}">Darse de baja</a></p>
</td></tr>
</table>
</body>
</html>""",
    },
]

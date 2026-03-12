# Rutas públicas: tracking open/click y unsubscribe (sin login)
from flask import Blueprint, request, redirect, Response
from . import service
from . import repository

TRACKING_PIXEL = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;'
)

tracking_bp = Blueprint('marketing_tracking', __name__, url_prefix='')


@tracking_bp.route('/email/open/<tracking_id>')
def email_open(tracking_id):
    service.mark_opened(tracking_id)
    return Response(TRACKING_PIXEL, mimetype='image/gif')


@tracking_bp.route('/email/click/<tracking_id>')
def email_click(tracking_id):
    service.mark_clicked(tracking_id)
    url = request.args.get('url', '')
    if url:
        return redirect(url)
    return redirect('/')


@tracking_bp.route('/unsubscribe/<int:user_id>')
def unsubscribe(user_id):
    service.unsubscribe_user(user_id)
    return """
    <!DOCTYPE html><html><head><meta charset="utf-8"><title>Baja</title></head>
    <body><p>Has sido removido de las campañas de email marketing.</p></body></html>
    """, 200, {'Content-Type': 'text/html; charset=utf-8'}

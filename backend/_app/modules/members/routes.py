# Rutas de members (perfil): solo delegación a service.
import os
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user

from . import service

members_bp = Blueprint('members', __name__, url_prefix='')


@members_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@members_bp.route('/profile/upload-photo', methods=['POST'])
@login_required
def upload_profile_photo():
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No se proporcionó ninguna imagen'}), 400
    file = request.files['photo']
    upload_dir = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'profiles')
    try:
        success, result = service.upload_profile_photo(current_user, file, upload_dir)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    if success:
        return jsonify({
            'success': True,
            'message': 'Foto de perfil actualizada correctamente',
            'photo_url': current_user.get_profile_picture_url()
        })
    return jsonify({'success': False, 'error': result}), 400


@members_bp.route('/profile/remove-photo', methods=['POST'])
@login_required
def remove_profile_photo():
    upload_dir = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'profiles')
    try:
        success, error = service.remove_profile_photo(current_user, upload_dir)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    if success:
        return jsonify({'success': True, 'message': 'Foto de perfil eliminada correctamente'})
    return jsonify({'success': False, 'error': error or 'Error'}), 400


@members_bp.route('/api/profile/update', methods=['POST'])
@login_required
def api_profile_update():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Datos no válidos'}), 400
    try:
        success, error = service.update_profile(current_user, data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    if success:
        return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})
    return jsonify({'success': False, 'error': error}), 400

# Lógica de políticas institucionales.
from . import repository as repo

SLUG_POLITICA_CORREO = 'politica-uso-correo-institucional'

# Texto exacto para el checkbox (versión robusta).
CHECKBOX_POLITICA_CORREO = (
    'Declaro haber leído, comprendido y aceptado la Política de Uso del Correo Institucional vigente, '
    'y entiendo que el mantenimiento de mi cuenta depende de mi condición de miembro activo.'
)


def get_policy_for_display(slug, active_only=True):
    return repo.get_policy_by_slug(slug, active_only=active_only)


def user_must_accept_email_policy(user):
    """True si el usuario debe aceptar la política de correo antes de solicitar correo institucional."""
    policy = repo.get_policy_by_slug(SLUG_POLITICA_CORREO, active_only=True)
    if not policy:
        return False
    return not repo.user_has_accepted_policy(user.id, policy)


def record_email_policy_acceptance(user, request=None):
    """Registra aceptación de la política de correo. Retorna (True, None) o (False, error_msg)."""
    policy = repo.get_policy_by_slug(SLUG_POLITICA_CORREO, active_only=True)
    if not policy:
        return False, 'Política no configurada'
    if repo.user_has_accepted_policy(user.id, policy):
        return True, None
    ip = None
    if request and getattr(request, 'remote_addr', None):
        ip = request.remote_addr[:45]
    if request and request.headers.get('X-Forwarded-For'):
        ip = (request.headers.get('X-Forwarded-For').split(',')[0].strip() or ip or '')[:45]
    repo.record_acceptance(user.id, policy.id, policy.version, ip)
    return True, None

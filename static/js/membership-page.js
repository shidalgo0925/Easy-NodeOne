(function () {
    'use strict';

    function checkoutUrl() {
        var root = document.querySelector('.membership-page');
        return (root && root.getAttribute('data-checkout-url')) || '/checkout';
    }

    function showNotification(message, type, persist) {
        var notification = document.createElement('div');
        notification.className =
            'alert alert-' + (type === 'success' ? 'success' : 'danger') +
            ' alert-dismissible fade show position-fixed membership-page-toast';
        notification.innerHTML =
            message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
        document.body.appendChild(notification);
        if (!persist) {
            setTimeout(function () { notification.remove(); }, 8000);
        }
    }

    function bindPlanButtons() {
        document.querySelectorAll('.membership-page__buy-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var slug = btn.getAttribute('data-slug');
                var name = btn.getAttribute('data-name') || slug;
                membershipAddToCart(slug, name);
            });
        });
    }

    window.membershipAddToCart = function (slug, planName) {
        fetch('/cart/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_type: 'membership',
                product_id: 0,
                quantity: 1,
                membership_type: slug,
            }),
        })
            .then(function (response) {
                var ct = response.headers.get('content-type') || '';
                if (ct.indexOf('application/json') >= 0) {
                    return response.json();
                }
                throw new Error('Respuesta no válida del servidor.');
            })
            .then(function (data) {
                if (!data.success) {
                    if (data.requires_verification) {
                        showNotification('Verifica tu correo antes de continuar.', 'error');
                        setTimeout(function () { window.location.href = '/resend-verification'; }, 2000);
                        return;
                    }
                    showNotification('Error: ' + (data.error || 'desconocido'), 'error');
                    return;
                }
                var badge = document.getElementById('cart-count-badge');
                if (badge) {
                    badge.textContent = data.cart_items_count;
                    badge.style.display = 'block';
                }
                var ck = checkoutUrl();
                showNotification(
                    '«' + planName + '» en el carrito. ' +
                    '<a href="' + ck + '" class="alert-link fw-semibold">Ir al checkout</a>',
                    'success',
                    true
                );
            })
            .catch(function (err) {
                console.error(err);
                showNotification('No se pudo agregar al carrito.', 'error');
            });
    };

    document.addEventListener('DOMContentLoaded', bindPlanButtons);
})();

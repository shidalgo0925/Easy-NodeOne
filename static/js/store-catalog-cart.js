/**
 * Carrito de Tienda (catálogo Service): listado + ficha de producto.
 * Expone: showServiceNotification, addServiceFromCatalogDirect
 */
(function (global) {
  'use strict';

  function showServiceNotification(message, type) {
    var notification = document.createElement('div');
    notification.className =
      'alert alert-' +
      (type === 'success' ? 'success' : 'danger') +
      ' alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML =
      message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    document.body.appendChild(notification);
    setTimeout(function () {
      notification.remove();
    }, 3000);
  }

  function addServiceFromCatalogDirect(serviceId) {
    var sid = parseInt(serviceId, 10);
    if (!sid) {
      showServiceNotification('Producto inválido', 'error');
      return;
    }
    fetch('/cart/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        product_type: 'service',
        product_id: sid,
        quantity: 1,
      }),
    })
      .then(function (response) {
        var contentType = response.headers.get('content-type') || '';
        if (contentType.indexOf('application/json') !== -1) {
          return response.json();
        }
        return response.text().then(function () {
          throw new Error('Respuesta no válida del servidor. Verificá tu sesión.');
        });
      })
      .then(function (data) {
        if (data && data.success) {
          var cartBadge = document.getElementById('cart-count-badge');
          if (cartBadge) {
            cartBadge.textContent = data.cart_items_count;
            cartBadge.style.display = 'block';
          }
          showServiceNotification('Producto agregado al carrito', 'success');
          return;
        }
        if (data && data.requires_verification) {
          showServiceNotification('Verificá tu correo electrónico antes de continuar.', 'error');
          setTimeout(function () {
            global.location.href = '/verify-email';
          }, 2000);
          return;
        }
        showServiceNotification(
          'Error: ' + ((data && data.error) || 'No se pudo agregar al carrito'),
          'error'
        );
      })
      .catch(function (error) {
        console.error('Error:', error);
        showServiceNotification(
          'Error al agregar al carrito: ' + (error && error.message ? error.message : error),
          'error'
        );
      });
  }

  function bindBuyProductButton() {
    var btn = document.getElementById('btnBuyProduct');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var sid = btn.getAttribute('data-service-id');
      if (sid) addServiceFromCatalogDirect(sid);
    });
  }

  global.showServiceNotification = showServiceNotification;
  global.addServiceFromCatalogDirect = addServiceFromCatalogDirect;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindBuyProductButton);
  } else {
    bindBuyProductButton();
  }
})(typeof window !== 'undefined' ? window : this);

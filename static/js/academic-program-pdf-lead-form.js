(function () {
  'use strict';

  var root = document.getElementById('lc2-root');
  if (!root) return;

  var form = document.getElementById('lc2-form');
  var errBox = document.getElementById('lc2-error');
  var successBox = document.getElementById('lc2-success');
  var successMsg = document.getElementById('lc2-success-msg');
  var submitBtn = document.getElementById('lc2-submit');
  var formFields = form.querySelector('.lc2-form-fields');

  var slug = (root.getAttribute('data-program-slug') || '').trim().toLowerCase();
  var apiUrl = '/api/public/academic-programs/' + encodeURIComponent(slug) + '/lead';

  function setState(state) {
    root.classList.remove('lc2-state-idle', 'lc2-state-loading', 'lc2-state-success', 'lc2-state-error');
    root.classList.add('lc2-state-' + state);
  }

  function showError(msg) {
    errBox.textContent = msg || 'No se pudo enviar el formulario. Intentá de nuevo.';
    errBox.classList.add('is-visible');
    successBox.classList.remove('is-visible');
    setState('error');
  }

  function hideError() {
    errBox.classList.remove('is-visible');
    errBox.textContent = '';
  }

  function utmFromPage() {
    var params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get('utm_source') || '',
      utm_medium: params.get('utm_medium') || '',
      utm_campaign: params.get('utm_campaign') || '',
    };
  }

  function fillUtmHidden() {
    var u = utmFromPage();
    var el;
    el = document.getElementById('lc2-utm_source');
    if (el && u.utm_source) el.value = u.utm_source;
    el = document.getElementById('lc2-utm_medium');
    if (el && u.utm_medium) el.value = u.utm_medium;
    el = document.getElementById('lc2-utm_campaign');
    if (el && u.utm_campaign) el.value = u.utm_campaign;
  }

  fillUtmHidden();

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    hideError();
    successBox.classList.remove('is-visible');

    var fd = new FormData(form);
    var payload = {
      name: (fd.get('name') || '').toString().trim(),
      email: (fd.get('email') || '').toString().trim(),
      phone: (fd.get('phone') || '').toString().trim(),
      country: (fd.get('country') || '').toString().trim(),
      company: (fd.get('company') || '').toString().trim(),
      message: (fd.get('message') || '').toString().trim(),
      program_slug: slug,
      source: (fd.get('source') || 'wp_landing_pdf').toString().trim(),
      utm_source: (fd.get('utm_source') || '').toString().trim(),
      utm_medium: (fd.get('utm_medium') || '').toString().trim(),
      utm_campaign: (fd.get('utm_campaign') || '').toString().trim(),
      website: (fd.get('website') || '').toString().trim(),
    };

    if (!payload.name || !payload.email || !payload.phone) {
      showError('Completá nombre, correo y teléfono.');
      return;
    }

    setState('loading');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="lc2-spinner"></span> Enviando…';

    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data || !result.data.success) {
          var msg =
            (result.data && result.data.message) ||
            'No se pudo registrar tu solicitud.';
          if (result.status === 429) {
            msg = 'Demasiados intentos. Esperá un momento e intentá de nuevo.';
          }
          throw new Error(msg);
        }

        setState('success');
        successMsg.textContent =
          result.data.message ||
          'Te enviamos un correo de confirmación. Revisá tu bandeja y la carpeta de spam.';
        successBox.classList.add('is-visible');
        if (formFields) {
          formFields.style.display = 'none';
        }
        submitBtn.style.display = 'none';
      })
      .catch(function (err) {
        showError(err.message || 'Error de conexión.');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="lc2-btn__label--idle">Descargar Programa Académico</span>';
        setState('idle');
      });
  });

  setState('idle');
})();

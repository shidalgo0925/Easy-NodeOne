(function () {
  'use strict';

  var STAGE_MAP = { 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4 };
  var STAGE_LABEL = {
    1: 'Tu negocio',
    2: 'Tu recomendación',
    3: 'Tu acceso',
    4: 'Todo listo',
  };
  var INSTALL_LABELS = {
    1: 'Paso 1 de 5 · Cuenta lista',
    2: 'Paso 2 de 5 · Preparando descarga',
    3: 'Paso 3 de 5 · Descargando',
    4: 'Paso 4 de 5 · Instalar',
    5: 'Paso 5 de 5 · Si Android bloquea',
  };
  var OEM_HELP = {
    samsung:
      'Samsung: Ajustes → Seguridad → Instalar apps desconocidas → Chrome (u otro navegador) → Permitir. Volvé a Descargas e instalá EPosOne.apk.',
    xiaomi:
      'Xiaomi/Redmi: Ajustes → Privacidad y seguridad → Protección → Instalar apps vía fuentes externas → navegador → Permitir.',
    honor:
      'Honor: Ajustes → Seguridad y privacidad → Más ajustes → Instalar apps de orígenes desconocidos → navegador → Permitir.',
    huawei:
      'Huawei: Ajustes → Seguridad → Más ajustes → Instalar apps de orígenes externos → navegador → activar.',
    motorola:
      'Motorola: Ajustes → Apps → Acceso especial → Instalar apps desconocidas → navegador → Permitir.',
    realme:
      'Realme: Ajustes → Contraseñas y seguridad → Instalar apps desconocidas → navegador → Permitir.',
    otros:
      'Otros: en Ajustes buscá “instalar apps desconocidas” o “fuentes desconocidas” y habilitalo solo para el navegador que usaste.',
  };

  var bootstrap = {};
  try {
    bootstrap = JSON.parse(document.getElementById('bootstrap-data').textContent || '{}');
  } catch (e) {
    bootstrap = { business_types: [], plans: [] };
  }

  var appEl = document.getElementById('app');
  var apkUrl = (appEl && appEl.getAttribute('data-apk-url')) || '/static/apk/eposone/EPosOne.apk';

  var state = {
    screen: 1,
    businessType: 'Cafetería',
    planCode: 'business',
    recommendation: null,
    created: false,
    result: null,
    installStep: 1,
    blobUrl: null,
  };

  var historyStack = [];

  function $(id) {
    return document.getElementById(id);
  }

  function showError(el, msg) {
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      el.textContent = '';
      return;
    }
    el.hidden = false;
    el.textContent = msg;
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function updateStage() {
    var stage = STAGE_MAP[state.screen] || 1;
    document.querySelectorAll('#stage-bar span').forEach(function (el) {
      var n = parseInt(el.getAttribute('data-s'), 10);
      el.classList.toggle('on', n <= stage);
    });
    var label = $('stage-label');
    if (label) label.textContent = STAGE_LABEL[stage] || '';
    var back = $('btn-back');
    if (back) {
      var canBack =
        (state.screen > 1 && state.screen < 8 && !state.created) ||
        (state.screen === 9 && state.created);
      back.hidden = !canBack;
    }
  }

  function go(screen, push) {
    if (push !== false && screen !== state.screen) {
      historyStack.push(state.screen);
    }
    state.screen = screen;
    document.querySelectorAll('.screen').forEach(function (el) {
      el.classList.toggle('is-visible', parseInt(el.getAttribute('data-screen'), 10) === screen);
    });
    updateStage();
    if (screen === 3) renderRecommendation();
    if (screen === 4) renderPlans();
    if (screen === 6) {
      var tro = $('type_ro');
      if (tro) tro.value = state.businessType;
    }
    if (screen === 7) renderSummary();
    if (screen === 9) setInstallStep(state.installStep || 1);
  }

  function goBack() {
    if (state.screen === 9 && state.created) {
      go(8, false);
      return;
    }
    if (state.created && state.screen !== 9) return;
    var prev = historyStack.pop();
    if (prev) go(prev, false);
  }

  function renderTypes() {
    var root = $('types');
    if (!root) return;
    root.innerHTML = '';
    (bootstrap.business_types || []).forEach(function (t) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip' + (t === state.businessType ? ' is-selected' : '');
      btn.textContent = t;
      btn.addEventListener('click', function () {
        state.businessType = t;
        root.querySelectorAll('.chip').forEach(function (c) {
          c.classList.toggle('is-selected', c.textContent === t);
        });
      });
      root.appendChild(btn);
    });
  }

  function planCardHtml(p) {
    var lines = p.capacity_lines || [];
    var bullets =
      lines.length > 0
        ? '<ul class="plan-includes">' +
          lines
            .map(function (line) {
              return '<li>' + escapeHtml(line) + '</li>';
            })
            .join('') +
          '</ul>'
        : '';
    return (
      '<p class="eyebrow">' +
      escapeHtml(p.modality_benefit || '') +
      '</p>' +
      '<p style="margin:0.5rem 0 0;font-weight:800;font-size:1.15rem;">' +
      escapeHtml(p.display_name || p.plan_name || '') +
      '</p>' +
      '<p class="muted">' +
      escapeHtml(p.tagline || p.includes_summary || '') +
      '</p>' +
      bullets
    );
  }

  function renderRecommendation() {
    var card = $('reco-card');
    var lead = $('reco-lead');
    var p = state.recommendation;
    if (!p) {
      if (lead) lead.textContent = 'Cargando recomendación…';
      return;
    }
    if (lead) {
      lead.textContent =
        'Para ' + state.businessType + ' te sugerimos empezar con esta opción.';
    }
    if (card) card.innerHTML = planCardHtml(p);
  }

  function renderPlans() {
    var root = $('plan-list');
    if (!root) return;
    root.innerHTML = '';
    (bootstrap.plans || []).forEach(function (p) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'card-opt' + (p.plan_code === state.planCode ? ' is-selected' : '');
      btn.innerHTML =
        '<strong>' +
        escapeHtml(p.display_name || p.plan_name || p.plan_code) +
        '</strong><small>' +
        escapeHtml(p.includes_summary || p.tagline || '') +
        '</small>';
      btn.addEventListener('click', function () {
        state.planCode = p.plan_code;
        root.querySelectorAll('.card-opt').forEach(function (c) {
          c.classList.remove('is-selected');
        });
        btn.classList.add('is-selected');
      });
      root.appendChild(btn);
    });
  }

  function renderSummary() {
    var card = $('summary-card');
    if (!card) return;
    var plan =
      (bootstrap.plans || []).find(function (p) {
        return p.plan_code === state.planCode;
      }) || {};
    card.innerHTML =
      '<p class="eyebrow">Resumen</p>' +
      '<p style="margin:0.4rem 0;font-weight:700;">' +
      escapeHtml(($('business_name') && $('business_name').value) || 'Tu negocio') +
      '</p>' +
      '<p class="muted">' +
      escapeHtml(state.businessType) +
      ' · ' +
      escapeHtml(plan.display_name || state.planCode) +
      '</p>' +
      '<p class="muted">' +
      escapeHtml(($('email') && $('email').value) || '') +
      '</p>';
  }

  function fetchRecommend(cb) {
    fetch(
      '/api/public/eposone-start/recommend?business_type=' +
        encodeURIComponent(state.businessType),
      { credentials: 'same-origin', headers: { Accept: 'application/json' } }
    )
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        state.recommendation = data;
        state.planCode = data.plan_code || state.planCode;
        if (cb) cb();
      })
      .catch(function () {
        state.recommendation = {
          plan_code: 'business',
          display_name: 'Business',
          modality_benefit: 'Recomendado',
          capacity_lines: [],
        };
        if (cb) cb();
      });
  }

  function renderWow(result) {
    var title = $('wow-title');
    var sub = $('wow-sub');
    var list = $('wow-list');
    if (title && result.wow && result.wow.title) title.textContent = result.wow.title;
    if (sub && result.wow && result.wow.subtitle) sub.textContent = result.wow.subtitle;
    if (list) {
      list.innerHTML = '';
      (result.wow && result.wow.checks ? result.wow.checks : []).forEach(function (c) {
        var li = document.createElement('li');
        li.textContent = c;
        list.appendChild(li);
      });
    }
    var code = result.installation && result.installation.code;
    ['code-box', 'code-box-guide'].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      if (code) {
        el.textContent = code;
        el.hidden = true;
      } else {
        el.hidden = true;
      }
    });
    var pinBox = $('cashier-pin-box');
    var cashier = result.installation && result.installation.cashier;
    if (pinBox) {
      if (cashier && cashier.pin) {
        pinBox.textContent = 'PIN cajero: ' + cashier.pin;
        pinBox.hidden = false;
      } else {
        pinBox.hidden = true;
      }
    }
    if (result.play_store_url) {
      apkUrl = result.play_store_url;
      var play = $('btn-play');
      if (play) play.href = apkUrl;
    }
  }

  /* —— Password (P0.24) —— */
  function passwordChecks(pwd) {
    return {
      len: pwd.length >= 8,
      letter: /[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(pwd),
      digit: /\d/.test(pwd),
    };
  }

  function passwordScore(pwd) {
    var c = passwordChecks(pwd);
    var score = 0;
    if (c.len) score += 1;
    if (c.letter) score += 1;
    if (c.digit) score += 1;
    if (pwd.length >= 12 && c.letter && c.digit) score += 1;
    return score;
  }

  function updatePasswordUI() {
    var pwd = ($('password') && $('password').value) || '';
    var checks = passwordChecks(pwd);
    var score = passwordScore(pwd);
    document.querySelectorAll('#password-reqs [data-req]').forEach(function (li) {
      var ok = checks[li.getAttribute('data-req')];
      li.classList.toggle('is-ok', !!ok);
    });
    document.querySelectorAll('#password-meter span').forEach(function (el) {
      var n = parseInt(el.getAttribute('data-level'), 10);
      el.classList.toggle('on', n <= score && pwd.length > 0);
    });
    var label = $('password-strength-label');
    if (label) {
      if (!pwd) {
        label.hidden = true;
        label.textContent = '';
      } else {
        label.hidden = false;
        label.textContent =
          score <= 1 ? 'Débil' : score === 2 ? 'Aceptable' : score === 3 ? 'Buena' : 'Fuerte';
      }
    }
  }

  function generatePassword() {
    var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';
    var out = '';
    var buf = new Uint8Array(14);
    if (window.crypto && window.crypto.getRandomValues) {
      window.crypto.getRandomValues(buf);
    } else {
      for (var i = 0; i < buf.length; i++) buf[i] = Math.floor(Math.random() * 256);
    }
    for (var j = 0; j < buf.length; j++) out += chars[buf[j] % chars.length];
    var input = $('password');
    if (!input) return;
    input.type = 'text';
    input.value = out;
    var tog = $('btn-toggle-pass');
    if (tog) tog.textContent = 'Ocultar';
    updatePasswordUI();
  }

  function validateAccess() {
    var name = ($('full_name').value || '').trim();
    var email = ($('email').value || '').trim();
    var password = $('password').value || '';
    var c = passwordChecks(password);
    if (!name || !email || !c.len || !c.letter || !c.digit) {
      showError(
        $('access-error'),
        'Completá nombre, correo y una contraseña de al menos 8 caracteres con letra y número.'
      );
      updatePasswordUI();
      return false;
    }
    showError($('access-error'));
    return true;
  }

  function validateBiz() {
    var biz = ($('business_name').value || '').trim();
    if (!biz) {
      showError($('biz-error'), 'Revisa los campos marcados e intenta de nuevo.');
      return false;
    }
    showError($('biz-error'));
    return true;
  }

  /* —— Install assistant (P0.18 / 26) —— */
  function setInstallStep(step) {
    state.installStep = step;
    document.querySelectorAll('#install-step-bar span').forEach(function (el) {
      var n = parseInt(el.getAttribute('data-i'), 10);
      el.classList.toggle('on', n <= step);
    });
    var lab = $('install-step-label');
    if (lab) lab.textContent = INSTALL_LABELS[step] || '';
    for (var i = 1; i <= 5; i++) {
      var panel = $('install-panel-' + i);
      if (panel) panel.hidden = i !== step;
    }
    var next = $('btn-install-next');
    var dl = $('btn-download-apk');
    var open = $('btn-play');
    var blocked = $('btn-android-blocked');
    if (next) {
      next.hidden = !(step === 1 || step === 2);
      next.textContent = step === 1 ? 'Preparar descarga' : 'Continuar';
      next.disabled = false;
    }
    if (dl) {
      dl.hidden = step !== 3;
      dl.disabled = false;
      dl.textContent = 'Descargar EPosOne';
    }
    if (open) {
      open.hidden = step !== 4;
      open.textContent = 'Instalar EPosOne';
      if (state.blobUrl) open.href = state.blobUrl;
      else open.href = apkUrl;
    }
    if (blocked) blocked.hidden = step !== 4;
  }

  function startDownload() {
    setInstallStep(3);
    var bar = $('dl-bar');
    var pct = $('dl-pct');
    var status = $('dl-status');
    var btn = $('btn-download-apk');
    if (btn) btn.disabled = true;
    if (status) status.textContent = 'Descargando EPosOne…';
    if (bar) bar.style.width = '0%';
    if (pct) pct.textContent = '0 %';

    fetch(apkUrl, { credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('download_failed');
        var total = parseInt(res.headers.get('Content-Length') || '0', 10) || 0;
        if (!res.body || !res.body.getReader) {
          return res.blob().then(function (blob) {
            return { blob: blob, total: total || blob.size };
          });
        }
        var reader = res.body.getReader();
        var chunks = [];
        var received = 0;
        function pump() {
          return reader.read().then(function (result) {
            if (result.done) {
              return { blob: new Blob(chunks, { type: 'application/vnd.android.package-archive' }), total: total || received };
            }
            chunks.push(result.value);
            received += result.value.length;
            var p = total ? Math.min(99, Math.round((received / total) * 100)) : Math.min(90, Math.round(received / 1e6));
            if (bar) bar.style.width = p + '%';
            if (pct) pct.textContent = (total ? p : Math.min(90, p)) + ' %';
            return pump();
          });
        }
        return pump();
      })
      .then(function (pack) {
        if (state.blobUrl) {
          try {
            URL.revokeObjectURL(state.blobUrl);
          } catch (e) {}
        }
        state.blobUrl = URL.createObjectURL(pack.blob);
        if (bar) bar.style.width = '100%';
        if (pct) pct.textContent = '100 %';
        if (status) status.textContent = 'Descarga finalizada';
        var a = document.createElement('a');
        a.href = state.blobUrl;
        a.download = 'EPosOne.apk';
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function () {
          setInstallStep(4);
        }, 400);
      })
      .catch(function () {
        if (status) status.textContent = 'No se pudo descargar. Reintentá.';
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Reintentar descarga';
        }
        // Fallback: navegación directa
        var a = document.createElement('a');
        a.href = apkUrl;
        a.setAttribute('download', 'EPosOne.apk');
        a.rel = 'noopener';
        document.body.appendChild(a);
        a.click();
        a.remove();
      });
  }

  function submitPrepare() {
    if (state.created) {
      go(8);
      return;
    }
    var terms = $('chk-terms').checked;
    var privacy = $('chk-privacy').checked;
    var eula = $('chk-eula').checked;
    if (!(terms && privacy && eula)) {
      showError($('legal-error'), 'Debes aceptar Términos, Privacidad y EULA para continuar.');
      return;
    }
    showError($('legal-error'));
    var btn = $('btn-prepare');
    btn.disabled = true;
    btn.textContent = 'Preparando…';
    fetch('/api/public/eposone-start/complete', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        full_name: ($('full_name').value || '').trim(),
        email: ($('email').value || '').trim(),
        password: $('password').value || '',
        business_name: ($('business_name').value || '').trim(),
        business_type: state.businessType,
        country: ($('country').value || '').trim() || 'Panamá',
        plan_code: state.planCode,
        accept_terms: terms,
        accept_privacy: privacy,
        accept_eula: eula,
      }),
    })
      .then(function (r) {
        return r.json().then(function (body) {
          return { ok: r.ok, status: r.status, body: body };
        });
      })
      .then(function (res) {
        btn.disabled = false;
        btn.textContent = 'Preparar mi EPosOne';
        if (!res.ok || !res.body.ok) {
          showError(
            $('legal-error'),
            (res.body && res.body.message) ||
              'No pudimos completar este paso. Tu información está guardada. Intenta nuevamente.'
          );
          return;
        }
        state.created = true;
        state.result = res.body;
        state.installStep = 1;
        historyStack = [];
        renderWow(res.body);
        go(8, false);
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Preparar mi EPosOne';
        showError(
          $('legal-error'),
          'No pudimos completar este paso. Tu información está guardada. Intenta nuevamente.'
        );
      });
  }

  function toggleCode(show) {
    var code =
      state.result && state.result.installation && state.result.installation.code;
    ['code-box', 'code-box-guide'].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      if (code) {
        el.textContent = code;
        if (show) el.hidden = false;
      }
    });
  }

  document.querySelectorAll('[data-next]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var next = parseInt(btn.getAttribute('data-next'), 10);
      if (next === 3) {
        fetchRecommend(function () {
          go(3);
        });
        return;
      }
      go(next);
    });
  });

  $('btn-back').addEventListener('click', goBack);
  $('btn-use-reco').addEventListener('click', function () {
    if (state.recommendation) state.planCode = state.recommendation.plan_code;
    go(5);
  });
  $('btn-access').addEventListener('click', function () {
    if (validateAccess()) go(6);
  });
  $('btn-biz').addEventListener('click', function () {
    if (validateBiz()) go(7);
  });
  $('btn-prepare').addEventListener('click', submitPrepare);
  $('btn-show-code').addEventListener('click', function () {
    toggleCode(true);
  });
  $('btn-show-code-2').addEventListener('click', function () {
    toggleCode(true);
  });

  if ($('password')) {
    $('password').addEventListener('input', updatePasswordUI);
  }
  if ($('btn-toggle-pass')) {
    $('btn-toggle-pass').addEventListener('click', function () {
      var input = $('password');
      if (!input) return;
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      $('btn-toggle-pass').textContent = show ? 'Ocultar' : 'Ver';
    });
  }
  if ($('btn-gen-pass')) {
    $('btn-gen-pass').addEventListener('click', generatePassword);
  }

  if ($('btn-go-install')) {
    $('btn-go-install').addEventListener('click', function () {
      state.installStep = 1;
      go(9);
    });
  }
  if ($('btn-install-next')) {
    $('btn-install-next').addEventListener('click', function () {
      if (state.installStep === 1) {
        setInstallStep(2);
        setTimeout(function () {
          startDownload();
        }, 600);
      } else if (state.installStep === 2) {
        startDownload();
      }
    });
  }
  if ($('btn-download-apk')) {
    $('btn-download-apk').addEventListener('click', startDownload);
  }
  if ($('btn-android-blocked')) {
    $('btn-android-blocked').addEventListener('click', function () {
      setInstallStep(5);
    });
  }
  if ($('oem-select')) {
    $('oem-select').addEventListener('change', function () {
      var v = $('oem-select').value;
      var box = $('oem-help');
      if (!box) return;
      if (!v) {
        box.hidden = true;
        box.textContent = '';
        return;
      }
      box.hidden = false;
      box.textContent = OEM_HELP[v] || OEM_HELP.otros;
    });
  }

  renderTypes();
  updateStage();
  updatePasswordUI();
})();

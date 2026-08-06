(function () {
  'use strict';

  var STAGE_MAP = { 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 4, 9: 4 };
  var STAGE_LABEL = {
    1: 'Tu negocio',
    2: 'Tu recomendación',
    3: 'Tu acceso',
    4: 'Todo listo',
  };

  var bootstrap = {};
  try {
    bootstrap = JSON.parse(document.getElementById('bootstrap-data').textContent || '{}');
  } catch (e) {
    bootstrap = { business_types: [], plans: [] };
  }

  var state = {
    screen: 1,
    businessType: 'Cafetería',
    planCode: 'business',
    recommendation: null,
    created: false,
    result: null,
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
      var canBack = state.screen > 1 && state.screen < 8 && !state.created;
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
  }

  function goBack() {
    if (state.created) return;
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
      '<span class="badge">' +
      escapeHtml(p.trial_badge || '') +
      '</span>' +
      '<p class="muted">' +
      escapeHtml(p.blurb || '') +
      '</p>' +
      bullets +
      '<p class="muted" style="font-size:0.75rem;">' +
      escapeHtml(p.modality_label || '') +
      '</p>'
    );
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fetchRecommend(cb) {
    fetch(
      '/api/public/eposone-start/recommend?business_type=' +
        encodeURIComponent(state.businessType),
      { credentials: 'same-origin' }
    )
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        state.recommendation = data;
        state.planCode = data.plan_code || state.planCode;
        cb && cb();
      })
      .catch(function () {
        state.recommendation = bootstrap.recommendation || { plan_code: 'starter', display_name: 'EPosOne Starter' };
        state.planCode = state.recommendation.plan_code;
        cb && cb();
      });
  }

  function renderRecommendation() {
    var p = state.recommendation;
    if (!p) return;
    var lead = $('reco-lead');
    if (lead) lead.textContent = p.headline || '';
    var card = $('reco-card');
    if (card) card.innerHTML = planCardHtml(p);
  }

  function renderPlans() {
    var root = $('plan-list');
    if (!root) return;
    root.innerHTML = '';
    var plans = bootstrap.plans || [];
    if (!plans.length && state.recommendation) {
      plans = [state.recommendation];
    }
    plans.forEach(function (p) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'card-opt' + (p.plan_code === state.planCode ? ' is-selected' : '');
      btn.innerHTML =
        '<strong>' +
        escapeHtml(p.display_name || p.plan_name) +
        '</strong><small>' +
        escapeHtml(p.includes_summary || p.modality_benefit || '') +
        (p.trial_badge ? ' · ' + escapeHtml(p.trial_badge) : '') +
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

  function selectedPlanView() {
    if (state.recommendation && state.recommendation.plan_code === state.planCode) {
      return state.recommendation;
    }
    var plans = bootstrap.plans || [];
    for (var i = 0; i < plans.length; i++) {
      if (plans[i].plan_code === state.planCode) return plans[i];
    }
    return state.recommendation || { plan_name: state.planCode, includes_summary: '', trial_badge: '' };
  }

  function renderSummary() {
    var p = selectedPlanView();
    var biz = ($('business_name') && $('business_name').value) || 'Tu negocio';
    var card = $('summary-card');
    if (!card) return;
    card.innerHTML =
      '<p style="margin:0;"><strong>' +
      escapeHtml(biz) +
      '</strong></p>' +
      '<p class="muted">' +
      escapeHtml(p.modality_benefit || '') +
      '</p>' +
      '<p style="margin:0;font-weight:800;">' +
      escapeHtml(p.display_name || p.plan_name || '') +
      '</p>' +
      '<p class="muted" style="margin:0.35rem 0 0;">' +
      escapeHtml(p.includes_summary || '') +
      '</p>' +
      '<p style="margin:0.35rem 0 0;"><span class="badge">' +
      escapeHtml(p.trial_badge || '') +
      '</span></p>';
  }

  function renderWow(result) {
    $('wow-title').textContent = (result.wow && result.wow.title) || '¡Bienvenido a EPosOne!';
    $('wow-sub').textContent = (result.wow && result.wow.subtitle) || '';
    var list = $('wow-list');
    list.innerHTML = '';
    ((result.wow && result.wow.checks) || []).forEach(function (c) {
      var li = document.createElement('li');
      li.textContent = c;
      list.appendChild(li);
    });
    var code = result.installation && result.installation.code;
    ['code-box', 'code-box-guide'].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      if (code) {
        el.textContent = code;
        el.hidden = false;
      } else {
        el.hidden = true;
      }
    });
    if (result.play_store_url) {
      $('btn-play').href = result.play_store_url;
      $('btn-play-2').href = result.play_store_url;
    }
  }

  function validateAccess() {
    var name = ($('full_name').value || '').trim();
    var email = ($('email').value || '').trim();
    var password = $('password').value || '';
    if (!name || !email || password.length < 8) {
      showError($('access-error'), 'Revisa los campos marcados e intenta de nuevo.');
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
        el.hidden = !show ? el.hidden : false;
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

  renderTypes();
  updateStage();
})();

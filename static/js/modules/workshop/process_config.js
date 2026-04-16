/**
 * Admin: configuración SLA por etapa y overrides por servicio.
 */
(function () {
  const tbody = document.getElementById('woCfgStagesBody');
  const err = document.getElementById('woCfgErr');
  const btnSave = document.getElementById('woCfgSaveStages');
  const svcBody = document.getElementById('woCfgSvcBody');
  const svcIdEl = document.getElementById('woCfgServiceId');
  const btnLoadSvc = document.getElementById('woCfgLoadSvc');
  const btnSaveSvc = document.getElementById('woCfgSaveSvc');
  const svcErr = document.getElementById('woCfgSvcErr');

  if (!tbody || !btnSave) return;

  const STATUS = {
    draft: 'Recepción',
    inspected: 'Diagnóstico',
    quoted: 'Cotización',
    approved: 'Aprobación',
    in_progress: 'En proceso',
    qc: 'Control calidad',
    done: 'Terminado',
    delivered: 'Entrega',
    cancelled: 'Cancelado',
  };

  let stagesCache = [];

  function showErr(m) {
    if (!err) return;
    err.textContent = m;
    err.classList.remove('d-none');
  }

  function clearErr() {
    if (err) err.classList.add('d-none');
  }

  async function api(url, opts) {
    const r = await fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(opts && opts.headers) },
      ...opts,
    });
    const text = await r.text().catch(() => '');
    const t = text.trim();
    if (t.startsWith('<')) throw new Error('Sesión caducada o respuesta HTML.');
    let d;
    if (!t) d = {};
    else {
      try {
        d = JSON.parse(text);
      } catch {
        throw new Error('Respuesta no JSON');
      }
    }
    if (!r.ok) throw new Error((d && (d.error || d.detail)) || String(r.status));
    return d;
  }

  function renderStages(rows) {
    stagesCache = Array.isArray(rows) ? rows : [];
    tbody.innerHTML = stagesCache
      .map((r) => {
        return (
          '<tr data-id="' +
          r.id +
          '">' +
          '<td class="small font-monospace text-muted">' +
          escapeHtml(r.stage_key) +
          '</td>' +
          '<td><input type="text" class="form-control form-control-sm wo-f-name" value="' +
          escapeAttr(r.stage_name) +
          '"></td>' +
          '<td style="width:5rem"><input type="number" class="form-control form-control-sm wo-f-seq" value="' +
          r.sequence +
          '"></td>' +
          '<td style="width:6rem"><input type="number" min="1" class="form-control form-control-sm wo-f-min" value="' +
          r.expected_duration_minutes +
          '"></td>' +
          '<td style="width:7rem"><input type="text" class="form-control form-control-sm wo-f-color" value="' +
          escapeAttr(r.color) +
          '"></td>' +
          '<td class="text-center"><input type="checkbox" class="form-check-input wo-f-active" ' +
          (r.active ? 'checked' : '') +
          '></td>' +
          '<td class="text-center"><input type="checkbox" class="form-check-input wo-f-skip" ' +
          (r.allow_skip ? 'checked' : '') +
          '></td>' +
          '<td><input type="text" class="form-control form-control-sm wo-f-tag" value="' +
          escapeAttr(r.service_type_tag || '') +
          '" placeholder="opcional"></td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }

  function collectStagesPayload() {
    const items = [];
    tbody.querySelectorAll('tr[data-id]').forEach((tr) => {
      const id = parseInt(tr.getAttribute('data-id'), 10);
      if (!id) return;
      items.push({
        id,
        stage_name: tr.querySelector('.wo-f-name') && tr.querySelector('.wo-f-name').value,
        sequence: parseInt((tr.querySelector('.wo-f-seq') && tr.querySelector('.wo-f-seq').value) || '0', 10),
        expected_duration_minutes: parseInt((tr.querySelector('.wo-f-min') && tr.querySelector('.wo-f-min').value) || '1', 10),
        color: (tr.querySelector('.wo-f-color') && tr.querySelector('.wo-f-color').value) || '#0d6efd',
        active: !!(tr.querySelector('.wo-f-active') && tr.querySelector('.wo-f-active').checked),
        allow_skip: !!(tr.querySelector('.wo-f-skip') && tr.querySelector('.wo-f-skip').checked),
        service_type_tag: (tr.querySelector('.wo-f-tag') && tr.querySelector('.wo-f-tag').value) || '',
      });
    });
    return items;
  }

  btnSave.addEventListener('click', () => {
    clearErr();
    const items = collectStagesPayload();
    api('/api/workshop/process-stages', { method: 'PUT', body: JSON.stringify({ items }) })
      .then((rows) => {
        renderStages(rows);
        renderSvcTable();
      })
      .catch((e) => showErr(e.message || String(e)));
  });

  function renderSvcTable() {
    if (!svcBody) return;
    const sid = parseInt((svcIdEl && svcIdEl.value) || '0', 10);
    if (sid < 1) {
      svcBody.innerHTML =
        '<tr><td colspan="3" class="text-muted small">Indique un ID de servicio y cargue.</td></tr>';
      if (btnSaveSvc) btnSaveSvc.disabled = true;
      return;
    }
    api('/api/workshop/service-process-config?service_id=' + sid)
      .then((data) => {
        const ov = {};
        (data.items || []).forEach((x) => {
          ov[x.stage_key] = x.expected_duration_minutes;
        });
        svcBody.innerHTML = stagesCache
          .filter((s) => s.stage_key !== 'cancelled')
          .map((s) => {
            const def = s.expected_duration_minutes;
            const cur = ov[s.stage_key];
            const val = cur != null ? cur : '';
            return (
              '<tr data-stage="' +
              escapeAttr(s.stage_key) +
              '">' +
              '<td>' +
              escapeHtml(s.stage_name || STATUS[s.stage_key] || s.stage_key) +
              '</td>' +
              '<td>' +
              def +
              '</td>' +
              '<td><input type="number" min="1" class="form-control form-control-sm wo-svc-min" data-stage="' +
              escapeAttr(s.stage_key) +
              '" placeholder="' +
              def +
              '" value="' +
              (val === '' ? '' : val) +
              '"></td>' +
              '</tr>'
            );
          })
          .join('');
        if (btnSaveSvc) btnSaveSvc.disabled = false;
        if (svcErr) svcErr.classList.add('d-none');
      })
      .catch((e) => {
        if (svcErr) {
          svcErr.textContent = e.message || String(e);
          svcErr.classList.remove('d-none');
        }
        if (btnSaveSvc) btnSaveSvc.disabled = true;
      });
  }

  if (btnLoadSvc) {
    btnLoadSvc.addEventListener('click', () => renderSvcTable());
  }

  if (btnSaveSvc) {
    btnSaveSvc.addEventListener('click', () => {
      const sid = parseInt((svcIdEl && svcIdEl.value) || '0', 10);
      if (sid < 1) return;
      const items = [];
      svcBody.querySelectorAll('.wo-svc-min').forEach((inp) => {
        const sk = inp.getAttribute('data-stage');
        const raw = inp.value.trim();
        if (!sk) return;
        if (raw === '') {
          items.push({ stage_key: sk, expected_duration_minutes: null });
        } else {
          const n = parseInt(raw, 10);
          if (!Number.isNaN(n) && n > 0) items.push({ stage_key: sk, expected_duration_minutes: n });
        }
      });
      api('/api/workshop/service-process-config', {
        method: 'PUT',
        body: JSON.stringify({ service_id: sid, items }),
      })
        .then(() => renderSvcTable())
        .catch((e) => {
          if (svcErr) {
            svcErr.textContent = e.message || String(e);
            svcErr.classList.remove('d-none');
          }
        });
    });
  }

  api('/api/workshop/process-stages')
    .then((rows) => {
      renderStages(rows);
      renderSvcTable();
    })
    .catch((e) => showErr(e.message || String(e)));
})();

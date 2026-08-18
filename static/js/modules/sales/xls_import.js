(function () {
  const root = document.getElementById('salesXlsImportPage');
  if (!root) return;
  const apiBase = String(root.dataset.apiBase || '/api/sales/quotations').replace(/\/$/, '');
  const alertEl = document.getElementById('xlsAlert');
  const fileEl = document.getElementById('xlsFile');
  const profileEl = document.getElementById('xlsProfile');
  const btnAnalyze = document.getElementById('btnAnalyze');
  const btnCreate = document.getElementById('btnCreateQuote');
  const previewCard = document.getElementById('xlsPreviewCard');
  const metaEl = document.getElementById('xlsMeta');
  const linesEl = document.getElementById('xlsLines');
  const totalsEl = document.getElementById('xlsTotals');
  const validEl = document.getElementById('xlsValidation');
  let importId = null;

  const fmtNum = (n, decimals = 2) =>
    Number(n || 0).toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  const money = (n) => `B/. ${fmtNum(n)}`;
  function showAlert(kind, msg, extraHtml) {
    alertEl.className = `alert alert-${kind}`;
    alertEl.innerHTML = extraHtml || '';
    const span = document.createElement('div');
    span.textContent = String(msg || '');
    alertEl.prepend(span);
    alertEl.classList.remove('d-none');
  }
  function clearAlert() {
    alertEl.classList.add('d-none');
    alertEl.textContent = '';
  }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  async function api(rel, method, body, isFile) {
    const init = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (isFile) init.body = body;
    else if (body != null) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    const res = await fetch(apiBase + rel, init);
    const raw = await res.text();
    let data = {};
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch (e) {
      data = {};
    }
    if (!res.ok) {
      const fallback = res.status === 500
        ? 'El servidor no pudo analizar el archivo. Vuelva a intentar.'
        : `Error HTTP ${res.status}`;
      const err = new Error(data.user_message || data.detail || data.error || fallback);
      err.payload = data;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function renderPreview(p) {
    importId = p.import_id;
    const rows = [
      ['Cliente', p.customer || '—'],
      ['RUC', p.tax_id || '—'],
      ['DV', p.dv || '—'],
      ['Fecha', p.date || '—'],
      ['Referencia XLS', p.external_reference || p.filename || '—'],
      ['Contacto EN1', p.contact && p.contact.status === 'matched' ? `#${p.contact.contact_id} ${p.contact.display_name}` : 'Se propondrá crear'],
    ];
    metaEl.innerHTML = rows
      .map(([k, v]) => `<dt class="col-sm-3">${esc(k)}</dt><dd class="col-sm-9 mb-1">${esc(v)}</dd>`)
      .join('');
    linesEl.innerHTML = (p.lines || [])
      .map(
        (ln) => `<tr>
          <td>${esc(ln.description)}</td>
          <td class="text-end">${fmtNum(ln.quantity, Number.isInteger(Number(ln.quantity)) ? 0 : 2)}</td>
          <td class="text-end">${money(ln.unit_price)}</td>
          <td class="text-end">${ln.tax_rate == null ? '—' : esc(ln.tax_rate) + '%'}</td>
          <td class="text-end">${money(ln.total)}</td>
        </tr>`,
      )
      .join('');
    totalsEl.innerHTML = `Subtotal: <strong>${money(p.subtotal)}</strong><br>
      ITBMS: <strong>${money(p.tax_total)}</strong><br>
      TOTAL EN1: <strong>${money(p.grand_total)}</strong>
      ${p.declared_total != null ? `<br>TOTAL XLS: ${money(p.declared_total)}` : ''}
      ${p.declared_total != null ? `<br>Diferencia: ${money(p.difference)}` : ''}`;
    const v = p.validation || {};
    const items = [];
    items.push(v.recognized ? '✓ datos reconocidos' : '✕ faltan datos de encabezado');
    items.push(v.lines_ok ? '✓ líneas reconocidas' : '✕ no hay líneas');
    items.push(v.totals_ok ? '✓ totales coinciden' : '✕ el total calculado por EN1 no coincide con el total declarado en el archivo');
    const warn = (v.warnings || []).map((w) => `⚠ ${w}`);
    const err = (v.errors || []).map((e) => `✕ ${e}`);
    validEl.innerHTML = `<div class="small"><strong>Validación</strong><ul class="mb-0">${[...items, ...warn, ...err]
      .map((x) => `<li>${esc(x)}</li>`)
      .join('')}</ul></div>`;
    btnCreate.disabled = !p.can_create;
    previewCard.classList.remove('d-none');
  }

  function showDuplicate(p) {
    const url = p.quotation_url || (p.quotation_id ? `/admin/sales/quotations/${p.quotation_id}` : '');
    const extra = url
      ? `<div class="mt-1"><a href="${esc(url)}">Abrir cotización ${esc(p.quotation_number || '')}</a></div>`
      : '';
    showAlert('warning', p.user_message || 'Este archivo ya fue procesado.', extra);
    previewCard.classList.add('d-none');
    btnCreate.disabled = true;
  }

  async function loadProfiles() {
    try {
      const data = await api('/xls-import/profiles', 'GET');
      const current = profileEl.value;
      profileEl.innerHTML = '';
      (data.profiles || []).forEach((pr) => {
        const opt = document.createElement('option');
        opt.value = pr.code;
        opt.textContent = pr.version ? `${pr.label} (v${pr.version})` : pr.label;
        profileEl.appendChild(opt);
      });
      if ([...profileEl.options].some((o) => o.value === current)) profileEl.value = current;
    } catch (e) {
      /* el combo queda en Automático */
    }
  }

  btnAnalyze.addEventListener('click', async () => {
    clearAlert();
    const file = fileEl.files && fileEl.files[0];
    if (!file) {
      showAlert('danger', 'Seleccione un archivo XLS/XLSX.');
      return;
    }
    const fd = new FormData();
    fd.append('file', file);
    fd.append('profile', profileEl.value || 'auto');
    btnAnalyze.disabled = true;
    try {
      const data = await api('/xls-import/analyze', 'POST', fd, true);
      renderPreview(data);
    } catch (e) {
      if (e.payload && e.payload.already_imported) showDuplicate(e.payload);
      else showAlert('danger', e.message);
    } finally {
      btnAnalyze.disabled = false;
    }
  });

  btnCreate.addEventListener('click', async () => {
    if (!importId) return;
    clearAlert();
    btnCreate.disabled = true;
    try {
      const data = await api(`/xls-import/${importId}/commit`, 'POST', { create_customer: true });
      if (data.quotation_url) {
        window.location.href = data.quotation_url;
        return;
      }
      showAlert('success', 'Cotización creada.');
    } catch (e) {
      if (e.payload && e.payload.already_imported) showDuplicate(e.payload);
      else showAlert('danger', e.message);
      btnCreate.disabled = false;
    }
  });

  loadProfiles();
})();

/**
 * Ficha orden de taller: recepción, líneas (M2O estilo Odoo), body map, cotización.
 */
(function () {
  const root = document.getElementById('workshopOrderPage');
  if (!root) return;

  const orderId = Number(root.dataset.orderId || 0) || 0;
  const errEl = document.getElementById('woErr');
  const fmt = (n) => `B/. ${Number(n || 0).toFixed(2)}`;

  const CUST_DEBOUNCE_MS = 300;
  const SVC_DEBOUNCE_MS = 300;
  const LS_WORKSHOP_INSP_HIDDEN = 'workshop_order_inspection_hidden';

  let order = null;
  let zones = [];
  let taxes = [];
  let inspection = { inspection_id: null, points: [] };
  let zoneLabels = {};

  const customerSearch = document.getElementById('custSearch');
  const customerMenu = document.getElementById('custMenu');
  const customerId = document.getElementById('custId');
  const lineItems = document.getElementById('wolLines');

  const CHECKLIST_PRESETS = [
    'Rayones / pintura',
    'Swirls / hologramas',
    'Golpes o abolladuras',
    'Interior',
    'Cristales',
    'Neumáticos',
    'Ópticas / faros',
  ];
  const COND_OPTS = [
    ['ok', 'OK'],
    ['leve', 'Leve'],
    ['medio', 'Medio'],
    ['severo', 'Severo'],
  ];
  const DAMAGE_LABELS = {
    scratch: 'Rayón',
    swirl: 'Swirl',
    dent: 'Golpe / abolladura',
    stain: 'Mancha',
    chip: 'Descascarado',
  };
  const SEV_LABELS = { low: 'baja', medium: 'media', high: 'alta' };

  function escAttr(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function applyInspectionMapLayout(hidden) {
    const main = document.getElementById('woMainColumn');
    const insp = document.getElementById('woInspectionColumn');
    if (!main || !insp) return;
    if (hidden) {
      insp.classList.add('d-none');
      main.classList.remove('col-lg-7');
      main.classList.add('col-lg-12');
    } else {
      insp.classList.remove('d-none');
      main.classList.remove('col-lg-12');
      main.classList.add('col-lg-7');
    }
  }

  function syncInspectionMapToggleButton(mapVisible) {
    const btn = document.getElementById('btnWoMapToggle');
    if (!btn) return;
    const lab = btn.querySelector('.wo-map-toggle-label');
    if (mapVisible) {
      if (lab) lab.textContent = 'Ocultar mapa';
      btn.setAttribute('aria-expanded', 'true');
      btn.title = 'Ocultar el mapa de la derecha y ampliar líneas / cotización';
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-outline-secondary');
    } else {
      if (lab) lab.textContent = 'Mostrar mapa';
      btn.setAttribute('aria-expanded', 'false');
      btn.title = 'Volver a mostrar el mapa de inspección';
      btn.classList.remove('btn-outline-secondary');
      btn.classList.add('btn-primary');
    }
  }

  function initInspectionMapToggle() {
    const btn = document.getElementById('btnWoMapToggle');
    if (!btn) return;
    let mapVisible = true;
    try {
      if (localStorage.getItem(LS_WORKSHOP_INSP_HIDDEN) === '1') mapVisible = false;
    } catch (_) {
      /* ignore */
    }
    applyInspectionMapLayout(!mapVisible);
    syncInspectionMapToggleButton(mapVisible);

    btn.addEventListener('click', () => {
      mapVisible = !mapVisible;
      try {
        if (mapVisible) localStorage.removeItem(LS_WORKSHOP_INSP_HIDDEN);
        else localStorage.setItem(LS_WORKSHOP_INSP_HIDDEN, '1');
      } catch (_) {
        /* ignore */
      }
      applyInspectionMapLayout(!mapVisible);
      syncInspectionMapToggleButton(mapVisible);
    });
  }

  function renderChecklist(items) {
    const tb = document.getElementById('woChecklistBody');
    if (!tb) return;
    const byItem = {};
    (items || []).forEach((r) => {
      if (r && r.item) byItem[r.item] = r;
    });
    tb.innerHTML = CHECKLIST_PRESETS.map((label) => {
      const ex = byItem[label] || {};
      const cond = ex.condition || 'ok';
      const notes = String(ex.notes || '').replace(/"/g, '&quot;');
      const opts = COND_OPTS.map(([v, t]) => `<option value="${v}"${cond === v ? ' selected' : ''}>${t}</option>`).join('');
      const safe = label.replace(/"/g, '&quot;');
      return `<tr data-item="${safe}"><td class="small">${label}</td><td><select class="form-select form-select-sm woch-cond">${opts}</select></td><td><input type="text" class="form-control form-control-sm woch-notes" value="${notes}" placeholder="…"/></td></tr>`;
    }).join('');
  }

  function collectChecklist() {
    const tb = document.getElementById('woChecklistBody');
    if (!tb) return [];
    return [...tb.querySelectorAll('tr')].map((tr) => ({
      item: tr.dataset.item || '',
      condition: tr.querySelector('.woch-cond') ? tr.querySelector('.woch-cond').value : 'ok',
      notes: (tr.querySelector('.woch-notes') && tr.querySelector('.woch-notes').value.trim()) || null,
    }));
  }

  async function loadChecklist() {
    if (!order || !order.id) {
      renderChecklist([]);
      return;
    }
    try {
      const data = await api(`/api/workshop/orders/${order.id}/checklist`);
      renderChecklist(data.items || []);
    } catch (_) {
      renderChecklist([]);
    }
  }

  async function persistChecklist() {
    if (!order || !order.id) return;
    await api(`/api/workshop/orders/${order.id}/checklist`, 'PUT', { items: collectChecklist() });
  }

  function showErr(m) {
    if (!errEl) return;
    errEl.textContent = m || 'Error';
    errEl.classList.remove('d-none');
  }
  function clearErr() {
    if (errEl) errEl.classList.add('d-none');
  }

  async function api(url, method, body) {
    const opt = { method: method || 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (body != null) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const r = await fetch(url, opt);
    const text = await r.text().catch(() => '');
    const t = text.trim();
    if (t.startsWith('<')) {
      throw new Error('Sesión caducada o respuesta HTML. Recargue la página e inicie sesión de nuevo.');
    }
    let d;
    if (!t) {
      d = {};
    } else {
      try {
        d = JSON.parse(text);
      } catch {
        throw new Error(`HTTP ${r.status}: la API no devolvió JSON (${t.slice(0, 60)}…)`);
      }
    }
    if (!r.ok) throw new Error((d && (d.detail || d.error)) || `HTTP ${r.status}`);
    return d;
  }

  async function loadTaxes() {
    try {
      taxes = await api('/api/taxes?include_inactive=1');
    } catch {
      try {
        taxes = await api('/taxes?include_inactive=1');
      } catch {
        taxes = [];
      }
    }
    if (!Array.isArray(taxes)) taxes = [];
  }

  async function loadZones() {
    try {
      zones = await api('/api/workshop/zones');
    } catch {
      zones = [];
    }
    if (!Array.isArray(zones)) zones = [];
    zoneLabels = {};
    zones.forEach((z) => {
      if (z && z.code) zoneLabels[z.code] = z.name;
    });
    fillZonePick();
  }

  function fillZonePick() {
    const sel = document.getElementById('woModalZonePick');
    if (!sel) return;
    sel.innerHTML = zones
      .map((z) => `<option value="${escAttr(z.code)}">${escHtml(z.name || z.code || '')}</option>`)
      .join('');
  }

  function syncModalZoneTitle(fallbackZoneCode) {
    const pick = document.getElementById('woModalZonePick');
    const lab = document.getElementById('woModalZoneLabel');
    if (!lab) return;
    let code = pick && pick.value ? String(pick.value) : '';
    if (!code && fallbackZoneCode) code = String(fallbackZoneCode);
    if (!code && pick && pick.options.length) code = String(pick.options[0].value);
    lab.textContent = zoneLabels[code] || code || '—';
  }

  function clearModalExistingPhotos() {
    const wrap = document.getElementById('woModalExistingPhotosWrap');
    const box = document.getElementById('woModalExistingPhotos');
    if (box) box.innerHTML = '';
    if (wrap) wrap.classList.add('d-none');
  }

  function fillModalExistingPhotos(p) {
    const wrap = document.getElementById('woModalExistingPhotosWrap');
    const box = document.getElementById('woModalExistingPhotos');
    if (!box || !wrap) return;
    const photos = p && Array.isArray(p.photos) ? p.photos : [];
    if (!photos.length) {
      clearModalExistingPhotos();
      return;
    }
    box.innerHTML = photos
      .map((ph) => {
        const u = String(ph.url || '').replace(/"/g, '&quot;').replace(/</g, '');
        if (!u) return '';
        return (
          `<a href="${u}" target="_blank" rel="noopener" class="wo-point-photo-thumb border rounded overflow-hidden bg-light d-inline-block" ` +
          `style="width:4.5rem;height:4.5rem" title="Ver foto">` +
          `<img src="${u}" alt="" width="72" height="72" class="w-100 h-100" style="object-fit:cover" loading="lazy"/>` +
          `</a>`
        );
      })
      .join('');
    wrap.classList.remove('d-none');
  }

  function taxOptionsHtml() {
    return (
      '<option value="">Sin impuesto</option>' +
      taxes
        .map((t) => `<option value="${t.id}">${(t.name || '').replace(/</g, '')} (${Number(t.rate != null ? t.rate : t.percentage || 0)}%)</option>`)
        .join('')
    );
  }

  /* —— Cliente (Many2one + crear) —— */
  function closeCustomerMenu() {
    if (!customerMenu) return;
    customerMenu.classList.remove('show');
    customerMenu.innerHTML = '';
    if (customerSearch) customerSearch.setAttribute('aria-expanded', 'false');
  }

  function setCustomerHighlight(menu, index) {
    const opts = [...menu.querySelectorAll('.wo-cust-kbd-opt')];
    opts.forEach((el, i) => el.classList.toggle('odoo-m2o-item-active', i === index));
    if (opts[index]) opts[index].scrollIntoView({ block: 'nearest' });
    return opts;
  }

  function buildCustomerDropdownHtml(users, qRaw) {
    const q = (qRaw || '').trim();
    let head = '';
    if (q) {
      const qDisp = escHtml(q);
      const qAttr = escAttr(q);
      head =
        `<button type="button" class="odoo-m2o-item wo-cust-kbd-opt wo-cust-quick-create wo-cust-odoo-create border-0 w-100 text-start" data-q="${qAttr}">Crear "${qDisp}"</button>` +
        `<button type="button" class="odoo-m2o-item wo-cust-kbd-opt wo-cust-open-edit border-0 w-100 text-start">Crear y editar…</button>`;
    }
    const body = (users || [])
      .map((u) => {
        const title = escHtml(u.name || u.email || '');
        const em =
          u.email && String(u.email) !== String(u.name || '')
            ? `<span class="odoo-m2o-item-meta">${escHtml(u.email)}</span>`
            : '';
        return `<button type="button" class="odoo-m2o-item wo-cust-kbd-opt wo-cust-m2o-opt" data-id="${u.id}" data-name="${escAttr(u.name || '')}" data-email="${escAttr(u.email || '')}"><span class="odoo-m2o-item-title">${title}</span>${em}</button>`;
      })
      .join('');
    let mid = '';
    if (users && users.length) {
      mid = body;
    } else {
      mid = `<div class="px-3 py-2 small text-muted">${q ? 'Sin coincidencias en esta organización' : 'No hay contactos en el listado reciente'}</div>`;
    }
    const footer =
      '<div class="odoo-m2o-footer border-top">' +
      '<a href="/admin/users" target="_blank" rel="noopener" class="odoo-m2o-more">Buscar más…</a>' +
      '</div>';
    const hint = '<div class="odoo-m2o-hint">Empiece a escribir…</div>';
    return `${head}${mid}${footer}${hint}`;
  }

  async function fetchWorkshopCustomers(q, limit) {
    return api(`/api/workshop/customers/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  }

  async function renderCustomerDropdown(q, limit) {
    if (!customerMenu || !customerSearch) return;
    root._custFetch = (root._custFetch || 0) + 1;
    const fid = root._custFetch;
    customerMenu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
    customerMenu.classList.add('show');
    customerSearch.setAttribute('aria-expanded', 'true');
    try {
      const users = await fetchWorkshopCustomers(q, limit);
      if (fid !== root._custFetch) return;
      const list = Array.isArray(users) ? users : [];
      customerMenu.innerHTML = buildCustomerDropdownHtml(list, q);
      const kbd = [...customerMenu.querySelectorAll('.wo-cust-kbd-opt')];
      root._custM2oIndex = kbd.length ? 0 : -1;
      if (kbd.length) setCustomerHighlight(customerMenu, root._custM2oIndex);
    } catch (e) {
      if (fid !== root._custFetch) return;
      customerMenu.classList.add('show');
      customerMenu.innerHTML = `<div class="px-3 py-2 small text-danger">${escAttr(e.message)}</div><div class="odoo-m2o-hint small px-3 pb-2">Si persiste, recargue (Ctrl+F5) o revise la consola del navegador.</div>`;
    }
  }

  function applyCustomerPick(u) {
    if (!customerId || !customerSearch) return;
    customerId.value = String(u.id);
    const disp = u.email && u.name ? `${u.name} (${u.email})` : u.name || u.email || '';
    customerSearch.value = disp;
    customerSearch.dataset.lockedLabel = disp;
    closeCustomerMenu();
  }

  function openNewCustomerModal(prefillOverride) {
    closeCustomerMenu();
    const raw =
      prefillOverride != null && String(prefillOverride).trim() !== ''
        ? String(prefillOverride).trim()
        : (customerSearch && customerSearch.value ? customerSearch.value.trim() : '');
    const em = document.getElementById('woNewCustEmail');
    const fn = document.getElementById('woNewCustFirst');
    const ln = document.getElementById('woNewCustLast');
    const ph = document.getElementById('woNewCustPhone');
    const er = document.getElementById('woNewCustErr');
    if (em) em.value = raw.includes('@') ? raw : '';
    if (fn) {
      if (raw.includes('@')) {
        const local = raw.split('@')[0].replace(/[._+-]/g, ' ').trim();
        fn.value = local.slice(0, 50);
      } else {
        fn.value = raw.slice(0, 50);
      }
    }
    if (ln) ln.value = '';
    if (ph) ph.value = '';
    if (er) {
      er.textContent = '';
      er.classList.add('d-none');
    }
    const modalEl = document.getElementById('woNewCustomerModal');
    if (window.bootstrap && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  async function quickCreateFromTypedLabel(raw) {
    const t = String(raw || '').trim();
    if (!t) return;
    clearErr();
    try {
      let res;
      if (t.includes('@')) {
        res = await api('/api/workshop/customers', 'POST', { email: t.toLowerCase() });
      } else {
        res = await api('/api/workshop/customers', 'POST', { quick_create_name: t });
      }
      applyCustomerPick({ id: res.id, name: res.name, email: res.email });
      closeCustomerMenu();
    } catch (e) {
      showErr(e.message);
    }
  }

  async function submitNewCustomer() {
    const em = document.getElementById('woNewCustEmail');
    const fn = document.getElementById('woNewCustFirst');
    const ln = document.getElementById('woNewCustLast');
    const ph = document.getElementById('woNewCustPhone');
    const er = document.getElementById('woNewCustErr');
    const payload = {
      email: (em && em.value.trim()) || '',
      first_name: (fn && fn.value.trim()) || '',
      last_name: (ln && ln.value.trim()) || '',
      phone: (ph && ph.value.trim()) || '',
    };
    try {
      const res = await api('/api/workshop/customers', 'POST', payload);
      applyCustomerPick({ id: res.id, name: res.name, email: res.email });
      const modalEl = document.getElementById('woNewCustomerModal');
      if (window.bootstrap && modalEl) window.bootstrap.Modal.getInstance(modalEl)?.hide();
      clearErr();
    } catch (e) {
      if (er) {
        er.textContent = e.message || 'No se pudo crear el cliente';
        er.classList.remove('d-none');
      }
    }
  }

  /* —— Líneas: producto Many2one —— */
  function closeAllWolProductMenus(exceptTr = null) {
    if (!lineItems) return;
    lineItems.querySelectorAll('.li-product-menu.show').forEach((menu) => {
      const tr = menu.closest('tr');
      if (exceptTr && tr === exceptTr) return;
      menu.classList.remove('show');
      menu.innerHTML = '';
      const inp = tr && tr.querySelector('.li-product-search');
      if (inp) inp.setAttribute('aria-expanded', 'false');
    });
  }

  function setM2oHighlight(menu, index) {
    const opts = [...menu.querySelectorAll('.li-product-option')];
    opts.forEach((el, i) => el.classList.toggle('odoo-m2o-item-active', i === index));
    if (opts[index]) opts[index].scrollIntoView({ block: 'nearest' });
    return opts;
  }

  function buildServiceDropdownHtml(products) {
    const fmtPu = (n) => `B/. ${Number(n || 0).toFixed(2)}`;
    let body = (products || [])
      .map((p) => {
        const code = p.code != null && String(p.code) !== '' ? String(p.code) : String(p.id);
        const dt = p.default_tax_id != null && p.default_tax_id !== '' ? escAttr(String(p.default_tax_id)) : '';
        return `<button type="button" class="odoo-m2o-item li-product-option" data-id="${p.id}" data-name="${escAttr(p.name)}" data-desc="${escAttr(p.description || '')}" data-price="${Number(p.price_unit || 0)}" data-tax="${dt}"><span class="odoo-m2o-item-title">${escHtml(p.name)}</span><span class="odoo-m2o-item-meta"><span class="text-muted">Ref. ${escHtml(code)}</span> · ${escHtml(fmtPu(p.price_unit))}</span></button>`;
      })
      .join('');
    if (!products || !products.length) body = '<div class="px-3 py-2 small text-muted">Sin resultados</div>';
    return `${body}<div class="odoo-m2o-footer"><a href="/admin/services" target="_blank" rel="noopener" class="odoo-m2o-more wo-svc-catalog">Catálogo de servicios…</a></div><div class="odoo-m2o-hint">Nombre, descripción o ID</div>`;
  }

  async function fetchWorkshopProducts(q, limit) {
    return api(`/api/workshop/products/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  }

  async function renderServiceDropdown(tr, q, limit) {
    const menu = tr.querySelector('.li-product-menu');
    const inp = tr.querySelector('.li-product-search');
    if (!menu || !inp) return;
    tr._svcFetch = (tr._svcFetch || 0) + 1;
    const fid = tr._svcFetch;
    menu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
    menu.classList.add('show');
    inp.setAttribute('aria-expanded', 'true');
    try {
      const prods = await fetchWorkshopProducts(q, limit);
      if (fid !== tr._svcFetch) return;
      const list = Array.isArray(prods) ? prods : [];
      menu.innerHTML = buildServiceDropdownHtml(list);
      tr._m2oIndex = list.length ? 0 : -1;
      if (list.length) setM2oHighlight(menu, tr._m2oIndex);
    } catch (e) {
      if (fid !== tr._svcFetch) return;
      menu.innerHTML = `<div class="px-3 py-2 small text-danger">${escAttr(e.message)}</div>`;
    }
  }

  function applyServiceToRow(tr, p) {
    const hid = tr.querySelector('.li-product');
    const inp = tr.querySelector('.li-product-search');
    const desc = tr.querySelector('.wol-desc');
    const price = tr.querySelector('.wol-price');
    const taxSel = tr.querySelector('.wol-tax');
    if (hid) hid.value = p.id;
    if (inp) inp.value = p.name || '';
    if (desc) desc.value = (p.description || p.name || '').trim() || p.name || '';
    if (price) price.value = Number(p.price_unit || 0).toFixed(2);
    if (taxSel) {
      let tid = p.default_tax_id != null && p.default_tax_id !== '' ? Number(p.default_tax_id) : null;
      if (tid == null || Number.isNaN(tid)) tid = taxes.length === 1 ? Number(taxes[0].id) : null;
      if (tid != null && !Number.isNaN(tid)) taxSel.value = String(tid);
    }
    closeAllWolProductMenus();
    recalcLineTotals();
  }

  function lineRow(ln, idx) {
    const pnm = ln && ln.product_name ? String(ln.product_name) : '';
    return `<tr data-idx="${idx}">
      <td class="align-top p-2">
        <div class="odoo-m2o">
          <div class="d-flex align-items-stretch odoo-m2o-input-wrap">
            <input class="li-product-search flex-grow-1 border-0 shadow-none rounded-0 py-1" type="text" placeholder="Buscar servicio…" value="${escAttr(pnm)}" autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list">
            <button type="button" class="btn btn-sm btn-link odoo-m2o-toggle li-product-toggle px-2" tabindex="-1" title="Listado">🔍</button>
          </div>
          <input class="li-product" type="hidden" value="${ln.product_id || ''}">
          <div class="odoo-m2o-dropdown li-product-menu" role="listbox"></div>
        </div>
      </td>
      <td class="p-2"><input class="form-control form-control-sm wol-desc" value="${String(ln.description || '').replace(/"/g, '&quot;')}"/></td>
      <td class="p-2"><input class="form-control form-control-sm wol-qty" type="number" step="0.01" value="${Number(ln.quantity || 1)}"/></td>
      <td class="p-2"><input class="form-control form-control-sm wol-price" type="number" step="0.01" value="${Number(ln.price_unit || 0).toFixed(2)}"/></td>
      <td class="p-2"><select class="form-select form-select-sm wol-tax">${taxOptionsHtml()}</select></td>
      <td class="text-end small wol-line-total p-2 align-middle">${fmt(ln.total)}</td>
      <td class="p-1"><button type="button" class="btn btn-sm btn-outline-danger wol-del">×</button></td>
    </tr>`;
  }

  function collectLines() {
    const rows = [...document.querySelectorAll('#wolLines tr')];
    return rows.map((tr) => ({
      product_id: tr.querySelector('.li-product') && tr.querySelector('.li-product').value
        ? Number(tr.querySelector('.li-product').value)
        : null,
      description: tr.querySelector('.wol-desc').value.trim() || 'Servicio',
      quantity: Number(tr.querySelector('.wol-qty').value || 0),
      price_unit: Number(tr.querySelector('.wol-price').value || 0),
      tax_id: tr.querySelector('.wol-tax').value ? Number(tr.querySelector('.wol-tax').value) : null,
    }));
  }

  function recalcLineTotals() {
    document.querySelectorAll('#wolLines tr').forEach((tr) => {
      const qty = Number(tr.querySelector('.wol-qty').value || 0);
      const pu = Number(tr.querySelector('.wol-price').value || 0);
      const el = tr.querySelector('.wol-line-total');
      if (el) el.textContent = fmt(qty * pu);
    });
  }

  function wireLineRow(tr, arr) {
    const tid = tr.querySelector('.wol-tax');
    const ln = arr[Number(tr.dataset.idx) || 0];
    if (tid && ln && ln.tax_id) tid.value = String(ln.tax_id);
    tr.querySelector('.wol-del')?.addEventListener('click', () => {
      tr.remove();
      if (!document.querySelector('#wolLines tr')) renderLines([{ description: '', quantity: 1, price_unit: 0 }]);
      recalcLineTotals();
    });
    tr.querySelectorAll('.wol-qty,.wol-price,.wol-tax').forEach((el) => el.addEventListener('input', recalcLineTotals));
  }

  function renderLines(lines) {
    const tb = document.getElementById('wolLines');
    if (!tb) return;
    const arr = Array.isArray(lines) && lines.length ? lines : [{ description: '', quantity: 1, price_unit: 0, tax_id: null }];
    tb.innerHTML = arr.map((ln, i) => lineRow(ln, i)).join('');
    tb.querySelectorAll('tr').forEach((tr) => wireLineRow(tr, arr));
    recalcLineTotals();
  }

  function bindCustomerM2o() {
    if (!customerSearch || !customerMenu) return;
    customerSearch.addEventListener('focusin', () => {
      renderCustomerDropdown((customerSearch.value || '').trim(), 15);
    });
    customerSearch.addEventListener('click', () => {
      renderCustomerDropdown((customerSearch.value || '').trim(), 15);
    });
    customerSearch.addEventListener('input', () => {
      if (customerSearch.dataset.lockedLabel && customerSearch.value !== customerSearch.dataset.lockedLabel) {
        if (customerId) customerId.value = '';
        delete customerSearch.dataset.lockedLabel;
      }
      const q = (customerSearch.value || '').trim();
      clearTimeout(root._custDeb);
      root._custDeb = setTimeout(() => renderCustomerDropdown(q, 15), CUST_DEBOUNCE_MS);
    });
    customerSearch.addEventListener('keydown', (e) => {
      const menu = customerMenu;
      if (!menu.classList.contains('show')) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          renderCustomerDropdown((customerSearch.value || '').trim(), 15);
        }
        return;
      }
      const opts = [...menu.querySelectorAll('.wo-cust-kbd-opt')];
      if (!opts.length) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeCustomerMenu();
        }
        return;
      }
      let idx = typeof root._custM2oIndex === 'number' ? root._custM2oIndex : 0;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        idx = Math.min(idx + 1, opts.length - 1);
        root._custM2oIndex = idx;
        setCustomerHighlight(menu, idx);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        idx = Math.max(idx - 1, 0);
        root._custM2oIndex = idx;
        setCustomerHighlight(menu, idx);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        opts[idx].click();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeCustomerMenu();
      }
    });
    document.getElementById('woCustomerM2o')?.addEventListener('click', (e) => {
      const qc = e.target.closest && e.target.closest('.wo-cust-quick-create');
      if (qc) {
        e.preventDefault();
        quickCreateFromTypedLabel(qc.dataset.q || '');
        return;
      }
      const ed = e.target.closest && e.target.closest('.wo-cust-open-edit');
      if (ed) {
        e.preventDefault();
        openNewCustomerModal();
        return;
      }
      const btn = e.target.closest && e.target.closest('.wo-cust-m2o-opt');
      if (btn && btn.dataset.id) {
        applyCustomerPick({
          id: btn.dataset.id,
          name: btn.dataset.name,
          email: btn.dataset.email,
        });
      }
    });
    document.querySelector('#woCustomerM2o .wo-cust-toggle')?.addEventListener('click', (e) => {
      e.preventDefault();
      customerSearch.focus();
      renderCustomerDropdown((customerSearch.value || '').trim(), 15);
    });
  }

  function bindLineItemsM2o() {
    if (!lineItems) return;
    lineItems.addEventListener('focusin', (e) => {
      if (!e.target.classList.contains('li-product-search')) return;
      const tr = e.target.closest('tr');
      const q = (e.target.value || '').trim();
      closeAllWolProductMenus(tr);
      renderServiceDropdown(tr, q, 20);
    });
    lineItems.addEventListener('input', (e) => {
      const tr = e.target.closest('tr');
      if (!tr) return;
      if (e.target.classList.contains('li-product-search')) {
        const q = (e.target.value || '').trim();
        clearTimeout(tr._svcDeb);
        tr._svcDeb = setTimeout(() => renderServiceDropdown(tr, q, 20), SVC_DEBOUNCE_MS);
        return;
      }
      recalcLineTotals();
    });
    lineItems.addEventListener('keydown', (e) => {
      if (!e.target.classList.contains('li-product-search')) return;
      const tr = e.target.closest('tr');
      const menu = tr.querySelector('.li-product-menu');
      if (!menu.classList.contains('show')) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          renderServiceDropdown(tr, (e.target.value || '').trim(), 20);
        }
        return;
      }
      const opts = [...menu.querySelectorAll('.li-product-option')];
      if (!opts.length) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeAllWolProductMenus();
        }
        return;
      }
      let idx = typeof tr._m2oIndex === 'number' ? tr._m2oIndex : 0;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        idx = Math.min(idx + 1, opts.length - 1);
        tr._m2oIndex = idx;
        setM2oHighlight(menu, idx);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        idx = Math.max(idx - 1, 0);
        tr._m2oIndex = idx;
        setM2oHighlight(menu, idx);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        opts[idx].click();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeAllWolProductMenus();
      }
    });
    lineItems.addEventListener('click', (e) => {
      const delBtn = e.target.closest && e.target.closest('.wol-del');
      if (delBtn) {
        closeAllWolProductMenus();
        return;
      }
      if (e.target.classList.contains('li-product-toggle')) {
        e.preventDefault();
        const tr = e.target.closest('tr');
        const inp = tr.querySelector('.li-product-search');
        closeAllWolProductMenus(tr);
        inp.focus();
        renderServiceDropdown(tr, (inp.value || '').trim(), 20);
        return;
      }
      const optBtn = e.target.closest && e.target.closest('.li-product-option');
      if (optBtn) {
        const tr = optBtn.closest('tr');
        applyServiceToRow(tr, {
          id: optBtn.dataset.id,
          name: optBtn.dataset.name,
          description: optBtn.dataset.desc,
          price_unit: optBtn.dataset.price,
          default_tax_id: optBtn.dataset.tax || null,
        });
      }
    });
  }

  document.addEventListener('mousedown', (e) => {
    if (!e.target.closest('#woCustomerM2o')) closeCustomerMenu();
    if (e.target.closest('#wolLines .odoo-m2o')) return;
    closeAllWolProductMenus();
  });

  function paintZones() {
    document.querySelectorAll('.workshop-body-map-svg .car-zone').forEach((el) => {
      el.classList.remove('sev-low', 'sev-medium', 'sev-high');
    });
    const byZone = {};
    (inspection.points || []).forEach((p) => {
      const z = p.zone_code;
      const rank = { low: 1, medium: 2, high: 3 };
      const cur = byZone[z] || 'low';
      if ((rank[p.severity] || 1) > (rank[cur] || 1)) byZone[z] = p.severity;
    });
    Object.keys(byZone).forEach((z) => {
      const el = document.getElementById(z);
      if (!el) return;
      const s = byZone[z];
      el.classList.add(s === 'high' ? 'sev-high' : s === 'medium' ? 'sev-medium' : 'sev-low');
    });
  }

  async function loadInspection() {
    if (!order || !order.id) return;
    inspection = await api(`/api/workshop/orders/${order.id}/inspection`);
    paintZones();
    renderPointsList();
  }

  function renderPointsList() {
    const ul = document.getElementById('woPointsList');
    if (!ul) return;
    const pts = inspection.points || [];
    if (!pts.length) {
      ul.innerHTML = '<li class="text-muted small">Sin daños registrados en el mapa</li>';
      return;
    }
    ul.innerHTML = pts
      .map((p) => {
        const zname = escHtml(zoneLabels[p.zone_code] || p.zone_code || '');
        const dlab = escHtml(DAMAGE_LABELS[p.damage_type] || p.damage_type || '');
        const slab = escHtml(SEV_LABELS[p.severity] || p.severity || '');
        const notes = (p.notes || '').trim();
        const notesBlock = notes
          ? `<div class="wo-point-notes small text-body-secondary mt-1">“${escHtml(notes)}”</div>`
          : '';
        const photos = Array.isArray(p.photos) ? p.photos : [];
        const photosBlock =
          photos.length > 0
            ? `<div class="wo-point-photos d-flex flex-wrap gap-2 mt-2" role="group" aria-label="Fotos del daño">` +
              photos
                .map((ph) => {
                  const u = String(ph.url || '').replace(/"/g, '&quot;').replace(/</g, '');
                  if (!u) return '';
                  return (
                    `<a href="${u}" target="_blank" rel="noopener" class="wo-point-photo-thumb border rounded overflow-hidden bg-light" ` +
                    `style="width:4.5rem;height:4.5rem" title="Ver foto">` +
                    `<img src="${u}" alt="" width="72" height="72" class="w-100 h-100" style="object-fit:cover" loading="lazy"/>` +
                    `</a>`
                  );
                })
                .join('') +
              `</div>`
            : '';
        return (
          `<li class="small mb-2 pb-2 border-bottom wo-point-row" data-point-id="${p.id}">` +
          `<div class="fw-semibold">${zname}</div>` +
          `<div class="text-muted">${dlab} · severidad <span class="text-dark">${slab}</span></div>` +
          notesBlock +
          photosBlock +
          `<div class="mt-1 d-flex flex-wrap gap-2 align-items-center">` +
          `<button type="button" class="btn btn-link btn-sm p-0 wo-edit-point" data-id="${p.id}">Editar</button>` +
          `<button type="button" class="btn btn-link btn-sm p-0 text-danger wo-del-point" data-id="${p.id}">Eliminar</button>` +
          `</div></li>`
        );
      })
      .join('');
    ul.querySelectorAll('.wo-del-point').forEach((btn) =>
      btn.addEventListener('click', async (ev) => {
        ev.stopPropagation();
        try {
          await api(`/api/workshop/inspection-points/${btn.dataset.id}`, 'DELETE');
          await loadInspection();
        } catch (e) {
          showErr(e.message);
        }
      }),
    );
    ul.querySelectorAll('.wo-edit-point').forEach((btn) =>
      btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const id = Number(btn.dataset.id);
        const p = (inspection.points || []).find((x) => Number(x.id) === id);
        if (p) openDamageEditModal(p);
      }),
    );
  }

  function openZoneModal(zoneCode) {
    if (!order || !order.id) {
      alert('Guarde la orden primero para usar el mapa de inspección.');
      return;
    }
    const modalEl = document.getElementById('woDamageModal');
    const pidEl = document.getElementById('woModalPointId');
    const actEl = document.getElementById('woDamageModalAction');
    if (pidEl) pidEl.value = '';
    if (actEl) actEl.textContent = 'Registrar';
    const pick = document.getElementById('woModalZonePick');
    if (pick) {
      if (zoneCode && [...pick.options].some((o) => o.value === zoneCode)) pick.value = zoneCode;
      else if (pick.options.length) pick.selectedIndex = 0;
      syncModalZoneTitle(zoneCode);
    } else {
      syncModalZoneTitle(zoneCode);
    }
    clearModalExistingPhotos();
    document.getElementById('woModalDamage').value = 'scratch';
    document.getElementById('woModalSeverity').value = 'low';
    document.getElementById('woModalNotes').value = '';
    document.getElementById('woModalPhoto').value = '';
    if (window.bootstrap && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function openDamageEditModal(p) {
    if (!order || !order.id || !p) return;
    const modalEl = document.getElementById('woDamageModal');
    const pidEl = document.getElementById('woModalPointId');
    const actEl = document.getElementById('woDamageModalAction');
    if (pidEl) pidEl.value = String(p.id);
    if (actEl) actEl.textContent = 'Editar';
    const pick = document.getElementById('woModalZonePick');
    const zc = p.zone_code || '';
    if (pick) {
      if (zc && [...pick.options].some((o) => o.value === zc)) pick.value = zc;
      else if (pick.options.length) pick.selectedIndex = 0;
      syncModalZoneTitle(zc);
    } else {
      syncModalZoneTitle(zc);
    }
    fillModalExistingPhotos(p);
    const dmg = document.getElementById('woModalDamage');
    if (dmg) dmg.value = p.damage_type || 'scratch';
    const sev = document.getElementById('woModalSeverity');
    if (sev) sev.value = p.severity || 'low';
    document.getElementById('woModalNotes').value = (p.notes && String(p.notes)) || '';
    document.getElementById('woModalPhoto').value = '';
    if (window.bootstrap && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  async function uploadInspectionPointPhoto(pointId, fileInp) {
    if (!fileInp || !fileInp.files || !fileInp.files[0] || !pointId) return;
    const fd = new FormData();
    fd.append('file', fileInp.files[0]);
    const r = await fetch(`/api/workshop/inspection-points/${pointId}/photos`, {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || d.error || r.status);
  }

  async function saveDamageFromModal() {
    const pointIdRaw = (document.getElementById('woModalPointId') && document.getElementById('woModalPointId').value) || '';
    const pointId = pointIdRaw ? Number(pointIdRaw) : 0;
    const zonePick = document.getElementById('woModalZonePick');
    const zone = zonePick ? zonePick.value : '';
    const damage = document.getElementById('woModalDamage').value;
    const sev = document.getElementById('woModalSeverity').value;
    const notes = document.getElementById('woModalNotes').value.trim();
    const fileInp = document.getElementById('woModalPhoto');
    try {
      let pid = pointId;
      if (pointId > 0) {
        await api(`/api/workshop/inspection-points/${pointId}`, 'PATCH', {
          zone_code: zone,
          damage_type: damage,
          severity: sev,
          notes: notes || null,
        });
      } else {
        const res = await api(`/api/workshop/orders/${order.id}/inspection/points`, 'POST', {
          zone_code: zone,
          damage_type: damage,
          severity: sev,
          notes,
          photos: [],
        });
        if (res.inspection_id) inspection.inspection_id = res.inspection_id;
        pid = res.id;
      }
      if (fileInp && fileInp.files && fileInp.files[0] && pid) {
        await uploadInspectionPointPhoto(pid, fileInp);
      }
      if (window.bootstrap) {
        const m = document.getElementById('woDamageModal');
        window.bootstrap.Modal.getInstance(m)?.hide();
      }
      await loadInspection();
      clearErr();
    } catch (e) {
      showErr(e.message);
    }
  }

  function renderPhotosGallery(photos) {
    const el = document.getElementById('woPhotosGallery');
    if (!el) return;
    const KIND = { entrada: 'Entrada', proceso: 'Proceso', salida: 'Salida' };
    if (!photos || !photos.length) {
      el.innerHTML = '<p class="text-muted small mb-0">Sin fotos de la orden. Suba imágenes arriba.</p>';
      return;
    }
    el.innerHTML =
      '<div class="row g-2">' +
      photos
        .map((p) => {
          const u = String(p.url || '').replace(/"/g, '&quot;');
          const k = escHtml(KIND[p.kind] || p.kind || '');
          return (
            '<div class="col-6 col-md-4"><div class="card border h-100"><a href="' +
            u +
            '" target="_blank" rel="noopener" class="d-block bg-light"><img src="' +
            u +
            '" class="w-100 rounded-top" style="max-height:140px;object-fit:cover" alt="Foto orden" loading="lazy"/></a><div class="small text-muted px-2 py-1">' +
            k +
            '</div></div></div>'
          );
        })
        .join('') +
      '</div>';
  }

  function fillForm(o) {
    document.getElementById('woCode').textContent = o.code || '—';
    document.getElementById('woStatus').textContent = o.status || '';
    if (customerId) customerId.value = o.customer_id || '';
    if (customerSearch) {
      if (o.customer_name || o.customer_email) {
        const nm = (o.customer_name || '').trim();
        const em = (o.customer_email || '').trim();
        const disp = em && nm ? `${nm} (${em})` : nm || em || '';
        customerSearch.value = disp;
        if (disp) customerSearch.dataset.lockedLabel = disp;
        else delete customerSearch.dataset.lockedLabel;
      } else {
        customerSearch.value = '';
        delete customerSearch.dataset.lockedLabel;
      }
    }
    document.getElementById('vehPlate').value = (o.vehicle && o.vehicle.plate) || '';
    document.getElementById('vehBrand').value = (o.vehicle && o.vehicle.brand) || '';
    document.getElementById('vehModel').value = (o.vehicle && o.vehicle.model) || '';
    document.getElementById('vehYear').value = (o.vehicle && o.vehicle.year) || '';
    document.getElementById('vehColor').value = (o.vehicle && o.vehicle.color) || '';
    document.getElementById('vehVin').value = (o.vehicle && o.vehicle.vin) || '';
    document.getElementById('vehMileage').value = (o.vehicle && o.vehicle.mileage) || '';
    document.getElementById('vehNick').value = (o.vehicle && o.vehicle.nickname) || '';
    document.getElementById('woNotes').value = o.notes || '';
    document.getElementById('woQcNotes').value = o.qc_notes || '';
    document.getElementById('woGrand').textContent = fmt(o.total_estimated);
    const qLink = document.getElementById('woQuotationLink');
    if (qLink) {
      if (o.quotation_id) {
        qLink.href = `/admin/sales/quotations/${o.quotation_id}`;
        qLink.classList.remove('d-none');
      } else qLink.classList.add('d-none');
    }
    const wi = document.getElementById('woInvoiceId');
    if (wi) wi.value = o.invoice_id != null && o.invoice_id !== '' ? o.invoice_id : '';
    const hint = document.getElementById('woInvoiceHint');
    if (hint) {
      hint.textContent = o.invoice_id ? `Registrado: factura #${o.invoice_id}` : '';
    }
    renderLines(o.lines || []);
    renderPhotosGallery(o.photos || []);
  }

  async function saveOrder() {
    clearErr();
    const cust = Number((customerId && customerId.value) || 0);
    if (cust < 1) {
      showErr('Seleccione un cliente de la lista o cree uno nuevo.');
      return;
    }
    const vehicle = {
      plate: document.getElementById('vehPlate').value.trim(),
      brand: document.getElementById('vehBrand').value.trim(),
      model: document.getElementById('vehModel').value.trim(),
      year: document.getElementById('vehYear').value ? Number(document.getElementById('vehYear').value) : null,
      color: document.getElementById('vehColor').value.trim(),
      vin: document.getElementById('vehVin').value.trim(),
      mileage: Number(document.getElementById('vehMileage').value || 0),
      nickname: document.getElementById('vehNick').value.trim() || null,
    };
    const payload = {
      customer_id: cust,
      vehicle,
      lines: collectLines(),
      notes: document.getElementById('woNotes').value.trim() || null,
      qc_notes: document.getElementById('woQcNotes').value.trim() || null,
    };
    const wi = document.getElementById('woInvoiceId');
    try {
      if (order && order.id) {
        if (wi) {
          const v = wi.value.trim();
          payload.invoice_id = v ? Number(v) : null;
        }
        order = await api(`/api/workshop/orders/${order.id}`, 'PATCH', payload);
        await persistChecklist();
      } else {
        order = await api('/api/workshop/orders', 'POST', {
          ...payload,
          checklist: collectChecklist(),
        });
        location.href = `/admin/workshop/orders/${order.id}`;
        return;
      }
      fillForm(order);
      await loadChecklist();
      clearErr();
    } catch (e) {
      showErr(e.message);
    }
  }

  async function transition(st) {
    if (!order || !order.id) return;
    try {
      order = await api(`/api/workshop/orders/${order.id}`, 'PATCH', { status: st });
      fillForm(order);
      clearErr();
    } catch (e) {
      showErr(e.message);
    }
  }

  async function uploadOrderPhoto() {
    const inp = document.getElementById('woPhotoFile');
    const kindEl = document.getElementById('woPhotoKind');
    const kind = kindEl && kindEl.value ? kindEl.value : 'entrada';
    if (!inp || !inp.files || !inp.files[0] || !order || !order.id) return;
    const fd = new FormData();
    fd.append('file', inp.files[0]);
    fd.append('kind', kind);
    const r = await fetch(`/api/workshop/orders/${order.id}/photos`, { method: 'POST', body: fd, credentials: 'same-origin' });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      showErr(d.detail || d.error || r.status);
      return;
    }
    inp.value = '';
    clearErr();
    try {
      const fresh = await api(`/api/workshop/orders/${order.id}`);
      order = fresh;
      renderPhotosGallery(fresh.photos || []);
    } catch (_) {
      /* ignore refresh */
    }
  }

  bindCustomerM2o();
  bindLineItemsM2o();

  initInspectionMapToggle();

  document.getElementById('btnWoNewCustSave')?.addEventListener('click', () => {
    submitNewCustomer().catch(() => {});
  });

  document.getElementById('btnWoSave')?.addEventListener('click', saveOrder);
  document.getElementById('btnWoQuote')?.addEventListener('click', async () => {
    if (!order || !order.id) return;
    try {
      const res = await api(`/api/workshop/orders/${order.id}/create-quotation`, 'POST', {});
      clearErr();
      if (res.admin_url) location.href = res.admin_url;
    } catch (e) {
      showErr(e.message);
    }
  });
  document.getElementById('btnWoPhoto')?.addEventListener('click', () => uploadOrderPhoto());

  document.querySelectorAll('.wo-trans').forEach((btn) =>
    btn.addEventListener('click', () => transition(btn.dataset.status)),
  );

  document.querySelectorAll('.workshop-body-map-svg .car-zone').forEach((el) =>
    el.addEventListener('click', () => openZoneModal(el.id)),
  );
  document.getElementById('woModalSave')?.addEventListener('click', saveDamageFromModal);
  document.getElementById('woModalZonePick')?.addEventListener('change', syncModalZoneTitle);

  document.getElementById('btnWoAddLine')?.addEventListener('click', () => {
    const tb = document.getElementById('wolLines');
    const wrap = document.createElement('tbody');
    wrap.innerHTML = lineRow({}, tb.querySelectorAll('tr').length);
    const row = wrap.firstElementChild;
    tb.appendChild(row);
    wireLineRow(row, [{}]);
  });

  (async function boot() {
    try {
      await loadTaxes();
      await loadZones();
      if (orderId > 0) {
        order = await api(`/api/workshop/orders/${orderId}`);
        fillForm(order);
        await loadChecklist();
        await loadInspection();
      } else {
        document.getElementById('woCode').textContent = 'Nueva';
        renderChecklist([]);
        renderLines([]);
        renderPhotosGallery([]);
        paintZones();
      }
    } catch (e) {
      showErr(e.message || String(e));
    }
  })();
})();

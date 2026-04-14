(function () {
  const root = document.getElementById('odooInvoiceForm');
  if (!root) return;
  if (!window.QuotationLinesComponent || typeof window.QuotationLinesComponent.mount !== 'function') {
    const fe = document.getElementById('invFormError');
    if (fe) {
      fe.textContent = 'No se cargó quotation_lines_component.js. Recargue la página (Ctrl+F5).';
      fe.classList.remove('d-none');
    }
    return;
  }

  const iid = Number(root.dataset.invoiceId);
  const INV_BASE = String(root.dataset.invApiBase || '/invoices').replace(/\/$/, '');
  const SALES_Q_BASE = '/api/sales/quotations';

  const err = document.getElementById('invFormError');
  const lineItems = document.getElementById('invLineItems');
  if (!lineItems) return;

  const customerId = document.getElementById('invCustomerId');
  const customerSearch = document.getElementById('invCustomerSearch');
  const customerMenu = document.getElementById('invCustomerMenu');
  const salespersonSearch = document.getElementById('invSalespersonSearch');
  const salespersonMenu = document.getElementById('invSalespersonMenu');
  const salespersonUserId = document.getElementById('invSalespersonUserId');
  const invDate = document.getElementById('invDate');
  const invDueDate = document.getElementById('invDueDate');
  const invOriginLabel = document.getElementById('invOriginLabel');

  let taxes = [];
  let inv = null;
  let serviceCatalogCache = [];
  let servicePickTargetTr = null;

  const fmt = (n) => `B/. ${Number(n || 0).toFixed(2)}`;
  const SVC_DEBOUNCE_MS = 300;
  const CUST_DEBOUNCE_MS = 300;
  const SP_DEBOUNCE_MS = 300;

  function canEditContentForInv(row) {
    return row && row.status === 'draft';
  }
  function canEditContent() {
    return canEditContentForInv(inv);
  }

  function showSavedToast() {
    const el = document.getElementById('invSavedToast');
    if (!el) return;
    el.classList.remove('d-none');
    el.classList.add('show');
    clearTimeout(root._savedToastT);
    root._savedToastT = setTimeout(() => {
      el.classList.add('d-none');
      el.classList.remove('show');
    }, 2200);
  }

  function applyEditMode() {
    if (!inv) return;
    const editable = canEditContent();
    root.classList.toggle('quote-odoo-readonly', !editable);
    const banner = document.getElementById('invReadonlyBanner');
    if (banner) banner.classList.toggle('d-none', editable);
    const roIds = ['invCustomerSearch', 'invOriginLabel'];
    roIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.readOnly = !editable || id === 'invOriginLabel';
    });
    if (invDate) invDate.readOnly = !editable;
    if (invDueDate) invDueDate.disabled = !editable;
    const btnAdd = document.getElementById('invBtnAddLine');
    const btnExtras = document.getElementById('invBtnLineExtras');
    if (btnAdd) btnAdd.disabled = !editable;
    if (btnExtras) btnExtras.disabled = !editable;

    const st = String(inv.status || '');
    const btnSave = document.getElementById('invBtnSave');
    const btnPost = document.getElementById('invBtnPost');
    const btnPay = document.getElementById('invBtnPay');
    const btnCancel = document.getElementById('invBtnCancel');
    const btnDelete = document.getElementById('invBtnDelete');
    if (btnSave) btnSave.disabled = !editable;
    if (btnPost) btnPost.disabled = st !== 'draft';
    if (btnPay) btnPay.disabled = st !== 'posted';
    if (btnCancel) btnCancel.disabled = st === 'cancelled' || st === 'paid';
    if (btnDelete) {
      btnDelete.disabled = st !== 'draft';
      btnDelete.title = st === 'draft' ? 'Eliminar borrador' : 'Solo en borrador';
    }
  }

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

  const API_ERROR_LABELS = {
    invoice_not_editable: 'Solo se puede editar en borrador.',
    invoice_not_draft: 'La factura debe estar en borrador.',
    invoice_must_be_draft: 'La factura debe estar en borrador para contabilizarla.',
    invoice_must_be_posted: 'La factura debe estar contabilizada para registrar el pago.',
    paid_invoice_cannot_be_cancelled: 'No se puede cancelar una factura pagada.',
    forbidden: 'No tiene permiso para esta acción.',
    not_found: 'No se encontró el recurso solicitado.',
  };

  function humanizeApiMessage(m) {
    const s = String(m == null ? '' : m).trim();
    if (!s) return 'Error';
    if (API_ERROR_LABELS[s]) return API_ERROR_LABELS[s];
    return s;
  }

  const showError = (m) => {
    err.textContent = humanizeApiMessage(m);
    err.classList.remove('d-none');
  };
  const clearError = () => {
    err.classList.add('d-none');
    err.textContent = '';
  };

  async function fetchJsonAbsolute(absolutePath, method = 'GET', body = null) {
    const url = absolutePath.startsWith('/') ? absolutePath : `/${absolutePath}`;
    const headers = { Accept: 'application/json' };
    if (body != null || (method !== 'GET' && method !== 'HEAD')) {
      headers['Content-Type'] = 'application/json';
    }
    const init = { method, credentials: 'same-origin', headers };
    if (body != null) init.body = JSON.stringify(body);
    const res = await fetch(url, init);
    const text = await res.text().catch(() => '');
    const t = text.trim();
    const ct = (res.headers.get('Content-Type') || '').toLowerCase();
    if (ct.includes('text/html') || t.startsWith('<!') || t.startsWith('<html')) {
      throw new Error(
        'El servidor devolvió HTML en lugar de JSON (suele ser sesión caducada). Recargue e inicie sesión.',
      );
    }
    let data;
    try {
      data = t ? JSON.parse(t) : {};
    } catch {
      throw new Error(`HTTP ${res.status}: respuesta no válida`);
    }
    if (!res.ok) {
      const code = typeof data.error === 'string' ? data.error : '';
      let msg =
        (typeof data.user_message === 'string' && data.user_message) ||
        (typeof data.detail === 'string' && data.detail) ||
        code ||
        `HTTP ${res.status}`;
      if (code && API_ERROR_LABELS[code]) msg = API_ERROR_LABELS[code];
      throw new Error(msg);
    }
    return data;
  }

  async function invApi(urlPath, method = 'GET', body = null) {
    const suffix = urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
    return fetchJsonAbsolute(INV_BASE + suffix, method, body);
  }

  async function salesApi(urlPath, method = 'GET', body = null) {
    const suffix = urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
    return fetchJsonAbsolute(SALES_Q_BASE + suffix, method, body);
  }

  async function loadTaxes() {
    let data;
    try {
      data = await fetchJsonAbsolute('/api/taxes?include_inactive=1');
    } catch (e1) {
      try {
        data = await fetchJsonAbsolute('/taxes?include_inactive=1');
      } catch (e2) {
        throw e1;
      }
    }
    taxes = Array.isArray(data) ? data : [];
  }

  function lineTax(line) {
    return taxes.find((t) => Number(t.id) === Number(line.tax_id)) || null;
  }

  function priceIncludedTax(tax) {
    if (!tax) return false;
    if (tax.price_included != null) return !!tax.price_included;
    return tax.type === 'included';
  }

  function computationModeTax(tax) {
    const c = tax.computation || 'percent';
    return c === 'fixed' ? 'fixed' : 'percent';
  }

  function computeLine(line) {
    if (line.is_note) return { subtotal: 0, tax: 0, total: 0 };
    const qty = Number(line.quantity || 0);
    const pu = Number(line.price_unit || 0);
    const amount = qty * pu;
    const tax = lineTax(line);
    if (!tax) return { subtotal: amount, tax: 0, total: amount };
    const inc = priceIncludedTax(tax);
    const comp = computationModeTax(tax);
    const rate = Number(tax.rate != null ? tax.rate : tax.percentage || 0);
    const fixed = Number(tax.amount_fixed || 0);
    if (comp === 'fixed') {
      const taxAmt = fixed * qty;
      if (inc) {
        const subtotal = Math.max(0, amount - taxAmt);
        return { subtotal, tax: taxAmt, total: amount };
      }
      return { subtotal: amount, tax: taxAmt, total: amount + taxAmt };
    }
    if (inc) {
      const subtotal = rate > 0 ? amount / (1 + rate / 100) : amount;
      return { subtotal, tax: amount - subtotal, total: amount };
    }
    const taxAmt = amount * (rate / 100);
    return { subtotal: amount, tax: taxAmt, total: amount + taxAmt };
  }

  function recalcUiTotals() {
    if (!canEditContent() && inv) {
      document.getElementById('invSubtotalLbl').textContent = fmt(inv.total);
      document.getElementById('invTaxLbl').textContent = fmt(inv.tax_total);
      document.getElementById('invGrandLbl').textContent = fmt(inv.grand_total);
      return;
    }
    const lines = window.QuotationLinesComponent.collect(lineItems);
    let subtotal = 0;
    let tax = 0;
    let grand = 0;
    [...lineItems.querySelectorAll('tr')].forEach((tr, idx) => {
      const calc = computeLine(lines[idx] || {});
      subtotal += calc.subtotal;
      tax += calc.tax;
      grand += calc.total;
      const totalCell = tr.querySelector('.li-total');
      if (totalCell) totalCell.textContent = Number(calc.total || 0).toFixed(2);
    });
    document.getElementById('invSubtotalLbl').textContent = fmt(subtotal);
    document.getElementById('invTaxLbl').textContent = fmt(tax);
    document.getElementById('invGrandLbl').textContent = fmt(grand);
  }

  function setStatus(status) {
    ['invStDraft', 'invStPosted', 'invStPaid', 'invStCancelled'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.opacity = '0.35';
    });
    const map = {
      draft: 'invStDraft',
      posted: 'invStPosted',
      paid: 'invStPaid',
      cancelled: 'invStCancelled',
    };
    const id = map[status];
    if (id) {
      const el = document.getElementById(id);
      if (el) el.style.opacity = '1';
    }
  }

  function closeCustomerMenu() {
    if (!customerMenu) return;
    customerMenu.classList.remove('show');
    customerMenu.innerHTML = '';
    if (customerSearch) customerSearch.setAttribute('aria-expanded', 'false');
  }

  function closeSalespersonMenu() {
    if (!salespersonMenu) return;
    salespersonMenu.classList.remove('show');
    salespersonMenu.innerHTML = '';
    if (salespersonSearch) salespersonSearch.setAttribute('aria-expanded', 'false');
  }

  function setSalespersonHighlight(menu, index) {
    const opts = [...menu.querySelectorAll('.sp-m2o-opt')];
    opts.forEach((el, i) => el.classList.toggle('odoo-m2o-item-active', i === index));
    if (opts[index]) opts[index].scrollIntoView({ block: 'nearest' });
    return opts;
  }

  function buildSalespersonDropdownHtml(rows) {
    const body = rows
      .map((r) => {
        const title = escHtml(r.name || r.email || r.code || '');
        const meta =
          r.email && String(r.email) !== String(r.name || '')
            ? `<span class="odoo-m2o-item-meta">${escHtml(r.email)}</span>`
            : r.code
              ? `<span class="odoo-m2o-item-meta">${escHtml(r.code)}</span>`
              : '';
        return `<button type="button" class="odoo-m2o-item sp-m2o-opt" data-id="${r.id}" data-name="${escAttr(r.name || '')}" data-email="${escAttr(r.email || '')}" data-code="${escAttr(r.code || '')}"><span class="odoo-m2o-item-title">${title}</span>${meta}</button>`;
      })
      .join('');
    const empty =
      '<div class="px-3 py-2 small text-muted">Sin vendedores. En <strong>Usuarios</strong> marque «Es vendedor».</div>';
    return `${rows.length ? body : empty}<div class="odoo-m2o-hint">Miembros con «Es vendedor»</div>`;
  }

  async function renderSalespersonDropdown(q, limit) {
    if (!salespersonMenu || !salespersonSearch) return;
    root._spFetch = (root._spFetch || 0) + 1;
    const fid = root._spFetch;
    salespersonMenu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
    salespersonMenu.classList.add('show');
    salespersonSearch.setAttribute('aria-expanded', 'true');
    try {
      const list = await salesApi(`/salespersons/search?q=${encodeURIComponent(q)}&limit=${limit}`);
      const arr = Array.isArray(list) ? list : [];
      if (fid !== root._spFetch) return;
      salespersonMenu.innerHTML = buildSalespersonDropdownHtml(arr);
      root._spM2oIndex = arr.length ? 0 : -1;
      setSalespersonHighlight(salespersonMenu, root._spM2oIndex);
    } catch (e) {
      if (fid !== root._spFetch) return;
      salespersonMenu.innerHTML = `<div class="px-3 py-2 small text-danger">${escAttr(e.message)}</div>`;
    }
  }

  async function applySalespersonPick(r) {
    if (!salespersonUserId || !salespersonSearch) return;
    salespersonUserId.value = String(r.id);
    const disp =
      r.email && r.name ? `${r.name} (${r.email})` : r.name || r.email || r.code || String(r.id);
    salespersonSearch.value = disp;
    salespersonSearch.dataset.lockedLabel = disp;
    closeSalespersonMenu();
  }

  function setCustomerHighlight(menu, index) {
    const opts = [...menu.querySelectorAll('.cust-m2o-opt')];
    opts.forEach((el, i) => el.classList.toggle('odoo-m2o-item-active', i === index));
    if (opts[index]) opts[index].scrollIntoView({ block: 'nearest' });
    return opts;
  }

  function buildCustomerDropdownHtml(users) {
    const body = users
      .map((u) => {
        const title = escHtml(u.name || u.email || '');
        const em =
          u.email && String(u.email) !== String(u.name || '')
            ? `<span class="odoo-m2o-item-meta">${escHtml(u.email)}</span>`
            : '';
        return `<button type="button" class="odoo-m2o-item cust-m2o-opt" data-id="${u.id}" data-name="${escAttr(u.name || '')}" data-email="${escAttr(u.email || '')}"><span class="odoo-m2o-item-title">${title}</span>${em}</button>`;
      })
      .join('');
    const empty = '<div class="px-3 py-2 small text-muted">Sin resultados</div>';
    return `${users.length ? body : empty}<div class="odoo-m2o-hint">Miembros activos</div>`;
  }

  async function renderCustomerDropdown(q, limit) {
    if (!canEditContent()) return;
    if (!customerMenu || !customerSearch) return;
    root._custFetch = (root._custFetch || 0) + 1;
    const fid = root._custFetch;
    customerMenu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
    customerMenu.classList.add('show');
    customerSearch.setAttribute('aria-expanded', 'true');
    try {
      const users = await salesApi(`/customers/search?q=${encodeURIComponent(q)}&limit=${limit}`);
      if (fid !== root._custFetch) return;
      const list = Array.isArray(users) ? users : [];
      customerMenu.innerHTML = buildCustomerDropdownHtml(list);
      root._custM2oIndex = list.length ? 0 : -1;
      setCustomerHighlight(customerMenu, root._custM2oIndex);
    } catch (e) {
      if (fid !== root._custFetch) return;
      customerMenu.innerHTML = `<div class="px-3 py-2 small text-danger">${escAttr(e.message)}</div>`;
    }
  }

  function applyCustomerPick(u) {
    customerId.value = String(u.id);
    const disp = u.email && u.name ? `${u.name} (${u.email})` : u.name || u.email || '';
    customerSearch.value = disp;
    customerSearch.dataset.lockedLabel = disp;
    closeCustomerMenu();
  }

  function closeAllServiceMenus(exceptTr = null) {
    document.querySelectorAll('#invLineItems .li-product-menu.show').forEach((menu) => {
      const tr = menu.closest('tr');
      if (exceptTr && tr === exceptTr) return;
      menu.classList.remove('show');
      menu.innerHTML = '';
      const inp = tr && tr.querySelector('.li-product-search');
      if (inp) inp.setAttribute('aria-expanded', 'false');
    });
  }

  function applyServiceToRow(tr, p) {
    tr.querySelector('.li-product').value = p.id;
    tr.querySelector('.li-product-search').value = p.name || '';
    tr.querySelector('.li-desc').value = (p.description || p.name || '').trim() || p.name || '';
    tr.querySelector('.li-price').value = Number(p.price_unit || 0).toFixed(2);
    const taxSel = tr.querySelector('.li-tax');
    if (taxSel) {
      let tid = p.default_tax_id != null && p.default_tax_id !== '' ? Number(p.default_tax_id) : null;
      if (tid == null || Number.isNaN(tid)) tid = taxes.length === 1 ? Number(taxes[0].id) : null;
      if (tid != null && !Number.isNaN(tid)) taxSel.value = String(tid);
    }
    closeAllServiceMenus();
    recalcUiTotals();
  }

  function setM2oHighlight(menu, index) {
    const opts = [...menu.querySelectorAll('.li-product-option')];
    opts.forEach((el, i) => el.classList.toggle('odoo-m2o-item-active', i === index));
    if (opts[index]) opts[index].scrollIntoView({ block: 'nearest' });
    return opts;
  }

  function buildServiceDropdownHtml(products) {
    const fmtPu = (n) => `B/. ${Number(n || 0).toFixed(2)}`;
    let body = products
      .map((p) => {
        const code = p.code != null && String(p.code) !== '' ? String(p.code) : String(p.id);
        const dt =
          p.default_tax_id != null && p.default_tax_id !== '' ? escAttr(String(p.default_tax_id)) : '';
        return `<button type="button" class="odoo-m2o-item li-product-option" data-id="${p.id}" data-name="${escAttr(p.name)}" data-desc="${escAttr(p.description || '')}" data-price="${Number(p.price_unit || 0)}" data-tax="${dt}"><span class="odoo-m2o-item-title">${escHtml(p.name)}</span><span class="odoo-m2o-item-meta"><span class="text-muted">Ref. ${escHtml(code)}</span> · ${escHtml(fmtPu(p.price_unit))}</span></button>`;
      })
      .join('');
    if (!products.length) body = '<div class="px-3 py-2 small text-muted">Sin resultados</div>';
    return `${body}<div class="odoo-m2o-footer"><a href="#" class="odoo-m2o-more li-product-more">Catálogo completo…</a></div><div class="odoo-m2o-hint">Nombre, descripción o ID</div>`;
  }

  async function renderServiceDropdown(tr, q, limit) {
    if (!canEditContent()) return;
    const menu = tr.querySelector('.li-product-menu');
    const inp = tr.querySelector('.li-product-search');
    tr._svcFetch = (tr._svcFetch || 0) + 1;
    const fid = tr._svcFetch;
    menu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
    menu.classList.add('show');
    inp.setAttribute('aria-expanded', 'true');
    try {
      const products = await salesApi(`/products/search?q=${encodeURIComponent(q)}&limit=${limit}`);
      if (fid !== tr._svcFetch) return;
      const arr = Array.isArray(products) ? products : [];
      menu.innerHTML = buildServiceDropdownHtml(arr);
      tr._m2oIndex = arr.length ? 0 : -1;
      setM2oHighlight(menu, tr._m2oIndex);
    } catch (e) {
      if (fid !== tr._svcFetch) return;
      menu.innerHTML = `<div class="px-3 py-2 small text-danger">${escAttr(e.message)}</div>`;
    }
  }

  function openServiceCatalogModal(tr) {
    if (!canEditContent()) return;
    closeAllServiceMenus();
    servicePickTargetTr = tr;
    const modalEl = document.getElementById('invServiceCatalogModal');
    const tbody = document.getElementById('invServiceCatalogRows');
    const filter = document.getElementById('invServiceCatalogFilter');
    filter.value = '';
    tbody.innerHTML = '<tr><td class="text-muted small p-2" colspan="3">Cargando…</td></tr>';
    if (window.bootstrap && window.bootstrap.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
    salesApi('/products/search?q=&limit=500')
      .then((list) => {
        serviceCatalogCache = list;
        renderServiceCatalogRows('');
      })
      .catch(() => {
        tbody.innerHTML = '<tr><td class="text-danger small p-2" colspan="3">Error al cargar servicios</td></tr>';
      });
  }

  function renderServiceCatalogRows(filterQ) {
    const tbody = document.getElementById('invServiceCatalogRows');
    const fq = (filterQ || '').toLowerCase().trim();
    const list = fq
      ? serviceCatalogCache.filter((p) =>
          `${p.name} ${p.description || ''} ${p.code || p.id}`.toLowerCase().includes(fq),
        )
      : serviceCatalogCache;
    tbody.innerHTML =
      list
        .map((p) => {
          const code = p.code != null && String(p.code) !== '' ? String(p.code) : String(p.id);
          const pu = `B/. ${Number(p.price_unit || 0).toFixed(2)}`;
          const dtax =
            p.default_tax_id != null && p.default_tax_id !== '' ? escAttr(String(p.default_tax_id)) : '';
          return `<tr class="li-catalog-row" style="cursor:pointer" data-id="${p.id}" data-name="${escAttr(p.name)}" data-desc="${escAttr(p.description || '')}" data-price="${Number(p.price_unit || 0)}" data-tax="${dtax}"><td class="small py-1"><strong>${escHtml(p.name)}</strong><div class="text-muted" style="font-size:0.75rem">Ref. ${escHtml(code)}</div></td><td class="small text-muted py-1">${escHtml(String(p.description || '').slice(0, 100))}</td><td class="small text-end py-1">${escHtml(pu)}</td></tr>`;
        })
        .join('') || '<tr><td class="text-muted small p-2" colspan="3">Sin coincidencias</td></tr>';
  }

  async function loadInvoice() {
    clearError();
    const row = await invApi(`/${iid}`);
    inv = row;
    root.dataset.status = row.status;
    document.getElementById('invNumber').textContent = row.number;
    customerId.value = row.customer_id || '';
    if (customerSearch) {
      const disp = row.customer_email
        ? `${(row.customer_name || row.customer_email).trim()} (${row.customer_email})`
        : (row.customer_name || '').trim();
      customerSearch.value = disp;
      if (disp) customerSearch.dataset.lockedLabel = disp;
      else delete customerSearch.dataset.lockedLabel;
    }
    if (salespersonUserId) {
      const sid = row.salesperson_user_id;
      salespersonUserId.value =
        sid != null && sid !== '' && !Number.isNaN(Number(sid)) ? String(Number(sid)) : '';
    }
    if (salespersonSearch) {
      let sd = '';
      if (row.salesperson_name || row.salesperson_email) {
        const sn = (row.salesperson_name || '').trim();
        const se = (row.salesperson_email || '').trim();
        sd = sn && se ? `${sn} (${se})` : sn || se;
      }
      salespersonSearch.value = sd;
      if (sd) salespersonSearch.dataset.lockedLabel = sd;
      else delete salespersonSearch.dataset.lockedLabel;
    }
    if (invDate) invDate.value = row.date ? row.date.slice(0, 10) : '';
    if (invDueDate) invDueDate.value = row.due_date ? row.due_date.slice(0, 10) : '';
    if (invOriginLabel) {
      if (row.origin_quotation_id && row.origin_quotation_number) {
        invOriginLabel.value = `Cotización ${row.origin_quotation_number} (#${row.origin_quotation_id})`;
      } else if (row.origin_quotation_id) {
        invOriginLabel.value = `Cotización #${row.origin_quotation_id}`;
      } else {
        invOriginLabel.value = '';
      }
    }
    const invOrgFiscalText = document.getElementById('invOrgFiscalText');
    if (invOrgFiscalText) {
      const displayName =
        (row.organization_legal_name || row.organization_name || '').trim() || '—';
      const location = [row.organization_fiscal_city, row.organization_fiscal_state, row.organization_fiscal_country]
        .map((x) => String(x || '').trim())
        .filter(Boolean)
        .join(', ');
      const contact = [row.organization_fiscal_phone, row.organization_fiscal_email]
        .map((x) => String(x || '').trim())
        .filter(Boolean)
        .join(' · ');
      const parts = [
        displayName !== '—' ? displayName : '',
        row.organization_tax_id ? `RUC/NIT: ${row.organization_tax_id}` : '',
        row.organization_tax_regime ? `Régimen: ${row.organization_tax_regime}` : '',
        row.organization_fiscal_address || '',
        location || '',
        contact || '',
      ].filter(Boolean);
      invOrgFiscalText.textContent = parts.join(' | ') || 'Sin datos fiscales configurados.';
    }
    document.getElementById('invSubtotalLbl').textContent = fmt(row.total);
    document.getElementById('invTaxLbl').textContent = fmt(row.tax_total);
    document.getElementById('invGrandLbl').textContent = fmt(row.grand_total);
    setStatus(row.status);
    window.QuotationLinesComponent.mount(lineItems, row.lines || [], taxes, {
      readOnly: !canEditContentForInv(row),
    });
    applyEditMode();
    recalcUiTotals();
  }

  async function saveInvoice(opts = {}) {
    const silent = opts.silent === true;
    if (!inv) {
      showError('Factura no cargada.');
      return;
    }
    const spRaw = salespersonUserId ? Number(salespersonUserId.value) : null;
    const spPayload = spRaw && !Number.isNaN(spRaw) && spRaw > 0 ? spRaw : null;

    if (!canEditContent()) {
      const patch = { salesperson_user_id: spPayload };
      const updated = await invApi(`/${iid}`, 'PUT', patch);
      inv = updated;
      root.dataset.status = updated.status;
      window.QuotationLinesComponent.mount(lineItems, updated.lines || [], taxes, {
        readOnly: !canEditContentForInv(updated),
      });
      applyEditMode();
      recalcUiTotals();
      if (!silent) showSavedToast();
      return;
    }

    const lines = window.QuotationLinesComponent.collect(lineItems);
    const cid = Number(customerId.value) || 0;
    if (cid < 1) {
      showError('Seleccione un cliente.');
      return;
    }
    const payload = {
      customer_id: cid,
      due_date:
        invDueDate && invDueDate.value
          ? new Date(`${invDueDate.value}T12:00:00`).toISOString()
          : null,
      lines,
      salesperson_user_id: spPayload,
    };
    if (invDate && invDate.value) {
      payload.date = new Date(`${invDate.value}T12:00:00`).toISOString();
    }
    const updated = await invApi(`/${iid}`, 'PUT', payload);
    inv = updated;
    root.dataset.status = updated.status;
    window.QuotationLinesComponent.mount(lineItems, updated.lines || [], taxes, {
      readOnly: !canEditContentForInv(updated),
    });
    applyEditMode();
    recalcUiTotals();
    if (!silent) showSavedToast();
  }

  function addProductLine() {
    if (!canEditContent()) return;
    try {
      if (!Array.isArray(taxes)) taxes = [];
      const cur = window.QuotationLinesComponent.collect(lineItems);
      cur.push({ description: '', quantity: 1, price_unit: 0, tax_id: null, product_id: null, is_note: false });
      window.QuotationLinesComponent.mount(lineItems, cur, taxes);
      recalcUiTotals();
      const rows = [...lineItems.querySelectorAll('tr:not([data-note="1"])')];
      const last = rows[rows.length - 1];
      const inp = last && last.querySelector('.li-product-search');
      if (inp) inp.focus();
    } catch (e) {
      showError(e.message || String(e));
    }
  }

  function addNoteLine(isSection) {
    if (!canEditContent()) return;
    try {
      if (!Array.isArray(taxes)) taxes = [];
      const cur = window.QuotationLinesComponent.collect(lineItems);
      cur.push({
        description: '',
        quantity: 0,
        price_unit: 0,
        tax_id: null,
        product_id: null,
        is_note: true,
        is_section: Boolean(isSection),
      });
      window.QuotationLinesComponent.mount(lineItems, cur, taxes);
      recalcUiTotals();
      const noteInp = lineItems.querySelector('tr[data-note="1"]:last-of-type .li-note');
      if (noteInp) noteInp.focus();
    } catch (e) {
      showError(e.message || String(e));
    }
  }

  document.addEventListener('mousedown', (e) => {
    if (!e.target.closest('#invCustomerM2o')) closeCustomerMenu();
    if (!e.target.closest('#invSalespersonM2o')) closeSalespersonMenu();
    if (e.target.closest('#invLineItems .odoo-m2o')) return;
    closeAllServiceMenus();
  });

  if (customerSearch && customerMenu) {
    customerSearch.addEventListener('focusin', () => {
      if (!canEditContent()) return;
      renderCustomerDropdown((customerSearch.value || '').trim(), 20);
    });
    customerSearch.addEventListener('input', () => {
      if (!canEditContent()) return;
      if (customerSearch.dataset.lockedLabel && customerSearch.value !== customerSearch.dataset.lockedLabel) {
        customerId.value = '';
        delete customerSearch.dataset.lockedLabel;
      }
      const q = (customerSearch.value || '').trim();
      clearTimeout(root._custDeb);
      root._custDeb = setTimeout(() => renderCustomerDropdown(q, 20), CUST_DEBOUNCE_MS);
    });
    customerSearch.addEventListener('keydown', (e) => {
      if (!canEditContent()) return;
      const menu = customerMenu;
      if (!menu.classList.contains('show')) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          renderCustomerDropdown((customerSearch.value || '').trim(), 20);
        }
        return;
      }
      const opts = [...menu.querySelectorAll('.cust-m2o-opt')];
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
    document.getElementById('invCustomerM2o').addEventListener('click', (e) => {
      const btn = e.target.closest && e.target.closest('.cust-m2o-opt');
      if (!btn) return;
      applyCustomerPick({
        id: btn.dataset.id,
        name: btn.dataset.name,
        email: btn.dataset.email,
      });
    });
  }

  const spM2oRoot = document.getElementById('invSalespersonM2o');
  if (salespersonSearch && salespersonMenu && spM2oRoot) {
    salespersonSearch.addEventListener('focusin', () => {
      renderSalespersonDropdown((salespersonSearch.value || '').trim(), 40);
    });
    salespersonSearch.addEventListener('input', () => {
      if (
        salespersonSearch.dataset.lockedLabel &&
        salespersonSearch.value !== salespersonSearch.dataset.lockedLabel
      ) {
        salespersonUserId.value = '';
        delete salespersonSearch.dataset.lockedLabel;
      }
      const qv = (salespersonSearch.value || '').trim();
      clearTimeout(root._spDeb);
      root._spDeb = setTimeout(() => renderSalespersonDropdown(qv, 40), SP_DEBOUNCE_MS);
    });
    salespersonSearch.addEventListener('keydown', (e) => {
      const menu = salespersonMenu;
      if (!menu.classList.contains('show')) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          renderSalespersonDropdown((salespersonSearch.value || '').trim(), 40);
        }
        return;
      }
      const opts = [...menu.querySelectorAll('.sp-m2o-opt')];
      if (!opts.length) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeSalespersonMenu();
        }
        return;
      }
      let idx = typeof root._spM2oIndex === 'number' ? root._spM2oIndex : 0;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        idx = Math.min(idx + 1, opts.length - 1);
        root._spM2oIndex = idx;
        setSalespersonHighlight(menu, idx);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        idx = Math.max(idx - 1, 0);
        root._spM2oIndex = idx;
        setSalespersonHighlight(menu, idx);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        opts[idx].click();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeSalespersonMenu();
      }
    });
    spM2oRoot.addEventListener('click', (e) => {
      const btn = e.target.closest && e.target.closest('.sp-m2o-opt');
      if (!btn) return;
      void applySalespersonPick({
        id: btn.dataset.id,
        name: btn.dataset.name,
        email: btn.dataset.email,
        code: btn.dataset.code,
      });
    });
  }

  lineItems.addEventListener('focusin', (e) => {
    if (!canEditContent()) return;
    if (!e.target.classList.contains('li-product-search')) return;
    const tr = e.target.closest('tr');
    const q = (e.target.value || '').trim();
    renderServiceDropdown(tr, q, 20);
  });

  lineItems.addEventListener('input', (e) => {
    if (!canEditContent()) return;
    const tr = e.target.closest('tr');
    if (!tr) return;
    if (e.target.classList.contains('li-product-search')) {
      const q = (e.target.value || '').trim();
      clearTimeout(tr._svcDeb);
      tr._svcDeb = setTimeout(() => renderServiceDropdown(tr, q, 20), SVC_DEBOUNCE_MS);
      return;
    }
    recalcUiTotals();
  });

  lineItems.addEventListener('keydown', (e) => {
    if (!canEditContent()) return;
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
        closeAllServiceMenus();
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
      closeAllServiceMenus();
    }
  });

  lineItems.addEventListener('click', (e) => {
    if (!canEditContent()) return;
    const delBtn = e.target.closest && e.target.closest('.li-del');
    if (delBtn) {
      e.preventDefault();
      const tr = delBtn.closest('tr');
      if (tr) tr.remove();
      recalcUiTotals();
      return;
    }
    if (e.target.classList.contains('li-product-toggle')) {
      e.preventDefault();
      const tr = e.target.closest('tr');
      const inp = tr.querySelector('.li-product-search');
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
      return;
    }
    const more = e.target.closest && e.target.closest('.li-product-more');
    if (more) {
      e.preventDefault();
      const tr = more.closest('tr');
      openServiceCatalogModal(tr);
    }
  });

  const svcFilter = document.getElementById('invServiceCatalogFilter');
  const svcRows = document.getElementById('invServiceCatalogRows');
  if (svcFilter && svcRows) {
    svcFilter.addEventListener('input', (ev) => renderServiceCatalogRows(ev.target.value));
    svcRows.addEventListener('click', (ev) => {
      const row = ev.target.closest('.li-catalog-row');
      if (!row || !servicePickTargetTr) return;
      applyServiceToRow(servicePickTargetTr, {
        id: row.dataset.id,
        name: row.dataset.name,
        description: row.dataset.desc,
        price_unit: row.dataset.price,
        default_tax_id: row.dataset.tax || null,
      });
      const modalEl = document.getElementById('invServiceCatalogModal');
      if (window.bootstrap && window.bootstrap.Modal) {
        window.bootstrap.Modal.getInstance(modalEl)?.hide();
      }
    });
  }

  document.getElementById('invBtnAddLine')?.addEventListener('click', (e) => {
    e.preventDefault();
    addProductLine();
  });
  document.getElementById('invMenuAddNote')?.addEventListener('click', (e) => {
    e.preventDefault();
    addNoteLine(false);
  });
  document.getElementById('invMenuAddSection')?.addEventListener('click', (e) => {
    e.preventDefault();
    addNoteLine(true);
  });
  document.getElementById('invMenuOpenCatalog')?.addEventListener('click', (e) => {
    e.preventDefault();
    if (!canEditContent()) return;
    let tr = [...lineItems.querySelectorAll('tr:not([data-note="1"])')].pop();
    if (!tr) {
      addProductLine();
      tr = [...lineItems.querySelectorAll('tr:not([data-note="1"])')].pop();
    }
    if (tr) openServiceCatalogModal(tr);
  });

  document.getElementById('invBtnSave')?.addEventListener('click', async () => {
    try {
      clearError();
      await saveInvoice();
    } catch (e) {
      showError(e.message);
    }
  });

  document.getElementById('invBtnPost')?.addEventListener('click', async () => {
    try {
      clearError();
      if (canEditContent()) await saveInvoice({ silent: true });
      await invApi(`/${iid}/post`, 'POST', {});
      await loadInvoice();
    } catch (e) {
      showError(e.message);
    }
  });

  document.getElementById('invBtnPay')?.addEventListener('click', async () => {
    try {
      clearError();
      await invApi(`/${iid}/pay`, 'POST', {});
      await loadInvoice();
    } catch (e) {
      showError(e.message);
    }
  });

  document.getElementById('invBtnCancel')?.addEventListener('click', async () => {
    if (!window.confirm('¿Cancelar esta factura?')) return;
    try {
      clearError();
      await invApi(`/${iid}/cancel`, 'POST', {});
      await loadInvoice();
    } catch (e) {
      showError(e.message);
    }
  });

  document.getElementById('invBtnDelete')?.addEventListener('click', async () => {
    if (!window.confirm('¿Eliminar este borrador de forma permanente?')) return;
    try {
      clearError();
      await invApi(`/${iid}/delete`, 'POST', {});
      window.location.href = '/admin/accounting/invoices';
    } catch (e) {
      showError(e.message);
    }
  });

  (async function init() {
    try {
      await loadTaxes();
      await loadInvoice();
    } catch (e) {
      showError(e.message || String(e));
    }
  })();
})();

(function () {
  const root = document.getElementById('odooQuotationForm');
  if (!root) return;
  if (!window.QuotationLinesComponent || typeof window.QuotationLinesComponent.mount !== 'function') {
    const fe = document.getElementById('formError');
    if (fe) {
      fe.textContent = 'No se cargó quotation_lines_component.js. Recargue la página (Ctrl+F5).';
      fe.classList.remove('d-none');
    }
    return;
  }
  const qid = Number(root.dataset.quotationId);
  const err = document.getElementById('formError');
  const lineItems = document.getElementById('lineItems');
  if (!lineItems) return;
  const customerId = document.getElementById('customerId');
  const customerSearch = document.getElementById('customerSearch');
  const customerMenu = document.getElementById('customerMenu');
  const paymentTerms = document.getElementById('paymentTerms');
  const validityDate = document.getElementById('validityDate');
  const previewBody = document.getElementById('quotePreviewBody');
  const previewModal = document.getElementById('quotePreviewModal');
  let taxes = [];
  let quote = null;
  let serviceCatalogCache = [];
  let servicePickTargetTr = null;

  const fmt = (n) => `B/. ${Number(n || 0).toFixed(2)}`;
  const SVC_DEBOUNCE_MS = 300;
  const CUST_DEBOUNCE_MS = 300;

  function canEditContentForQuote(q) {
    return q && (q.status === 'draft' || q.status === 'cancelled');
  }
  function canEditContent() {
    return canEditContentForQuote(quote);
  }

  function linesFromApiQuote(q) {
    if (!q || !Array.isArray(q.lines)) return [];
    return q.lines.map((ln) => {
      if (ln.is_note) {
        return {
          is_note: true,
          is_section: false,
          product_id: null,
          description: ln.description || '',
          quantity: 0,
          price_unit: 0,
          tax_id: null,
        };
      }
      return {
        product_id: ln.product_id != null ? Number(ln.product_id) : null,
        description: ln.description || '',
        quantity: Number(ln.quantity) || 0,
        price_unit: Number(ln.price_unit) || 0,
        tax_id: ln.tax_id != null ? Number(ln.tax_id) : null,
        is_note: false,
      };
    });
  }

  function getLinesForPreview() {
    if (canEditContent()) return window.QuotationLinesComponent.collect(lineItems);
    return linesFromApiQuote(quote);
  }

  function showSavedToast() {
    const el = document.getElementById('quoteSavedToast');
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
    if (!quote) return;
    const editable = canEditContent();
    root.classList.toggle('quote-odoo-readonly', !editable);
    const banner = document.getElementById('quoteReadonlyBanner');
    if (banner) banner.classList.toggle('d-none', editable);
    const roIds = ['customerSearch', 'paymentTerms', 'quoteSeller', 'quoteInternalNotes'];
    roIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.readOnly = !editable;
    });
    if (validityDate) validityDate.disabled = !editable;
    const btnAddLineEl = document.getElementById('btnAddLine');
    const btnLineExtras = document.getElementById('btnLineExtras');
    if (btnAddLineEl) btnAddLineEl.disabled = !editable;
    if (btnLineExtras) btnLineExtras.disabled = !editable;
    const st = String(quote.status || '');
    const btnSave = document.getElementById('btnSave');
    const btnConfirm = document.getElementById('btnConfirm');
    const btnSend = document.getElementById('btnSend');
    const btnCancel = document.getElementById('btnCancel');
    const btnCreateInvoice = document.getElementById('btnCreateInvoice');
    const btnViewInvoice = document.getElementById('btnViewInvoice');
    if (btnSave) btnSave.disabled = !editable;
    if (btnConfirm) btnConfirm.disabled = !['draft', 'sent'].includes(st);
    if (btnSend) btnSend.disabled = !['draft', 'sent'].includes(st);
    if (btnCancel) btnCancel.disabled = st === 'cancelled';
    const hasInv = quote.invoice_id != null && Number(quote.invoice_id) > 0;
    if (btnCreateInvoice) {
      btnCreateInvoice.classList.toggle('d-none', hasInv);
      btnCreateInvoice.disabled = st !== 'confirmed' || hasInv;
    }
    if (btnViewInvoice) {
      btnViewInvoice.classList.toggle('d-none', !hasInv);
      if (hasInv && quote.invoice_number) {
        btnViewInvoice.textContent = `Factura ${quote.invoice_number}`;
      } else if (hasInv) {
        btnViewInvoice.textContent = 'Ver factura';
      }
    }
    const btnDeleteQuotation = document.getElementById('btnDeleteQuotation');
    if (btnDeleteQuotation) {
      const canDel = !hasInv && !['invoiced', 'paid'].includes(st);
      btnDeleteQuotation.title = canDel
        ? 'Eliminar esta cotización de forma permanente'
        : 'No disponible: facturada, pagada o con factura asociada';
    }
  }

  function escAttr(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function closeCustomerMenu() {
    if (!customerMenu) return;
    customerMenu.classList.remove('show');
    customerMenu.innerHTML = '';
    if (customerSearch) customerSearch.setAttribute('aria-expanded', 'false');
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
        const em = u.email && String(u.email) !== String(u.name || '') ? `<span class="odoo-m2o-item-meta">${escHtml(u.email)}</span>` : '';
        return `<button type="button" class="odoo-m2o-item cust-m2o-opt" data-id="${u.id}" data-name="${escAttr(u.name || '')}" data-email="${escAttr(u.email || '')}"><span class="odoo-m2o-item-title">${title}</span>${em}</button>`;
      })
      .join('');
    const empty = '<div class="px-3 py-2 small text-muted">Sin resultados</div>';
    return `${users.length ? body : empty}<div class="odoo-m2o-hint">Miembros activos de la organización</div>`;
  }

  async function fetchCustomers(q, limit) {
    return api(`/quotations/customers/search?q=${encodeURIComponent(q)}&limit=${limit}`);
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
      const users = await fetchCustomers(q, limit);
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
    const disp = u.email && u.name ? `${u.name} (${u.email})` : (u.name || u.email || '');
    customerSearch.value = disp;
    customerSearch.dataset.lockedLabel = disp;
    closeCustomerMenu();
  }

  function closeAllServiceMenus(exceptTr = null) {
    document.querySelectorAll('#lineItems .li-product-menu.show').forEach((menu) => {
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
      .map(
        (p) => {
          const code = p.code != null && String(p.code) !== '' ? String(p.code) : String(p.id);
          const dt =
            p.default_tax_id != null && p.default_tax_id !== '' ? escAttr(String(p.default_tax_id)) : '';
          return `<button type="button" class="odoo-m2o-item li-product-option" data-id="${p.id}" data-name="${escAttr(p.name)}" data-desc="${escAttr(p.description || '')}" data-price="${Number(p.price_unit || 0)}" data-tax="${dt}"><span class="odoo-m2o-item-title">${escHtml(p.name)}</span><span class="odoo-m2o-item-meta"><span class="text-muted">Ref. ${escHtml(code)}</span> · ${escHtml(fmtPu(p.price_unit))}</span></button>`;
        },
      )
      .join('');
    if (!products.length) body = '<div class="px-3 py-2 small text-muted">Sin resultados</div>';
    return `${body}<div class="odoo-m2o-footer"><a href="#" class="odoo-m2o-more li-product-more">Catálogo completo…</a></div><div class="odoo-m2o-hint">Nombre, descripción o ID</div>`;
  }

  async function fetchServices(q, limit) {
    return api(`/quotations/products/search?q=${encodeURIComponent(q)}&limit=${limit}`);
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
      const products = await fetchServices(q, limit);
      if (fid !== tr._svcFetch) return;
      menu.innerHTML = buildServiceDropdownHtml(products);
      tr._m2oIndex = products.length ? 0 : -1;
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
    const modalEl = document.getElementById('serviceCatalogModal');
    const tbody = document.getElementById('serviceCatalogRows');
    const filter = document.getElementById('serviceCatalogFilter');
    filter.value = '';
    tbody.innerHTML = '<tr><td class="text-muted small p-2" colspan="3">Cargando…</td></tr>';
    if (window.bootstrap && window.bootstrap.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
    fetchServices('', 500).then((list) => {
      serviceCatalogCache = list;
      renderServiceCatalogRows('');
    }).catch(() => {
      tbody.innerHTML = '<tr><td class="text-danger small p-2" colspan="3">Error al cargar servicios</td></tr>';
    });
  }

  function renderServiceCatalogRows(filterQ) {
    const tbody = document.getElementById('serviceCatalogRows');
    const fq = (filterQ || '').toLowerCase().trim();
    const list = fq
      ? serviceCatalogCache.filter((p) => `${p.name} ${p.description || ''} ${p.code || p.id}`.toLowerCase().includes(fq))
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
  const API_ERROR_LABELS = {
    cancelled_quotation_cannot_be_edited:
      'Esta cotización está cancelada. Al guardar (Vista previa, Confirmar o Enviar) se reabre como borrador. Si sigue igual, recargue con Ctrl+F5.',
    invalid_state:
      'Esta acción no aplica al estado actual de la cotización (por ejemplo: ya confirmada o no se puede enviar en este estado).',
    quotation_needs_lines:
      'Agregue al menos una línea con cantidad mayor que cero antes de confirmar.',
    quotation_not_editable: 'Solo se puede editar en borrador.',
    quotation_must_be_confirmed: 'Debe confirmar la cotización antes de crear la factura.',
    quotation_has_invoice: 'No se puede eliminar: existe una factura asociada a esta cotización.',
    quotation_cannot_delete_final: 'No se puede eliminar una cotización facturada o pagada.',
    forbidden: 'No tiene permiso para esta acción.',
    not_found: 'No se encontró el recurso solicitado.',
  };

  function humanizeApiMessage(m) {
    const s = String(m == null ? '' : m).trim();
    if (!s) return 'Error';
    if (API_ERROR_LABELS[s]) return API_ERROR_LABELS[s];
    if (s.includes('cancelled_quotation_cannot_be_edited')) {
      return s.replace(/cancelled_quotation_cannot_be_edited/g, API_ERROR_LABELS.cancelled_quotation_cannot_be_edited);
    }
    if (s === 'invalid_state' || s.includes('invalid_state')) {
      return API_ERROR_LABELS.invalid_state;
    }
    return s;
  }

  const showError = (m) => {
    err.textContent = humanizeApiMessage(m);
    err.classList.remove('d-none');
  };
  const clearError = () => { err.classList.add('d-none'); err.textContent = ''; };

  async function api(url, method = 'GET', body = null) {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : null,
      credentials: 'same-origin',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const code = typeof data.error === 'string' ? data.error : '';
      let msg =
        (typeof data.user_message === 'string' && data.user_message) ||
        (typeof data.detail === 'string' && data.detail) ||
        code ||
        `request_failed (${res.status})`;
      if (code === 'cancelled_quotation_cannot_be_edited') {
        msg = API_ERROR_LABELS.cancelled_quotation_cannot_be_edited;
      }
      if (code === 'invalid_state' && msg === code) {
        msg = API_ERROR_LABELS.invalid_state;
      }
      if (code && API_ERROR_LABELS[code]) {
        msg = API_ERROR_LABELS[code];
      }
      const ex = new Error(msg);
      ex.status = res.status;
      ex.code = code;
      throw ex;
    }
    return data;
  }

  /** Catálogo de impuestos para líneas. Si falla una URL, prueba la otra; siempre deja taxes como array. */
  async function loadTaxes() {
    let data;
    try {
      data = await api('/api/taxes?include_inactive=1');
    } catch (e1) {
      try {
        data = await api('/taxes?include_inactive=1');
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

  function formatTaxPreview(t) {
    if (!t) return 'Sin impuesto';
    if (computationModeTax(t) === 'fixed') return `${t.name} (${Number(t.amount_fixed || 0)} fijo/u)`;
    return `${t.name} (${Number(t.rate != null ? t.rate : t.percentage || 0)}%)`;
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
    if (!canEditContent() && quote) {
      document.getElementById('subtotalLbl').textContent = fmt(quote.total);
      document.getElementById('taxLbl').textContent = fmt(quote.tax_total);
      document.getElementById('grandLbl').textContent = fmt(quote.grand_total);
      return;
    }
    const lines = window.QuotationLinesComponent.collect(lineItems);
    let subtotal = 0; let tax = 0; let grand = 0;
    [...lineItems.querySelectorAll('tr')].forEach((tr, idx) => {
      const calc = computeLine(lines[idx] || {});
      subtotal += calc.subtotal;
      tax += calc.tax;
      grand += calc.total;
      const totalCell = tr.querySelector('.li-total');
      if (totalCell) totalCell.textContent = Number(calc.total || 0).toFixed(2);
    });
    document.getElementById('subtotalLbl').textContent = fmt(subtotal);
    document.getElementById('taxLbl').textContent = fmt(tax);
    document.getElementById('grandLbl').textContent = fmt(grand);
  }

  function setStatus(status) {
    ['stDraft', 'stSent', 'stConfirmed', 'stInvoiced', 'stPaid'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.opacity = '0.35';
    });
    if (status === 'cancelled') return;
    const map = {
      draft: 'stDraft',
      sent: 'stSent',
      confirmed: 'stConfirmed',
      invoiced: 'stInvoiced',
      paid: 'stPaid',
    };
    const id = map[status];
    if (id) {
      const el = document.getElementById(id);
      if (el) el.style.opacity = '1';
    }
  }

  async function loadQuotation() {
    clearError();
    const q = await api(`/quotations/${qid}`);
    quote = q;
    root.dataset.status = q.status;
    document.getElementById('qNumber').textContent = q.number;
    customerId.value = q.customer_id || '';
    if (customerSearch) {
      const disp = q.customer_email
        ? `${(q.customer_name || q.customer_email).trim()} (${q.customer_email})`
        : (q.customer_name || '').trim();
      customerSearch.value = disp;
      if (disp) customerSearch.dataset.lockedLabel = disp;
      else delete customerSearch.dataset.lockedLabel;
    }
    validityDate.value = q.validity_date ? q.validity_date.slice(0, 10) : '';
    const qd = document.getElementById('quoteDate');
    if (qd) qd.value = q.date ? q.date.slice(0, 10) : '';
    if (paymentTerms) paymentTerms.value = q.payment_terms || '';
    document.getElementById('subtotalLbl').textContent = fmt(q.total);
    document.getElementById('taxLbl').textContent = fmt(q.tax_total);
    document.getElementById('grandLbl').textContent = fmt(q.grand_total);
    setStatus(q.status);
    window.QuotationLinesComponent.mount(lineItems, q.lines || [], taxes, { readOnly: !canEditContentForQuote(q) });
    applyEditMode();
    recalcUiTotals();
  }

  async function saveQuotation(extra = {}, opts = {}) {
    const silent = opts.silent === true;
    const wasEditable = canEditContent();
    if (!quote) {
      showError('Cotización no cargada.');
      return;
    }
    const lines = wasEditable
      ? window.QuotationLinesComponent.collect(lineItems)
      : linesFromApiQuote(quote);
    const payload = {
      customer_id: Number(customerId.value) || null,
      validity_date: validityDate.value ? new Date(validityDate.value).toISOString() : null,
      payment_terms: paymentTerms ? String(paymentTerms.value || '').trim() : '',
      lines,
    };
    const statusHint = (quote && quote.status) || root.dataset.status || root.dataset.initialStatus || '';
    if (String(statusHint).toLowerCase() === 'cancelled' && extra.status !== 'cancelled') {
      payload.status = 'draft';
    }
    Object.assign(payload, extra);
    const updated = await api(`/quotations/${qid}`, 'PUT', payload);
    quote = updated;
    root.dataset.status = updated.status;
    window.QuotationLinesComponent.mount(lineItems, updated.lines || [], taxes, { readOnly: !canEditContentForQuote(updated) });
    applyEditMode();
    recalcUiTotals();
    if (!silent && wasEditable) showSavedToast();
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

  const btnAddLineEl = document.getElementById('btnAddLine');
  if (btnAddLineEl) {
    btnAddLineEl.addEventListener('click', (e) => {
      e.preventDefault();
      addProductLine();
    });
  }
  const menuAddNote = document.getElementById('menuAddNote');
  if (menuAddNote) {
    menuAddNote.addEventListener('click', (e) => {
      e.preventDefault();
      addNoteLine(false);
    });
  }
  const menuAddSection = document.getElementById('menuAddSection');
  if (menuAddSection) {
    menuAddSection.addEventListener('click', (e) => {
      e.preventDefault();
      addNoteLine(true);
    });
  }
  const menuOpenCatalog = document.getElementById('menuOpenCatalog');
  if (menuOpenCatalog) {
    menuOpenCatalog.addEventListener('click', (e) => {
      e.preventDefault();
      if (!canEditContent()) return;
      let tr = [...lineItems.querySelectorAll('tr:not([data-note="1"])')].pop();
      if (!tr) {
        addProductLine();
        tr = [...lineItems.querySelectorAll('tr:not([data-note="1"])')].pop();
      }
      if (tr) openServiceCatalogModal(tr);
    });
  }

  document.addEventListener('mousedown', (e) => {
    if (!e.target.closest('#quoteCustomerM2o')) closeCustomerMenu();
    if (e.target.closest('#lineItems .odoo-m2o')) return;
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
        if (e.key === 'Escape') { e.preventDefault(); closeCustomerMenu(); }
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
    document.getElementById('quoteCustomerM2o').addEventListener('click', (e) => {
      const btn = e.target.closest && e.target.closest('.cust-m2o-opt');
      if (!btn) return;
      applyCustomerPick({
        id: btn.dataset.id,
        name: btn.dataset.name,
        email: btn.dataset.email,
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
      if (e.key === 'Escape') { e.preventDefault(); closeAllServiceMenus(); }
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

  const svcFilter = document.getElementById('serviceCatalogFilter');
  const svcRows = document.getElementById('serviceCatalogRows');
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
      const modalEl = document.getElementById('serviceCatalogModal');
      if (window.bootstrap && window.bootstrap.Modal) {
        window.bootstrap.Modal.getInstance(modalEl)?.hide();
      }
    });
  }

  const btnSave = document.getElementById('btnSave');
  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      try { await saveQuotation(); } catch (e) { showError(e.message); }
    });
  }
  const btnConfirm = document.getElementById('btnConfirm');
  if (btnConfirm) {
    btnConfirm.addEventListener('click', async () => {
      try { await saveQuotation(); await api(`/quotations/${qid}/confirm`, 'POST'); await loadQuotation(); } catch (e) { showError(e.message); }
    });
  }
  const btnCreateInvoice = document.getElementById('btnCreateInvoice');
  if (btnCreateInvoice) {
    btnCreateInvoice.addEventListener('click', async () => {
      try {
        await saveQuotation();
        await api(`/quotations/${qid}/create-invoice`, 'POST');
        await loadQuotation();
      } catch (e) { showError(e.message); }
    });
  }
  const btnSend = document.getElementById('btnSend');
  if (btnSend) {
    btnSend.addEventListener('click', async () => {
      try { await saveQuotation(); await api(`/quotations/${qid}/send`, 'POST'); await loadQuotation(); } catch (e) { showError(e.message); }
    });
  }
  const btnCancel = document.getElementById('btnCancel');
  if (btnCancel) {
    btnCancel.addEventListener('click', async () => {
      try { await saveQuotation({ status: 'cancelled' }); await loadQuotation(); } catch (e) { showError(e.message); }
    });
  }
  const btnDeleteQuotation = document.getElementById('btnDeleteQuotation');
  if (btnDeleteQuotation) {
    btnDeleteQuotation.addEventListener('click', async () => {
      if (!quote) return;
      const hasInv = quote.invoice_id != null && Number(quote.invoice_id) > 0;
      const st = String(quote.status || '');
      if (hasInv) {
        showError(API_ERROR_LABELS.quotation_has_invoice);
        return;
      }
      if (['invoiced', 'paid'].includes(st)) {
        showError(API_ERROR_LABELS.quotation_cannot_delete_final);
        return;
      }
      if (
        !window.confirm(
          `¿Eliminar la cotización ${document.getElementById('qNumber').textContent || ''} de forma permanente? Esta acción no se puede deshacer.`,
        )
      ) {
        return;
      }
      try {
        const res = await fetch(`/quotations/${qid}`, {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const code = typeof data.error === 'string' ? data.error : '';
          const msg =
            (typeof data.user_message === 'string' && data.user_message) ||
            (code && API_ERROR_LABELS[code]) ||
            code ||
            `request_failed (${res.status})`;
          throw new Error(msg);
        }
        window.location.href = '/admin/sales/quotations';
      } catch (e) {
        showError(e.message || String(e));
      }
    });
  }
  const btnPreview = document.getElementById('btnPreview');
  if (btnPreview) {
    btnPreview.addEventListener('click', async () => {
    try {
      if (canEditContent()) await saveQuotation({}, { silent: true });
      const lines = getLinesForPreview();
      previewBody.innerHTML = `
        <h5 class="mb-3">Cotización ${document.getElementById('qNumber').textContent}</h5>
        <div class="small text-muted mb-3">Cliente: ${escHtml(customerSearch ? customerSearch.value : '') || `ID ${customerId.value || '-'}`} | Vencimiento: ${validityDate.value || '-'}${paymentTerms && paymentTerms.value ? ` | Términos: ${escHtml(paymentTerms.value)}` : ''}</div>
        <table class="table table-sm">
          <thead><tr><th>Descripción</th><th class="text-end">Cant.</th><th class="text-end">Precio</th><th class="text-end">Impuesto</th><th class="text-end">Importe</th></tr></thead>
          <tbody>
            ${lines.map((ln) => {
              if (ln.is_note) return `<tr><td colspan="5"><em>${ln.description || ''}</em></td></tr>`;
              const c = computeLine(ln);
              const t = lineTax(ln);
              return `<tr><td>${ln.description || ''}</td><td class="text-end">${Number(ln.quantity || 0).toFixed(2)}</td><td class="text-end">${fmt(ln.price_unit)}</td><td class="text-end">${formatTaxPreview(t)}</td><td class="text-end">${fmt(c.total)}</td></tr>`;
            }).join('')}
          </tbody>
        </table>
        <div class="text-end"><strong>Total: ${document.getElementById('grandLbl').textContent}</strong></div>`;
      if (window.bootstrap && window.bootstrap.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(previewModal).show();
      } else {
        previewModal.classList.remove('d-none');
      }
    } catch (e) { showError(e.message); }
    });
  }

  lineItems.addEventListener('keydown', (e) => {
    if (!canEditContent()) return;
    if (e.key !== 'Enter' || e.shiftKey) return;
    if (!e.target.matches('.li-qty, .li-price')) return;
    e.preventDefault();
    addProductLine();
  });

  async function bootQuotationUi() {
    try {
      await loadTaxes();
    } catch (e) {
      taxes = [];
      showError(`No se pudo cargar el catálogo de impuestos: ${e.message || e}. Puede agregar líneas e intentar de nuevo.`);
    }
    try {
      await loadQuotation();
    } catch (e) {
      showError(e.message || String(e));
    }
    recalcUiTotals();
  }
  void bootQuotationUi();
})();


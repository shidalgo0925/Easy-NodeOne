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
  const Q_BASE = String(root.dataset.salesApiBase || '/api/sales/quotations').replace(/\/$/, '');
  const WORKSHOP_API_BASE = String(root.dataset.workshopApiBase || '/api/workshop').replace(/\/$/, '');
  const err = document.getElementById('formError');
  const lineItems = document.getElementById('lineItems');
  if (!lineItems) return;
  const customerId = document.getElementById('customerId');
  const customerSearch = document.getElementById('customerSearch');
  const customerMenu = document.getElementById('customerMenu');
  const salespersonSearch = document.getElementById('salespersonSearch');
  const salespersonMenu = document.getElementById('salespersonMenu');
  const salespersonUserId = document.getElementById('salespersonUserId');
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
  const SP_DEBOUNCE_MS = 300;

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

  function showMailSentToast(emailHint) {
    const el = document.getElementById('quoteMailToast');
    if (!el) return;
    el.textContent = emailHint ? `Correo enviado a ${emailHint}.` : 'Correo enviado al cliente.';
    el.classList.remove('d-none');
    el.classList.add('show');
    clearTimeout(root._mailToastT);
    root._mailToastT = setTimeout(() => {
      el.classList.add('d-none');
      el.classList.remove('show');
    }, 3800);
  }

  function applyEditMode() {
    if (!quote) return;
    const editable = canEditContent();
    root.classList.toggle('quote-odoo-readonly', !editable);
    const banner = document.getElementById('quoteReadonlyBanner');
    if (banner) banner.classList.toggle('d-none', editable);
    const roIds = ['customerSearch', 'paymentTerms', 'quoteInternalNotes'];
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
      if (hasInv && quote.invoice_id) {
        btnViewInvoice.href = `/admin/accounting/invoices/${quote.invoice_id}`;
      }
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

  function nlToBr(s) {
    return escHtml(s).replace(/\n/g, '<br>');
  }

  function formatDateEs(iso) {
    if (!iso || String(iso).trim() === '') return '—';
    const p = String(iso).slice(0, 10).split('-');
    if (p.length === 3 && p[0].length === 4) return `${p[2]}/${p[1]}/${p[0]}`;
    return escHtml(String(iso));
  }

  /** Texto vendedor para vista previa (fallback «—») o correo (fallback vacío). */
  function getQuotationSellerDisplay(fallbackWhenMissing) {
    if (salespersonSearch && salespersonSearch.value.trim()) return salespersonSearch.value.trim();
    if (quote && (quote.salesperson_name || quote.salesperson_email)) {
      const sn = (quote.salesperson_name || '').trim();
      const se = (quote.salesperson_email || '').trim();
      const line = sn && se ? `${sn} (${se})` : sn || se;
      return line || fallbackWhenMissing;
    }
    return fallbackWhenMissing;
  }

  function getOrganizationFiscalParts() {
    const orgName = (quote && quote.organization_name) || (root.dataset.quoteOrgName || '').trim() || '';
    const legal = (quote && quote.organization_legal_name) || '';
    const taxId = (quote && quote.organization_tax_id) || '';
    const regime = (quote && quote.organization_tax_regime) || '';
    const address = (quote && quote.organization_fiscal_address) || '';
    const city = (quote && quote.organization_fiscal_city) || '';
    const state = (quote && quote.organization_fiscal_state) || '';
    const country = (quote && quote.organization_fiscal_country) || '';
    const phone = (quote && quote.organization_fiscal_phone) || '';
    const email = (quote && quote.organization_fiscal_email) || '';
    return {
      displayName: (legal || orgName || '—').trim() || '—',
      taxId: String(taxId || '').trim(),
      regime: String(regime || '').trim(),
      address: String(address || '').trim(),
      location: [city, state, country].map((x) => String(x || '').trim()).filter(Boolean).join(', '),
      contact: [phone, email].map((x) => String(x || '').trim()).filter(Boolean).join(' · '),
    };
  }

  function buildQuotePreviewDocumentHtml(lines) {
    const brand = (root.dataset.quoteBrand || '').trim() || '—';
    const orgFiscal = getOrganizationFiscalParts();
    const logoUrl = (root.dataset.quoteLogoUrl || '').trim();
    const qNum = (document.getElementById('qNumber') && document.getElementById('qNumber').textContent.trim()) || '—';
    const custBlock = (customerSearch && customerSearch.value.trim()) || '—';
    const qDateVal = document.getElementById('quoteDate') ? document.getElementById('quoteDate').value : '';
    const seller = getQuotationSellerDisplay('—');
    const payTerms = (paymentTerms && paymentTerms.value.trim()) || 'Pago inmediato';
    const validityVal = document.getElementById('validityDate') ? document.getElementById('validityDate').value : '';
    const subtotalT = (document.getElementById('subtotalLbl') && document.getElementById('subtotalLbl').textContent) || 'B/. 0.00';
    const taxT = (document.getElementById('taxLbl') && document.getElementById('taxLbl').textContent) || 'B/. 0.00';
    const grandT = (document.getElementById('grandLbl') && document.getElementById('grandLbl').textContent) || 'B/. 0.00';

    const bodyRows = lines
      .map((ln) => {
        if (ln.is_note && ln.is_section) {
          return `<tr class="quote-doc-section"><td class="qd-col-desc" colspan="5">${nlToBr((ln.description || '').trim() || '—')}</td></tr>`;
        }
        if (ln.is_note) {
          return `<tr class="quote-doc-note"><td class="qd-col-desc" colspan="5">${nlToBr(ln.description || '')}</td></tr>`;
        }
        const c = computeLine(ln);
        const t = lineTax(ln);
        const taxLabel = formatTaxPreview(t);
        const taxShow = taxLabel === 'Sin impuesto' ? '—' : escHtml(taxLabel);
        const desc = (ln.description || '').trim() || '—';
        return `<tr>
          <td class="qd-col-desc">${nlToBr(desc)}</td>
          <td class="qd-col-num">${Number(ln.quantity || 0).toFixed(2)} Unidades</td>
          <td class="qd-col-num">${Number(ln.price_unit || 0).toFixed(2)}</td>
          <td class="qd-col-num">${taxShow}</td>
          <td class="qd-col-money">${fmt(c.total)}</td>
        </tr>`;
      })
      .join('');

    const brandCaps = escHtml(brand.toUpperCase());
    const logoBlock = logoUrl
      ? `<img class="quote-doc-preview__logo" src="${escAttr(logoUrl)}" alt=""><div class="quote-doc-preview__brand-name">${brandCaps}</div>`
      : `<div class="quote-doc-preview__brand-name">${brandCaps}</div>`;

    const validityNote = validityVal
      ? `<div>Vencimiento oferta: <strong>${formatDateEs(validityVal)}</strong></div>`
      : '';

    return `<div class="quote-doc-preview">
      <div class="quote-doc-preview__header">
        <div class="quote-doc-preview__wave" aria-hidden="true"></div>
        <div class="quote-doc-preview__header-grid">
          <div class="quote-doc-preview__brand">${logoBlock}</div>
          <div class="quote-doc-preview__company">
            <div class="quote-doc-preview__company-name">${escHtml(orgFiscal.displayName || brand)}</div>
            ${orgFiscal.taxId ? `<div class="small text-muted">RUC/NIT: ${escHtml(orgFiscal.taxId)}</div>` : ''}
            ${orgFiscal.regime ? `<div class="small text-muted">Régimen: ${escHtml(orgFiscal.regime)}</div>` : ''}
            ${orgFiscal.address ? `<div class="small text-muted">${escHtml(orgFiscal.address)}</div>` : ''}
            ${orgFiscal.location ? `<div class="small text-muted">${escHtml(orgFiscal.location)}</div>` : ''}
            ${orgFiscal.contact ? `<div class="small text-muted">${escHtml(orgFiscal.contact)}</div>` : ''}
          </div>
        </div>
      </div>
      <div class="quote-doc-preview__client-row">
        <div class="quote-doc-preview__client">${nlToBr(custBlock)}</div>
        <div class="quote-doc-preview__order-num">
          <span>Número de orden</span>
          ${escHtml(qNum)}
        </div>
      </div>
      <div class="quote-doc-preview__meta-box">
        <div><strong>Fecha de la orden</strong><br>${formatDateEs(qDateVal)}</div>
        <div><strong>Vendedor</strong><br>${escHtml(seller)}</div>
      </div>
      <div class="quote-doc-table-wrap">
        <table class="quote-doc-table">
          <thead>
            <tr>
              <th class="qd-col-desc">Descripción</th>
              <th class="qd-col-num">Cantidad</th>
              <th class="qd-col-num">Precio unitario</th>
              <th class="qd-col-num">Impuestos</th>
              <th class="qd-col-money text-end">Importe</th>
            </tr>
          </thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>
      <div class="quote-doc-totals-wrap">
        <table class="quote-doc-totals">
          <tr><td>Subtotal</td><td>${escHtml(subtotalT)}</td></tr>
          <tr><td>Impuestos</td><td>${escHtml(taxT)}</td></tr>
          <tr class="quote-doc-totals-grand"><td>Total</td><td>${escHtml(grandT)}</td></tr>
        </table>
      </div>
      <div class="quote-doc-terms">
        ${validityNote}
        <div>Términos de pago: ${escHtml(payTerms)}</div>
      </div>
      <div class="quote-doc-footer">
        <div>${escHtml(brand)}</div>
        <div class="quote-doc-footer__page">Página 1 / 1</div>
      </div>
    </div>`;
  }

  const WO_ST_PREV = {
    draft: 'Borrador',
    inspected: 'Inspeccionado',
    quoted: 'Cotizado',
    approved: 'Aprobado',
    in_progress: 'En proceso',
    qc: 'Control calidad',
    done: 'Terminado',
    delivered: 'Entregado',
    cancelled: 'Cancelada',
  };
  const WO_COND_PREV = { ok: 'OK', leve: 'Leve', medio: 'Medio', severo: 'Severo' };
  const WO_DMG_PREV = {
    scratch: 'Rayón',
    swirl: 'Swirl',
    dent: 'Golpe / abolladura',
    stain: 'Mancha',
    chip: 'Descascarado',
  };
  const WO_SEV_PREV = { low: 'baja', medium: 'media', high: 'alta' };

  function _woSafeImgUrl(url) {
    const raw = String(url || '').trim();
    if (!raw) return '';
    const path = raw.split('?')[0];
    return escAttr(path.startsWith('http') ? path : path.startsWith('/') ? path : `/${path}`);
  }

  function buildQuoteWorkshopPreviewSection(bundle) {
    const o = bundle.order || {};
    const zl = bundle.zone_labels || {};
    const inv = bundle.inspection || {};
    const chkItems = (bundle.checklist && bundle.checklist.items) || [];
    const code = escHtml(o.code || '—');
    const stLab = escHtml(WO_ST_PREV[o.status] || o.status || '—');
    const entryIso = o.entry_date ? String(o.entry_date) : '';

    const veh = o.vehicle || {};
    const vehLines = [];
    if (veh.plate) vehLines.push(`<strong>Placa:</strong> ${escHtml(veh.plate)}`);
    const brandModel = [veh.brand, veh.model].filter(Boolean).join(' ').trim();
    if (brandModel) vehLines.push(escHtml(brandModel));
    if (veh.year != null && veh.year !== '') vehLines.push(`<strong>Año:</strong> ${escHtml(String(veh.year))}`);
    if (veh.color) vehLines.push(`<strong>Color:</strong> ${escHtml(veh.color)}`);
    if (veh.mileage != null && Number(veh.mileage) > 0) vehLines.push(`<strong>Km:</strong> ${escHtml(String(veh.mileage))}`);
    if (veh.vin) vehLines.push(`<strong>VIN:</strong> ${escHtml(veh.vin)}`);
    const vehBlock = vehLines.length ? vehLines.join('<br>') : '<span class="text-muted">—</span>';

    let notesHtml = '';
    if ((o.notes || '').trim()) notesHtml += `<p class="mb-1"><strong>Notas orden:</strong> ${nlToBr(o.notes)}</p>`;
    if ((o.qc_notes || '').trim()) notesHtml += `<p class="mb-0"><strong>Notas control de calidad:</strong> ${nlToBr(o.qc_notes)}</p>`;

    const wlines = Array.isArray(o.lines) ? o.lines : [];
    const lineRows = wlines
      .map((ln) => {
        const desc = (ln.description || '').trim() || '—';
        return `<tr>
          <td class="qd-col-desc">${nlToBr(desc)}</td>
          <td class="qd-col-num">${Number(ln.quantity || 0).toFixed(2)}</td>
          <td class="qd-col-num">${Number(ln.price_unit || 0).toFixed(2)}</td>
          <td class="qd-col-money">${fmt(ln.total)}</td>
        </tr>`;
      })
      .join('');
    const linesBlock =
      wlines.length > 0
        ? `<div class="quote-doc-table-wrap mt-3">
        <table class="quote-doc-table">
          <thead><tr><th class="qd-col-desc">Descripción</th><th class="qd-col-num">Cant.</th><th class="qd-col-num">P. unit.</th><th class="qd-col-money">Total</th></tr></thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <p class="small text-muted mt-2 mb-0">Total estimado orden: <strong>${fmt(o.total_estimated)}</strong></p>`
        : '';

    const chkRows = chkItems
      .map((c) => {
        const ck = (c.condition || 'ok').toLowerCase();
        const condRaw =
          WO_COND_PREV[ck] != null ? WO_COND_PREV[ck] : String(c.condition || '').trim() || '—';
        const nt = (c.notes || '').trim();
        return `<tr><td>${escHtml(c.item || '')}</td><td>${escHtml(condRaw)}</td><td>${nt ? nlToBr(nt) : '—'}</td></tr>`;
      })
      .join('');
    const chkBlock =
      chkRows.length > 0
        ? `<h3 style="font-size:1rem;margin:1.25em 0 0.5em;color:var(--qd-blue)">Checklist de recepción</h3>
        <div class="quote-doc-table-wrap"><table class="quote-doc-table">
          <thead><tr><th>Ítem</th><th>Condición</th><th>Notas</th></tr></thead>
          <tbody>${chkRows}</tbody>
        </table></div>`
        : '';

    const pts = Array.isArray(inv.points) ? inv.points : [];
    const inspRows = pts
      .map((p) => {
        const zlab = escHtml(zl[p.zone_code] || p.zone_code || '');
        const dt = escHtml(WO_DMG_PREV[(p.damage_type || '').toLowerCase()] || p.damage_type || '—');
        const sv = escHtml(WO_SEV_PREV[(p.severity || 'low').toLowerCase()] || p.severity || '—');
        const nt = (p.notes || '').trim();
        return `<tr><td>${zlab}</td><td>${dt}</td><td>${sv}</td><td>${nt ? nlToBr(nt) : '—'}</td></tr>`;
      })
      .join('');
    let inspBlock = '';
    if (inspRows.length) {
      inspBlock = `<h3 style="font-size:1rem;margin:1.25em 0 0.5em;color:var(--qd-blue)">Inspección (body map)</h3>
        <div class="quote-doc-table-wrap"><table class="quote-doc-table">
          <thead><tr><th>Zona</th><th>Tipo</th><th>Severidad</th><th>Notas</th></tr></thead>
          <tbody>${inspRows}</tbody>
        </table></div>`;
    }
    if ((inv.notes || '').trim()) {
      inspBlock += `<p class="small mt-2 mb-0"><strong>Notas inspección:</strong> ${nlToBr(inv.notes)}</p>`;
    }

    const phKind = { entrada: 'Entrada', proceso: 'Proceso', salida: 'Salida' };
    const orderPhotos = Array.isArray(o.photos) ? o.photos : [];
    const opCells = orderPhotos
      .map((p) => {
        const su = _woSafeImgUrl(p.url);
        if (!su) return '';
        const k = escHtml(phKind[p.kind] || p.kind || 'Foto');
        return `<div class="wo-doc-photo-cell" style="break-inside:avoid"><div class="border rounded overflow-hidden bg-white h-100">
          <img src="${su}" alt="" style="width:100%;max-height:220px;object-fit:cover;display:block"/>
          <div class="small text-muted px-2 py-1">${k}</div>
        </div></div>`;
      })
      .filter(Boolean)
      .join('');
    const opBlock = opCells
      ? `<h3 style="font-size:1rem;margin:1.25em 0 0.5em;color:var(--qd-blue)">Fotos de la orden</h3><div class="wo-doc-photo-grid">${opCells}</div>`
      : '';

    const ipCells = [];
    pts.forEach((p) => {
      const zlab = escHtml(zl[p.zone_code] || p.zone_code || 'Zona');
      (p.photos || []).forEach((ph, idx) => {
        const su = _woSafeImgUrl(ph.url);
        if (!su) return;
        ipCells.push(`<div class="wo-doc-photo-cell" style="break-inside:avoid"><div class="border rounded overflow-hidden bg-white h-100">
          <img src="${su}" alt="" style="width:100%;max-height:220px;object-fit:cover;display:block"/>
          <div class="small text-muted px-2 py-1">${zlab} · ${idx + 1}</div>
        </div></div>`);
      });
    });
    const ipBlock = ipCells.length
      ? `<h3 style="font-size:1rem;margin:1.25em 0 0.5em;color:var(--qd-blue)">Fotos de inspección</h3><div class="wo-doc-photo-grid">${ipCells.join('')}</div>`
      : '';

    return `<div class="quote-wo-addon mt-4 pt-4" style="border-top:2px solid #1a3dcc">
      <h2 style="font-size:1.15rem;color:#1a3dcc;margin-bottom:0.75rem">Orden de trabajo ${code}</h2>
      <p class="mb-2"><strong>Estado:</strong> ${stLab} · <strong>Ingreso:</strong> ${formatDateEs(entryIso)}</p>
      <p class="mb-2"><strong>Vehículo</strong><br>${vehBlock}</p>
      ${notesHtml}
      ${linesBlock}
      ${chkBlock}
      ${inspBlock}
      ${opBlock}
      ${ipBlock}
    </div>`;
  }

  function syncQuotePreviewWorkshopWrap() {
    const wrap = document.getElementById('quotePreviewWorkshopWrap');
    const chk = document.getElementById('quotePreviewAttachWorkshop');
    if (!wrap || !chk) return;
    const hasWo = quote && quote.workshop_order_code;
    wrap.classList.toggle('d-none', !hasWo);
    chk.checked = !!hasWo;
  }

  async function refreshQuotePreviewInner() {
    if (!previewBody) return;
    const lines = getLinesForPreview();
    const baseHtml = buildQuotePreviewDocumentHtml(lines);
    const wrap = document.getElementById('quotePreviewWorkshopWrap');
    const chk = document.getElementById('quotePreviewAttachWorkshop');
    let extra = '';
    const wantWo =
      wrap &&
      !wrap.classList.contains('d-none') &&
      chk &&
      chk.checked &&
      quote &&
      quote.workshop_order_code;
    if (wantWo) {
      try {
        const bundle = await fetchJsonAbsolute(`${WORKSHOP_API_BASE}/by-quotation/${qid}`);
        extra = buildQuoteWorkshopPreviewSection(bundle);
      } catch (e) {
        extra = `<div class="alert alert-warning mt-4 mb-0" role="alert">${escHtml(e.message || 'No se pudo cargar la orden de trabajo.')}</div>`;
      }
    }
    previewBody.innerHTML = `<div class="p-3 p-md-4">${baseHtml}${extra}</div>`;
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
        const meta = r.email && String(r.email) !== String(r.name || '')
          ? `<span class="odoo-m2o-item-meta">${escHtml(r.email)}</span>`
          : r.code
            ? `<span class="odoo-m2o-item-meta">${escHtml(r.code)}</span>`
            : '';
        return `<button type="button" class="odoo-m2o-item sp-m2o-opt" data-id="${r.id}" data-name="${escAttr(r.name || '')}" data-email="${escAttr(r.email || '')}" data-code="${escAttr(r.code || '')}"><span class="odoo-m2o-item-title">${title}</span>${meta}</button>`;
      })
      .join('');
    const empty =
      '<div class="px-3 py-2 small text-muted">Sin vendedores. En <strong>Usuarios</strong> marque «Es vendedor» en los miembros que cotizan.</div>';
    return `${rows.length ? body : empty}<div class="odoo-m2o-hint">Miembros de la organización con «Es vendedor»</div>`;
  }

  async function fetchSalespersons(q, limit) {
    return api(`/salespersons/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  }

  async function renderSalespersonDropdown(q, limit) {
    if (!salespersonMenu || !salespersonSearch) return;
    root._spFetch = (root._spFetch || 0) + 1;
    const fid = root._spFetch;
    salespersonMenu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
    salespersonMenu.classList.add('show');
    salespersonSearch.setAttribute('aria-expanded', 'true');
    try {
      const list = await fetchSalespersons(q, limit);
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
    if (!canEditContent() && quote) {
      try {
        await saveQuotation({}, { silent: true });
      } catch (e) {
        showError(e.message);
      }
    }
  }

  function clearSalespersonPick() {
    if (salespersonUserId) salespersonUserId.value = '';
    if (salespersonSearch) {
      salespersonSearch.value = '';
      delete salespersonSearch.dataset.lockedLabel;
    }
  }

  async function maybeApplyDefaultSalesperson() {
    if (!canEditContent() || !salespersonUserId || (salespersonUserId.value || '').trim() !== '') return;
    try {
      const d = await api('/salespersons/default');
      if (d && d.id) {
        await applySalespersonPick(d);
        if (quote) {
          try {
            await saveQuotation({}, { silent: true });
          } catch (_) {
            /* sin persistir si falla */
          }
        }
      }
    } catch (_) {
      /* sin vendedor por defecto */
    }
  }

  function setCustomerHighlight(menu, index) {
    const opts = [...menu.querySelectorAll('.quote-cust-kbd-opt')];
    opts.forEach((el, i) => el.classList.toggle('odoo-m2o-item-active', i === index));
    if (opts[index]) opts[index].scrollIntoView({ block: 'nearest' });
    return opts;
  }

  /** Mismo desplegable que Taller: búsqueda + Crear «…» + Crear y editar + Buscar más. */
  function buildCustomerDropdownHtml(users, qRaw) {
    const q = (qRaw || '').trim();
    let head = '';
    if (q) {
      const qDisp = escHtml(q);
      const qAttr = escAttr(q);
      head =
        `<button type="button" class="odoo-m2o-item quote-cust-kbd-opt quote-cust-quick-create border-0 w-100 text-start" data-q="${qAttr}">Crear "${qDisp}"</button>` +
        `<button type="button" class="odoo-m2o-item quote-cust-kbd-opt quote-cust-open-edit border-0 w-100 text-start">Crear y editar…</button>`;
    }
    const body = (users || [])
      .map((u) => {
        const title = escHtml(u.name || u.email || '');
        const em =
          u.email && String(u.email) !== String(u.name || '')
            ? `<span class="odoo-m2o-item-meta">${escHtml(u.email)}</span>`
            : '';
        return `<button type="button" class="odoo-m2o-item quote-cust-kbd-opt quote-cust-m2o-opt" data-id="${u.id}" data-name="${escAttr(u.name || '')}" data-email="${escAttr(u.email || '')}"><span class="odoo-m2o-item-title">${title}</span>${em}</button>`;
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

  async function fetchCustomers(q, limit) {
    return fetchJsonAbsolute(
      `${WORKSHOP_API_BASE}/customers/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    );
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
      customerMenu.innerHTML = buildCustomerDropdownHtml(list, q);
      const kbd = [...customerMenu.querySelectorAll('.quote-cust-kbd-opt')];
      root._custM2oIndex = kbd.length ? 0 : -1;
      if (kbd.length) setCustomerHighlight(customerMenu, root._custM2oIndex);
    } catch (e) {
      if (fid !== root._custFetch) return;
      customerMenu.innerHTML =
        `<div class="px-3 py-2 small text-danger">${escAttr(e.message)}</div>` +
        '<div class="odoo-m2o-hint small px-3 pb-2">Si el módulo Taller está desactivado, no hay API de clientes.</div>';
    }
  }

  function applyCustomerPick(u) {
    customerId.value = String(u.id);
    const disp = u.email && u.name ? `${u.name} (${u.email})` : (u.name || u.email || '');
    customerSearch.value = disp;
    customerSearch.dataset.lockedLabel = disp;
    closeCustomerMenu();
  }

  async function quickCreateCustomerFromTypedLabel(raw) {
    const t = String(raw || '').trim();
    if (!t) return;
    clearError();
    try {
      let res;
      if (t.includes('@')) {
        res = await fetchJsonAbsolute(`${WORKSHOP_API_BASE}/customers`, 'POST', { email: t.toLowerCase() });
      } else {
        res = await fetchJsonAbsolute(`${WORKSHOP_API_BASE}/customers`, 'POST', { quick_create_name: t });
      }
      applyCustomerPick({ id: res.id, name: res.name, email: res.email });
      closeCustomerMenu();
    } catch (e) {
      showError(e.message);
    }
  }

  function openQuoteNewCustomerModal(prefillOverride) {
    closeCustomerMenu();
    const raw =
      prefillOverride != null && String(prefillOverride).trim() !== ''
        ? String(prefillOverride).trim()
        : (customerSearch && customerSearch.value ? customerSearch.value.trim() : '');
    const em = document.getElementById('quoteNewCustEmail');
    const fn = document.getElementById('quoteNewCustFirst');
    const ln = document.getElementById('quoteNewCustLast');
    const ph = document.getElementById('quoteNewCustPhone');
    const er = document.getElementById('quoteNewCustErr');
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
    const modalEl = document.getElementById('quoteNewCustomerModal');
    if (window.bootstrap && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  async function submitQuoteNewCustomer() {
    const em = document.getElementById('quoteNewCustEmail');
    const fn = document.getElementById('quoteNewCustFirst');
    const ln = document.getElementById('quoteNewCustLast');
    const ph = document.getElementById('quoteNewCustPhone');
    const er = document.getElementById('quoteNewCustErr');
    const payload = {
      email: (em && em.value.trim()) || '',
      first_name: (fn && fn.value.trim()) || '',
      last_name: (ln && ln.value.trim()) || '',
      phone: (ph && ph.value.trim()) || '',
    };
    try {
      const res = await fetchJsonAbsolute(`${WORKSHOP_API_BASE}/customers`, 'POST', payload);
      applyCustomerPick({ id: res.id, name: res.name, email: res.email });
      const modalEl = document.getElementById('quoteNewCustomerModal');
      if (window.bootstrap && modalEl) window.bootstrap.Modal.getInstance(modalEl)?.hide();
      if (er) {
        er.textContent = '';
        er.classList.add('d-none');
      }
    } catch (e) {
      if (er) {
        er.textContent = e.message || 'No se pudo crear el cliente';
        er.classList.remove('d-none');
      }
    }
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
    return api(`/products/search?q=${encodeURIComponent(q)}&limit=${limit}`);
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
    invalid_salesperson: 'Identificador de vendedor no válido.',
    salesperson_not_found: 'El vendedor no existe en esta organización.',
    salesperson_inactive: 'El vendedor está inactivo.',
    salesperson_not_flagged: 'El usuario no está habilitado como vendedor (actívelo en Usuarios).',
    customer_email_missing:
      'El contacto cliente no tiene correo electrónico. Edite el cliente y asigne un email antes de enviar.',
    recipients_required: 'Indique al menos un correo válido en «Para».',
    send_failed: 'No se pudo enviar el correo (SMTP o cola). Revise la configuración de email de la organización.',
    forbidden: 'No tiene permiso para esta acción.',
    not_found: 'No se encontró el recurso solicitado.',
    unauthorized: 'Sesión caducada o no autenticado. Recargue la página e inicie sesión.',
    organization_context_lost:
      'Sesión o contexto de organización inválido. Recargue la página e inicie sesión de nuevo.',
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

  /**
   * fetch JSON desde una ruta absoluta del sitio (desde /). No usar con rutas del API de cotizaciones.
   */
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
        'El servidor devolvió HTML en lugar de JSON (suele ser sesión caducada o URL mal enrutada). Recargue e inicie sesión.',
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

  /** Ruta relativa al API de cotizaciones (Q_BASE), p. ej. `/${qid}` o `/customers/search?...`. */
  async function api(urlPath, method = 'GET', body = null) {
    const suffix = urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
    return fetchJsonAbsolute(Q_BASE + suffix, method, body);
  }

  /** Catálogo de impuestos: vive en /api/taxes o /taxes, no bajo /api/sales/quotations. */
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
    const q = await api(`/${qid}`);
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
    if (salespersonUserId) {
      const sid = q.salesperson_user_id;
      salespersonUserId.value =
        sid != null && sid !== '' && !Number.isNaN(Number(sid)) ? String(Number(sid)) : '';
    }
    if (salespersonSearch) {
      let sd = '';
      if (q.salesperson_name || q.salesperson_email) {
        const sn = (q.salesperson_name || '').trim();
        const se = (q.salesperson_email || '').trim();
        sd = sn && se ? `${sn} (${se})` : sn || se;
      }
      salespersonSearch.value = sd;
      if (sd) salespersonSearch.dataset.lockedLabel = sd;
      else delete salespersonSearch.dataset.lockedLabel;
    }
    validityDate.value = q.validity_date ? q.validity_date.slice(0, 10) : '';
    const qd = document.getElementById('quoteDate');
    if (qd) qd.value = q.date ? q.date.slice(0, 10) : '';
    if (paymentTerms) paymentTerms.value = q.payment_terms || '';
    const orgFiscalEl = document.getElementById('quoteOrgFiscalText');
    if (orgFiscalEl) {
      const orgFiscal = getOrganizationFiscalParts();
      const parts = [
        orgFiscal.displayName !== '—' ? orgFiscal.displayName : '',
        orgFiscal.taxId ? `RUC/NIT: ${orgFiscal.taxId}` : '',
        orgFiscal.regime ? `Régimen: ${orgFiscal.regime}` : '',
        orgFiscal.address || '',
        orgFiscal.location || '',
        orgFiscal.contact || '',
      ].filter(Boolean);
      orgFiscalEl.textContent = parts.join(' | ') || 'Sin datos fiscales configurados.';
    }
    document.getElementById('subtotalLbl').textContent = fmt(q.total);
    document.getElementById('taxLbl').textContent = fmt(q.tax_total);
    document.getElementById('grandLbl').textContent = fmt(q.grand_total);
    setStatus(q.status);
    window.QuotationLinesComponent.mount(lineItems, q.lines || [], taxes, { readOnly: !canEditContentForQuote(q) });
    applyEditMode();
    recalcUiTotals();
    maybeApplyDefaultSalesperson();
    syncQuotePreviewWorkshopWrap();
  }

  async function saveQuotation(extra = {}, opts = {}) {
    const silent = opts.silent === true;
    const wasEditable = canEditContent();
    if (!quote) {
      showError('Cotización no cargada.');
      return;
    }
    const spRaw = salespersonUserId ? Number(salespersonUserId.value) : null;
    const spPayload = spRaw && !Number.isNaN(spRaw) && spRaw > 0 ? spRaw : null;
    if (!wasEditable) {
      const curSp =
        quote.salesperson_user_id != null && quote.salesperson_user_id !== ''
          ? Number(quote.salesperson_user_id)
          : null;
      const curNorm = curSp && !Number.isNaN(curSp) && curSp > 0 ? curSp : null;
      const spNorm = spPayload;
      if (curNorm === spNorm && Object.keys(extra).length === 0) {
        if (!silent) return;
      }
      const patch = { salesperson_user_id: spNorm };
      Object.assign(patch, extra);
      const updated = await api(`/${qid}`, 'PUT', patch);
      quote = updated;
      root.dataset.status = updated.status;
      window.QuotationLinesComponent.mount(lineItems, updated.lines || [], taxes, {
        readOnly: !canEditContentForQuote(updated),
      });
      applyEditMode();
      recalcUiTotals();
      if (!silent) showSavedToast();
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
      salesperson_user_id: spPayload,
    };
    const statusHint = (quote && quote.status) || root.dataset.status || root.dataset.initialStatus || '';
    if (String(statusHint).toLowerCase() === 'cancelled' && extra.status !== 'cancelled') {
      payload.status = 'draft';
    }
    Object.assign(payload, extra);
    const updated = await api(`/${qid}`, 'PUT', payload);
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
    if (!e.target.closest('#quoteSalespersonM2o')) closeSalespersonMenu();
    if (e.target.closest('#lineItems .odoo-m2o')) return;
    closeAllServiceMenus();
  });

  if (customerSearch && customerMenu) {
    customerSearch.addEventListener('focusin', () => {
      if (!canEditContent()) return;
      renderCustomerDropdown((customerSearch.value || '').trim(), 15);
    });
    customerSearch.addEventListener('click', () => {
      if (!canEditContent()) return;
      renderCustomerDropdown((customerSearch.value || '').trim(), 15);
    });
    customerSearch.addEventListener('input', () => {
      if (!canEditContent()) return;
      if (customerSearch.dataset.lockedLabel && customerSearch.value !== customerSearch.dataset.lockedLabel) {
        customerId.value = '';
        delete customerSearch.dataset.lockedLabel;
      }
      const q = (customerSearch.value || '').trim();
      clearTimeout(root._custDeb);
      root._custDeb = setTimeout(() => renderCustomerDropdown(q, 15), CUST_DEBOUNCE_MS);
    });
    customerSearch.addEventListener('keydown', (e) => {
      if (!canEditContent()) return;
      const menu = customerMenu;
      if (!menu.classList.contains('show')) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          renderCustomerDropdown((customerSearch.value || '').trim(), 15);
        }
        return;
      }
      const opts = [...menu.querySelectorAll('.quote-cust-kbd-opt')];
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
    document.getElementById('quoteCustomerM2o')?.addEventListener('click', (e) => {
      const qc = e.target.closest && e.target.closest('.quote-cust-quick-create');
      if (qc) {
        e.preventDefault();
        quickCreateCustomerFromTypedLabel(qc.getAttribute('data-q') || '');
        return;
      }
      const ed = e.target.closest && e.target.closest('.quote-cust-open-edit');
      if (ed) {
        e.preventDefault();
        openQuoteNewCustomerModal();
        return;
      }
      const btn = e.target.closest && e.target.closest('.quote-cust-m2o-opt');
      if (btn && btn.dataset.id) {
        e.preventDefault();
        applyCustomerPick({
          id: btn.dataset.id,
          name: btn.dataset.name,
          email: btn.dataset.email,
        });
      }
    });
    document.querySelector('#quoteCustomerM2o .quote-cust-toggle')?.addEventListener('click', (e) => {
      e.preventDefault();
      customerSearch.focus();
      renderCustomerDropdown((customerSearch.value || '').trim(), 15);
    });
  }

  document.getElementById('btnQuoteNewCustSave')?.addEventListener('click', (e) => {
    e.preventDefault();
    submitQuoteNewCustomer();
  });

  const spM2oRoot = document.getElementById('quoteSalespersonM2o');
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
      try { await saveQuotation(); await api(`/${qid}/confirm`, 'POST'); await loadQuotation(); } catch (e) { showError(e.message); }
    });
  }
  const btnCreateInvoice = document.getElementById('btnCreateInvoice');
  if (btnCreateInvoice) {
    btnCreateInvoice.addEventListener('click', async () => {
      try {
        await saveQuotation();
        const invRes = await api(`/${qid}/create-invoice`, 'POST');
        const newId = invRes && (invRes.invoice_id != null ? Number(invRes.invoice_id) : 0);
        if (newId > 0) {
          window.location.href = `/admin/accounting/invoices/${newId}`;
          return;
        }
        await loadQuotation();
      } catch (e) { showError(e.message); }
    });
  }
  function openQuoteMailModal() {
    const el = document.getElementById('quoteMailModal');
    if (!el) {
      showError(
        'No se abrió el envío de correo. Recargue la página forzando caché (Ctrl+F5 o Cmd+Shift+R).',
      );
      return;
    }
    if (window.bootstrap && window.bootstrap.Modal) {
      try {
        window.bootstrap.Modal.getOrCreateInstance(el).show();
        return;
      } catch (e) {
        console.warn('quoteMailModal', e);
      }
    }
    showError(
      'No se pudo mostrar el diálogo (Bootstrap no cargó). Revise conexión, bloqueadores de script y recargue.',
    );
  }

  function fillQuoteMailModal() {
    const toEl = document.getElementById('quoteMailTo');
    const subEl = document.getElementById('quoteMailSubject');
    const bodyEl = document.getElementById('quoteMailBody');
    const pdfNameEl = document.getElementById('quoteMailPdfName');
    const attChk = document.getElementById('quoteMailAttachPdf');
    const woWrap = document.getElementById('quoteMailWorkshopWrap');
    const woChk = document.getElementById('quoteMailAttachWorkshop');
    if (!toEl || !subEl || !bodyEl) return;
    const em = quote && quote.customer_email ? String(quote.customer_email).trim() : '';
    toEl.value = em;
    const org = (root.dataset.quoteOrgName || root.dataset.quoteBrand || '').trim();
    const num =
      (document.getElementById('qNumber') && document.getElementById('qNumber').textContent.trim()) || '—';
    subEl.value = org ? `${org} — Cotización (Ref ${num})` : `Cotización (Ref ${num})`;
    const nombre = quote && quote.customer_name ? String(quote.customer_name).trim() : 'Cliente';
    const grandEl = document.getElementById('grandLbl');
    const total = grandEl ? String(grandEl.textContent || '').trim() : 'B/. 0.00';
    const seller = getQuotationSellerDisplay('');
    const sig = seller ? `— ${seller}` : '—';
    bodyEl.value = [
      `Hola ${nombre},`,
      '',
      `Le enviamos la cotización ${num} por un importe de ${total}.`,
      '',
      'No dude en ponerse en contacto con nosotros si tiene alguna pregunta.',
      '',
      sig,
    ].join('\n');
    if (pdfNameEl) {
      const safeNum = String(num).replace(/[^\w.\-]+/g, '_');
      pdfNameEl.textContent = `Cotizacion-${safeNum}.pdf`;
    }
    if (attChk) attChk.checked = true;
    const hasWo = quote && quote.workshop_order_code;
    if (woWrap && woChk) {
      woWrap.classList.toggle('d-none', !hasWo);
      woChk.checked = !!hasWo;
      woChk.disabled = !hasWo;
    }
  }

  const btnSend = document.getElementById('btnSend');
  if (btnSend) {
    btnSend.addEventListener('click', async () => {
      try {
        clearError();
        await saveQuotation();
        if (!quote) {
          showError('Cotización no cargada.');
          return;
        }
        const em = quote.customer_email ? String(quote.customer_email).trim() : '';
        if (!em) {
          showError(API_ERROR_LABELS.customer_email_missing);
          return;
        }
        fillQuoteMailModal();
        openQuoteMailModal();
      } catch (e) {
        showError(e.message);
      }
    });
  }

  const btnQuoteMailSubmit = document.getElementById('btnQuoteMailSubmit');
  if (btnQuoteMailSubmit) {
    btnQuoteMailSubmit.addEventListener('click', async () => {
      const toEl = document.getElementById('quoteMailTo');
      const subEl = document.getElementById('quoteMailSubject');
      const bodyEl = document.getElementById('quoteMailBody');
      const attChk = document.getElementById('quoteMailAttachPdf');
      const woWrap = document.getElementById('quoteMailWorkshopWrap');
      const woChk = document.getElementById('quoteMailAttachWorkshop');
      if (!toEl || !subEl || !bodyEl) return;
      btnQuoteMailSubmit.disabled = true;
      try {
        let attachWo = false;
        if (woWrap && !woWrap.classList.contains('d-none') && woChk && !woChk.disabled) {
          attachWo = !!woChk.checked;
        }
        const payload = {
          to: String(toEl.value || '').trim(),
          subject: String(subEl.value || '').trim(),
          body_text: String(bodyEl.value || ''),
          attach_pdf: !!(attChk && attChk.checked),
          attach_workshop_order: attachWo,
        };
        await api(`/${qid}/send`, 'POST', payload);
        const mailModalEl = document.getElementById('quoteMailModal');
        if (mailModalEl && window.bootstrap && window.bootstrap.Modal) {
          try {
            window.bootstrap.Modal.getOrCreateInstance(mailModalEl).hide();
          } catch (_) {
            /* ignore */
          }
        }
        await loadQuotation();
        const firstTo = String(payload.to || '')
          .split(/[,;]+/)
          .map((s) => s.trim())
          .find(Boolean) || '';
        showMailSentToast(firstTo);
      } catch (e) {
        showError(e.message);
      } finally {
        btnQuoteMailSubmit.disabled = false;
      }
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
        // POST /id/delete: mismo efecto que DELETE; algunos proxies/firewalls bloquean DELETE.
        await api(`/${qid}/delete`, 'POST', {});
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
        syncQuotePreviewWorkshopWrap();
        await refreshQuotePreviewInner();
        if (window.bootstrap && window.bootstrap.Modal) {
          window.bootstrap.Modal.getOrCreateInstance(previewModal).show();
        } else if (previewModal) {
          previewModal.classList.remove('d-none');
        }
      } catch (e) {
        showError(e.message);
      }
    });
  }

  document.getElementById('quotePreviewAttachWorkshop')?.addEventListener('change', () => {
    void refreshQuotePreviewInner();
  });

  document.getElementById('btnQuotePreviewPrint')?.addEventListener('click', () => {
    window.print();
  });

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


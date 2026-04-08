/**
 * Ficha orden de taller: recepción, líneas, body map, cotización.
 */
(function () {
  const root = document.getElementById('workshopOrderPage');
  if (!root) return;

  const orderId = Number(root.dataset.orderId || 0) || 0;
  const errEl = document.getElementById('woErr');
  const fmt = (n) => `B/. ${Number(n || 0).toFixed(2)}`;

  let order = null;
  let zones = [];
  let taxes = [];
  let inspection = { inspection_id: null, points: [] };
  let zoneLabels = {};

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
    const opt = { method: method || 'GET', credentials: 'same-origin', headers: {} };
    if (body != null) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const r = await fetch(url, opt);
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || d.error || `HTTP ${r.status}`);
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
    zones = await api('/api/workshop/zones');
    zoneLabels = {};
    (zones || []).forEach((z) => {
      zoneLabels[z.code] = z.name;
    });
  }

  function taxOptionsHtml() {
    return (
      '<option value="">Sin impuesto</option>' +
      taxes
        .map((t) => `<option value="${t.id}">${(t.name || '').replace(/</g, '')} (${Number(t.rate != null ? t.rate : t.percentage || 0)}%)</option>`)
        .join('')
    );
  }

  function lineRow(ln, idx) {
    const tid = ln && ln.tax_id != null ? String(ln.tax_id) : '';
    return `<tr data-idx="${idx}">
      <td><input type="hidden" class="wol-pid" value="${ln.product_id || ''}"/><input class="form-control form-control-sm wol-psearch" type="text" placeholder="Buscar servicio…" value=""/></td>
      <td><input class="form-control form-control-sm wol-desc" value="${String(ln.description || '').replace(/"/g, '&quot;')}"/></td>
      <td><input class="form-control form-control-sm wol-qty" type="number" step="0.01" value="${Number(ln.quantity || 1)}"/></td>
      <td><input class="form-control form-control-sm wol-price" type="number" step="0.01" value="${Number(ln.price_unit || 0).toFixed(2)}"/></td>
      <td><select class="form-select form-select-sm wol-tax">${taxOptionsHtml()}</select></td>
      <td class="text-end small wol-line-total">${fmt(ln.total)}</td>
      <td><button type="button" class="btn btn-sm btn-outline-danger wol-del">×</button></td>
    </tr>`;
  }

  function collectLines() {
    const rows = [...document.querySelectorAll('#wolLines tr')];
    return rows.map((tr) => ({
      product_id: tr.querySelector('.wol-pid').value ? Number(tr.querySelector('.wol-pid').value) : null,
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

  async function bindProductSearch(tr) {
    const inp = tr.querySelector('.wol-psearch');
    const hid = tr.querySelector('.wol-pid');
    const desc = tr.querySelector('.wol-desc');
    const price = tr.querySelector('.wol-price');
    const taxSel = tr.querySelector('.wol-tax');
    if (!inp || inp.dataset.bound) return;
    inp.dataset.bound = '1';
    let tmo;
    inp.addEventListener('input', () => {
      clearTimeout(tmo);
      const q = inp.value.trim();
      if (q.length < 2) return;
      tmo = setTimeout(async () => {
        try {
          const prods = await api(`/quotations/products/search?q=${encodeURIComponent(q)}&limit=15`);
          if (!Array.isArray(prods) || !prods.length) return;
          const p = prods[0];
          hid.value = p.id;
          inp.value = p.name || '';
          desc.value = (p.description || p.name || '').trim();
          price.value = Number(p.price_unit || 0).toFixed(2);
          if (p.default_tax_id && taxSel) taxSel.value = String(p.default_tax_id);
          recalcLineTotals();
        } catch (_) {
          /* Ventas deshabilitado o sin resultados */
        }
      }, 300);
    });
  }

  function renderLines(lines) {
    const tb = document.getElementById('wolLines');
    if (!tb) return;
    const arr = Array.isArray(lines) && lines.length ? lines : [{ description: '', quantity: 1, price_unit: 0, tax_id: null }];
    tb.innerHTML = arr.map((ln, i) => lineRow(ln, i)).join('');
    tb.querySelectorAll('tr').forEach((tr) => {
      const tid = tr.querySelector('.wol-tax');
      const ln = arr[Number(tr.dataset.idx) || 0];
      if (tid && ln && ln.tax_id) tid.value = String(ln.tax_id);
      bindProductSearch(tr);
      tr.querySelector('.wol-del')?.addEventListener('click', () => {
        tr.remove();
        if (!document.querySelector('#wolLines tr')) renderLines([{ description: '', quantity: 1, price_unit: 0 }]);
        recalcLineTotals();
      });
      tr.querySelectorAll('.wol-qty,.wol-price,.wol-tax').forEach((el) => el.addEventListener('input', recalcLineTotals));
    });
    recalcLineTotals();
  }

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
      .map(
        (p) =>
          `<li class="small mb-1">${zoneLabels[p.zone_code] || p.zone_code}: ${p.damage_type} (${p.severity}) <button type="button" class="btn btn-link btn-sm p-0 wo-del-point" data-id="${p.id}">Eliminar</button></li>`,
      )
      .join('');
    ul.querySelectorAll('.wo-del-point').forEach((btn) =>
      btn.addEventListener('click', async () => {
        try {
          await api(`/api/workshop/inspection-points/${btn.dataset.id}`, 'DELETE');
          await loadInspection();
        } catch (e) {
          showErr(e.message);
        }
      }),
    );
  }

  function openZoneModal(zoneCode) {
    if (!order || !order.id) {
      alert('Guarde la orden primero para usar el mapa de inspección.');
      return;
    }
    const modalEl = document.getElementById('woDamageModal');
    document.getElementById('woModalZone').value = zoneCode;
    document.getElementById('woModalZoneLabel').textContent = zoneLabels[zoneCode] || zoneCode;
    document.getElementById('woModalNotes').value = '';
    document.getElementById('woModalPhoto').value = '';
    if (window.bootstrap && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  async function saveDamageFromModal() {
    const zone = document.getElementById('woModalZone').value;
    const damage = document.getElementById('woModalDamage').value;
    const sev = document.getElementById('woModalSeverity').value;
    const notes = document.getElementById('woModalNotes').value.trim();
    const fileInp = document.getElementById('woModalPhoto');
    try {
      const res = await api(`/api/workshop/orders/${order.id}/inspection/points`, 'POST', {
        zone_code: zone,
        damage_type: damage,
        severity: sev,
        notes,
        photos: [],
      });
      if (res.inspection_id) inspection.inspection_id = res.inspection_id;
      const pid = res.id;
      if (fileInp && fileInp.files && fileInp.files[0] && pid) {
        const fd = new FormData();
        fd.append('file', fileInp.files[0]);
        const r = await fetch(`/api/workshop/inspection-points/${pid}/photos`, { method: 'POST', body: fd, credentials: 'same-origin' });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.detail || d.error || r.status);
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

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
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
    document.getElementById('custId').value = o.customer_id || '';
    const cs = document.getElementById('custSearch');
    if (cs) {
      if (o.customer_name || o.customer_email) {
        const nm = (o.customer_name || '').trim();
        const em = (o.customer_email || '').trim();
        cs.value = em && nm ? `${nm} (${em})` : nm || em || '';
      } else {
        cs.value = '';
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
    const cust = Number(document.getElementById('custId').value || 0);
    if (cust < 1) {
      showErr('Seleccione o indique cliente (ID).');
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

  document.getElementById('btnWoAddLine')?.addEventListener('click', () => {
    const tb = document.getElementById('wolLines');
    const tr = document.createElement('tbody');
    tr.innerHTML = lineRow({}, tb.querySelectorAll('tr').length);
    const row = tr.firstElementChild;
    tb.appendChild(row);
    bindProductSearch(row);
    row.querySelector('.wol-del')?.addEventListener('click', () => {
      row.remove();
      recalcLineTotals();
    });
    row.querySelectorAll('.wol-qty,.wol-price,.wol-tax').forEach((el) => el.addEventListener('input', recalcLineTotals));
  });

  /* Cliente: ID + búsqueda opcional */
  let custTmo;
  document.getElementById('custSearch')?.addEventListener('input', function () {
    const menu = document.getElementById('custMenu');
    const q = this.value.trim();
    clearTimeout(custTmo);
    if (q.length < 2) {
      if (menu) {
        menu.innerHTML = '';
        menu.classList.add('d-none');
      }
      return;
    }
    custTmo = setTimeout(async () => {
      if (!menu) return;
      try {
        const users = await api(`/quotations/customers/search?q=${encodeURIComponent(q)}&limit=15`);
        if (!Array.isArray(users)) return;
        if (!users.length) {
          menu.classList.add('d-none');
          menu.innerHTML = '';
          return;
        }
        menu.innerHTML = users
          .map(
            (u) =>
              `<button type="button" class="dropdown-item wo-cust-pick text-start" data-id="${u.id}">${(u.name || u.email || '').replace(/</g, '')} <small class="text-muted">${(u.email || '').replace(/</g, '')}</small></button>`,
          )
          .join('');
        menu.classList.remove('d-none');
        menu.querySelectorAll('.wo-cust-pick').forEach((b) =>
          b.addEventListener('click', () => {
            document.getElementById('custId').value = b.dataset.id;
            document.getElementById('custSearch').value = b.textContent.trim();
            menu.innerHTML = '';
            menu.classList.add('d-none');
          }),
        );
      } catch (_) {
        menu.innerHTML =
          '<div class="px-2 py-1 text-danger small">Active Ventas para buscar por nombre o escriba el ID de cliente.</div>';
        menu.classList.remove('d-none');
      }
    }, 300);
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

window.QuotationLinesComponent = (function () {
  function fmtNum(n, decimals) {
    if (window.EN1Format) return window.EN1Format.number(n, decimals);
    return Number(n || 0).toFixed(decimals != null ? decimals : 2);
  }
  function fmtQty(n) {
    return window.EN1Format ? window.EN1Format.qty(n) : fmtNum(n);
  }

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function taxOptionLabel(t) {
    const comp = (t.computation || 'percent') === 'fixed' ? 'fijo' : '%';
    const v =
      (t.computation || 'percent') === 'fixed'
        ? Number(t.amount_fixed || 0).toFixed(2)
        : Number(t.rate != null ? t.rate : t.percentage || 0);
    const inc = (t.price_included || t.type === 'included') ? 'inc.' : 'exc.';
    return `${esc(t.name)} (${comp} ${v} ${inc})`;
  }

  function taxOptions(taxes, selected) {
    const opts = [`<option value="">Sin impuesto</option>`];
    const list = Array.isArray(taxes) ? taxes : [];
    list.forEach((t) => {
      if (!t || t.id == null) return;
      const isSel = Number(selected || 0) === Number(t.id) ? 'selected' : '';
      opts.push(`<option value="${t.id}" ${isSel}>${taxOptionLabel(t)}</option>`);
    });
    return opts.join('');
  }

  function taxLabelReadonly(line, taxes) {
    const tid = line.tax_id;
    if (tid == null || tid === '') return 'Sin impuesto';
    const t = (Array.isArray(taxes) ? taxes : []).find((x) => Number(x.id) === Number(tid));
    return t ? taxOptionLabel(t) : `Impuesto #${esc(String(tid))}`;
  }

  function rowTemplateReadonly(line, idx, taxes) {
    const isNote = Boolean(line.is_note);
    if (isNote) {
      const section = Boolean(line.is_section);
      const content = esc(line.description || '');
      if (section) {
        return `<tr data-idx="${idx}" data-note="1" data-section="1">
          <td colspan="6" class="fw-semibold pt-3 pb-1 border-0">${content}</td>
        </tr>`;
      }
      return `<tr data-idx="${idx}" data-note="1">
        <td colspan="6" class="text-muted fst-italic py-2">${content}</td>
      </tr>`;
    }
    const qty = Number(line.quantity || 0);
    const pu = Number(line.price_unit || 0);
    const total = Number(line.total != null ? line.total : qty * pu);
    return `<tr data-idx="${idx}">
      <td class="p-2"><div class="small">${esc(line.description || '')}</div></td>
      <td class="p-2 text-end align-middle">${fmtQty(qty)}</td>
      <td class="p-2 text-end align-middle">${fmtNum(pu)}</td>
      <td class="p-2 align-middle small">${taxLabelReadonly(line, taxes)}</td>
      <td class="p-2 li-total text-end fw-semibold align-middle">${fmtNum(total)}</td>
      <td class="p-1"></td>
    </tr>`;
  }

  function rowTemplate(line, idx, taxes) {
    const isNote = Boolean(line.is_note);
    if (isNote) {
      const section = Boolean(line.is_section);
      const ph = section ? 'Nombre de la sección…' : 'Nota o comentario en el documento…';
      return `<tr data-idx="${idx}" data-note="1"${section ? ' data-section="1"' : ''}>
        <td colspan="5"><input class="qcell-input qcell-note li-note" placeholder="${esc(ph)}" value="${esc(line.description || '')}"></td>
        <td class="text-center align-middle"><button type="button" class="btn btn-sm btn-link text-danger p-0 li-del" title="Eliminar">🗑</button></td>
      </tr>`;
    }
    const prodNameAttr = esc(line.product_name || '');
    return `<tr data-idx="${idx}">
      <td class="p-2 quote-line-desc-cell">
        <input class="li-product" type="hidden" value="${line.product_id || ''}" data-name="${prodNameAttr}">
        <div class="odoo-m2o quote-line-desc-m2o">
          <div class="d-flex align-items-stretch odoo-m2o-input-wrap">
            <textarea class="qcell-input qcell-textarea li-desc li-product-search flex-grow-1 border-0 shadow-none rounded-0 py-2" rows="1" placeholder="Buscar por descripción…" autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list">${esc(line.description || '')}</textarea>
            <button type="button" class="btn btn-sm btn-link odoo-m2o-toggle li-product-toggle px-2" tabindex="-1" title="Catálogo">🔍</button>
          </div>
          <div class="odoo-m2o-dropdown li-product-menu" role="listbox"></div>
        </div>
      </td>
      <td class="p-2" style="width:5.5rem"><input class="qcell-input li-qty text-end" type="number" step="0.01" min="0" value="${line.quantity || 1}"></td>
      <td class="p-2" style="width:6.5rem"><input class="qcell-input li-price text-end" type="number" step="0.01" min="0" value="${line.price_unit || 0}"></td>
      <td class="p-2" style="width:8rem"><select class="qcell-select li-tax">${taxOptions(taxes, line.tax_id)}</select></td>
      <td class="p-2 li-total text-end fw-semibold align-middle">${fmtNum(line.total || 0)}</td>
      <td class="text-center align-middle p-1"><button type="button" class="btn btn-sm btn-link text-danger p-0 li-del" title="Eliminar">🗑</button></td>
    </tr>`;
  }

  function mount(container, lines, taxes, opts) {
    const readOnly = opts && opts.readOnly;
    container.innerHTML = '';
    (lines || []).forEach((l, i) => {
      const tpl = readOnly ? rowTemplateReadonly(l, i, taxes) : rowTemplate(l, i, taxes);
      container.insertAdjacentHTML('beforeend', tpl);
    });
  }

  function collect(container) {
    const rows = [...container.querySelectorAll('tr')];
    return rows.map((tr) => {
      const isNote = tr.dataset.note === '1';
      if (isNote) {
        const noteEl = tr.querySelector('.li-note');
        return {
          is_note: true,
          is_section: tr.dataset.section === '1',
          product_id: null,
          description: noteEl ? noteEl.value || '' : '',
          quantity: 0,
          price_unit: 0,
          tax_id: null,
        };
      }
      const productEl = tr.querySelector('.li-product');
      const descEl = tr.querySelector('.li-desc');
      return {
        product_id: Number(productEl && productEl.value) || null,
        product_name: productEl ? String(productEl.dataset.name || '').trim() : '',
        description: descEl ? descEl.value || '' : '',
        quantity: Number(tr.querySelector('.li-qty').value) || 0,
        price_unit: Number(tr.querySelector('.li-price').value) || 0,
        tax_id: Number(tr.querySelector('.li-tax').value) || null,
        is_note: false,
      };
    });
  }

  return { mount, collect };
})();

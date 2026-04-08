window.QuotationLinesComponent = (function () {
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
          <td colspan="7" class="fw-semibold pt-3 pb-1 border-0">${content}</td>
        </tr>`;
      }
      return `<tr data-idx="${idx}" data-note="1">
        <td colspan="7" class="text-muted fst-italic py-2">${content}</td>
      </tr>`;
    }
    const qty = Number(line.quantity || 0);
    const pu = Number(line.price_unit || 0);
    const total = Number(line.total != null ? line.total : qty * pu).toFixed(2);
    const prodLabel = line.product_name
      ? esc(String(line.product_name))
      : line.product_id
        ? `<span class="text-muted small">Servicio #${esc(String(line.product_id))}</span>`
        : '—';
    return `<tr data-idx="${idx}">
      <td class="p-2 align-top">${prodLabel}</td>
      <td class="p-2"><div class="small">${esc(line.description || '')}</div></td>
      <td class="p-2 text-end align-middle">${qty.toFixed(2)}</td>
      <td class="p-2 text-end align-middle">${pu.toFixed(2)}</td>
      <td class="p-2 align-middle small">${taxLabelReadonly(line, taxes)}</td>
      <td class="p-2 li-total text-end fw-semibold align-middle">${total}</td>
      <td class="p-1"></td>
    </tr>`;
  }

  function rowTemplate(line, idx, taxes) {
    const isNote = Boolean(line.is_note);
    if (isNote) {
      const section = Boolean(line.is_section);
      const ph = section ? 'Nombre de la sección…' : 'Nota o comentario en el documento…';
      return `<tr data-idx="${idx}" data-note="1"${section ? ' data-section="1"' : ''}>
        <td colspan="6"><input class="qcell-input qcell-note li-note" placeholder="${esc(ph)}" value="${esc(line.description || '')}"></td>
        <td class="text-center align-middle"><button type="button" class="btn btn-sm btn-link text-danger p-0 li-del" title="Eliminar">🗑</button></td>
      </tr>`;
    }
    return `<tr data-idx="${idx}">
      <td class="align-top p-2">
        <div class="odoo-m2o">
          <div class="d-flex align-items-stretch odoo-m2o-input-wrap">
            <input class="qcell-input li-product-search flex-grow-1 border-0 shadow-none rounded-0 py-2" placeholder="Buscar producto o servicio…" value="${esc(line.product_name || '')}" autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list">
            <button type="button" class="btn btn-sm btn-link odoo-m2o-toggle li-product-toggle px-2" tabindex="-1" title="Catálogo">🔍</button>
          </div>
          <input class="li-product" type="hidden" value="${line.product_id || ''}">
          <div class="odoo-m2o-dropdown li-product-menu" role="listbox"></div>
        </div>
      </td>
      <td class="p-2"><textarea class="qcell-input qcell-textarea li-desc" rows="1">${esc(line.description || '')}</textarea></td>
      <td class="p-2" style="width:5.5rem"><input class="qcell-input li-qty text-end" type="number" step="0.01" min="0" value="${line.quantity || 1}"></td>
      <td class="p-2" style="width:6.5rem"><input class="qcell-input li-price text-end" type="number" step="0.01" min="0" value="${line.price_unit || 0}"></td>
      <td class="p-2" style="width:8rem"><select class="qcell-select li-tax">${taxOptions(taxes, line.tax_id)}</select></td>
      <td class="p-2 li-total text-end fw-semibold align-middle">${Number(line.total || 0).toFixed(2)}</td>
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
      return {
        product_id: Number(tr.querySelector('.li-product').value) || null,
        description: tr.querySelector('.li-desc').value || '',
        quantity: Number(tr.querySelector('.li-qty').value) || 0,
        price_unit: Number(tr.querySelector('.li-price').value) || 0,
        tax_id: Number(tr.querySelector('.li-tax').value) || null,
        is_note: false,
      };
    });
  }

  return { mount, collect };
})();

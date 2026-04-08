(function () {
  const root = document.getElementById('taxesAdminPage');
  if (!root) return;

  const err = document.getElementById('taxesPageError');
  const tbody = document.getElementById('taxesAdminTable');
  let taxes = [];
  /** Base efectiva tras primer GET (fallback si /api/taxes no existe en el servidor). */
  let taxApiBase = '/api/taxes';

  function escAttr(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const showError = (m) => {
    err.textContent = String(m || 'Error');
    err.classList.remove('d-none');
  };
  const clearError = () => {
    err.classList.add('d-none');
    err.textContent = '';
  };

  function humanError(e) {
    const m = String((e && e.message) || e || '');
    if (/forbidden/i.test(m)) {
      return 'Sin permiso para impuestos. Inicie sesión como administrador o habilite el módulo Ventas para esta organización.';
    }
    return m || 'Error de red o servidor';
  }

  async function api(url, method = 'GET', body = null) {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : null,
      credentials: 'same-origin',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const ex = new Error(data.error || data.detail || `HTTP ${res.status}`);
      ex.status = res.status;
      throw ex;
    }
    return data;
  }

  async function loadTaxes() {
    clearError();
    const inc = document.getElementById('taxIncludeInactive')?.checked;
    const q = `?include_inactive=${inc ? '1' : '0'}`;
    const tryBase = async (base) => {
      taxes = await api(`${base}${q}`, 'GET');
    };
    try {
      await tryBase(taxApiBase);
    } catch (e) {
      if (taxApiBase === '/api/taxes' && (e.status === 404 || e.status === 405)) {
        taxApiBase = '/taxes';
        try {
          await tryBase(taxApiBase);
        } catch (e2) {
          showError(humanError(e2));
          return;
        }
      } else {
        showError(humanError(e));
        return;
      }
    }
    render();
  }

  function rowValue(t) {
    return (t.computation || 'percent') === 'fixed' ? Number(t.amount_fixed || 0) : Number(t.rate != null ? t.rate : t.percentage || 0);
  }

  function render() {
    tbody.innerHTML = taxes
      .map(
        (t) => `
      <tr data-id="${t.id}">
        <td><input class="form-control form-control-sm tx-name" data-id="${t.id}" value="${escAttr(t.name)}"></td>
        <td>
          <select class="form-select form-select-sm tx-comp" data-id="${t.id}">
            <option value="percent" ${(t.computation || 'percent') === 'percent' ? 'selected' : ''}>Porcentaje</option>
            <option value="fixed" ${t.computation === 'fixed' ? 'selected' : ''}>Fijo</option>
          </select>
        </td>
        <td><input class="form-control form-control-sm tx-val" data-id="${t.id}" type="number" step="0.01" value="${rowValue(t)}"></td>
        <td class="text-center">
          <input class="form-check-input tx-inc" type="checkbox" data-id="${t.id}" ${t.price_included ? 'checked' : ''}>
        </td>
        <td>${t.active ? '<span class="badge bg-success">Sí</span>' : '<span class="badge bg-secondary">No</span>'}</td>
        <td>
          <button type="button" class="btn btn-sm btn-outline-primary tx-save" data-id="${t.id}">Guardar</button>
          ${t.active ? `<button type="button" class="btn btn-sm btn-outline-danger tx-del" data-id="${t.id}">Desactivar</button>` : `<button type="button" class="btn btn-sm btn-outline-success tx-reactivate" data-id="${t.id}">Reactivar</button>`}
        </td>
      </tr>`,
      )
      .join('');
  }

  document.getElementById('taxIncludeInactive').addEventListener('change', () => {
    loadTaxes().catch((e) => showError(humanError(e)));
  });

  document.getElementById('taxCreateBtn').addEventListener('click', async () => {
    try {
      const name = document.getElementById('taxName').value.trim();
      const computation = document.getElementById('taxComputation').value;
      const val = Number(document.getElementById('taxValue').value || 0);
      const price_included = document.getElementById('taxPriceIncluded').checked;
      if (!name) throw new Error('Indique un nombre');
      const body = {
        name,
        computation,
        price_included,
        rate: computation === 'percent' ? val : 0,
        amount_fixed: computation === 'fixed' ? val : 0,
      };
      await api(taxApiBase, 'POST', body);
      document.getElementById('taxName').value = '';
      document.getElementById('taxValue').value = '7';
      document.getElementById('taxComputation').value = 'percent';
      document.getElementById('taxPriceIncluded').checked = false;
      await loadTaxes();
    } catch (e) {
      showError(humanError(e));
    }
  });

  tbody.addEventListener('click', async (e) => {
    const id = Number(e.target.dataset.id || 0);
    if (!id) return;
    try {
      if (e.target.classList.contains('tx-save')) {
        const tr = e.target.closest('tr');
        const name = tr.querySelector('.tx-name').value;
        const computation = tr.querySelector('.tx-comp').value;
        const val = Number(tr.querySelector('.tx-val').value || 0);
        const price_included = tr.querySelector('.tx-inc').checked;
        await api(`${taxApiBase}/${id}`, 'PUT', {
          name,
          computation,
          price_included,
          rate: computation === 'percent' ? val : 0,
          amount_fixed: computation === 'fixed' ? val : 0,
        });
        await loadTaxes();
      }
      if (e.target.classList.contains('tx-del')) {
        await api(`${taxApiBase}/${id}`, 'DELETE');
        await loadTaxes();
      }
      if (e.target.classList.contains('tx-reactivate')) {
        await api(`${taxApiBase}/${id}`, 'PUT', { active: true });
        await loadTaxes();
      }
    } catch (ex) {
      showError(humanError(ex));
    }
  });

  loadTaxes().catch((e) => showError(humanError(e)));
})();

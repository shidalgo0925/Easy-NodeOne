(function () {
  const root = document.getElementById('odooQuotationList');
  if (!root) return;
  const tb = document.getElementById('tbodyQuotations');
  const qTotal = document.getElementById('qTotalFooter');
  const err = document.getElementById('salesError');
  const search = document.getElementById('quotationSearch');

  let rowsCache = [];
  const fmt = (n) => `B/. ${Number(n || 0).toFixed(2)}`;
  const statusBadge = (s) => {
    if (s === 'sent') return '<span class="badge bg-primary">Enviada</span>';
    if (s === 'confirmed') return '<span class="badge bg-success">Confirmada</span>';
    if (s === 'invoiced') return '<span class="badge bg-info">Facturada</span>';
    if (s === 'paid') return '<span class="badge bg-dark">Pagada</span>';
    if (s === 'cancelled') return '<span class="badge bg-danger">Cancelada</span>';
    return '<span class="badge bg-secondary">Borrador</span>';
  };

  function showError(m) { err.textContent = String(m || 'Error'); err.classList.remove('d-none'); }
  function clearError() { err.classList.add('d-none'); err.textContent = ''; }
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  const Q_BASE = String(root.dataset.salesApiBase || '/api/sales/quotations').replace(/\/$/, '');

  /** rel: '' lista, o ruta con / inicial (p. ej. '' para GET/POST raíz). */
  async function api(rel, method = 'GET', body = null) {
    const suffix = rel === '' || rel.startsWith('/') ? rel : `/${rel}`;
    const headers = { Accept: 'application/json' };
    if (body != null) headers['Content-Type'] = 'application/json';
    const init = { method, credentials: 'same-origin', headers };
    if (body != null) init.body = JSON.stringify(body);
    const res = await fetch(Q_BASE + suffix, init);
    const text = await res.text().catch(() => '');
    const t = text.trim();
    if (t.startsWith('<')) {
      throw new Error(
        'El servidor devolvió HTML en lugar de JSON (suele ser sesión caducada o URL mal enrutada). Recargue e inicie sesión.',
      );
    }
    let data;
    try {
      data = t ? JSON.parse(t) : method === 'GET' && suffix === '' ? [] : {};
    } catch {
      throw new Error(`HTTP ${res.status}: la respuesta no es JSON válido.`);
    }
    if (!res.ok) {
      const code = data && data.error;
      let msg =
        (data && (data.user_message || data.detail || data.message || data.error)) || `HTTP ${res.status}`;
      if (code === 'quotations_list_failed' && !(data && data.detail)) {
        msg =
          'Error interno al listar cotizaciones. Compruebe que el despliegue incluye los últimos cambios y revise los logs del servidor.';
      }
      throw new Error(msg);
    }
    if (method === 'GET' && suffix === '' && !Array.isArray(data)) {
      throw new Error('Formato de lista inesperado');
    }
    return data;
  }

  function render(rows) {
    tb.innerHTML = '';
    let sum = 0;
    rows.forEach((r) => {
      sum += Number(r.grand_total || 0);
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input type="checkbox"></td>
        <td><a href="/admin/sales/quotations/${r.id}" class="fw-semibold text-decoration-none">${r.number}</a></td>
        <td>${(r.date || '').slice(0, 19).replace('T', ' ')}</td>
        <td>${r.customer_id || ''}</td>
        <td>${r.salesperson_name ? escHtml(r.salesperson_name) : '<span class="text-muted">—</span>'}</td>
        <td><i class="far fa-clock"></i></td>
        <td class="text-end">${fmt(r.grand_total)}</td>
        <td>${statusBadge(r.status)}</td>`;
      tb.appendChild(tr);
    });
    qTotal.textContent = fmt(sum);
  }

  async function load() {
    clearError();
    rowsCache = await api('');
    if (!Array.isArray(rowsCache)) rowsCache = [];
    render(rowsCache);
  }

  document.getElementById('btnNewQuotation').addEventListener('click', async () => {
    try {
      const created = await api('', 'POST', {
        customer_id: 1,
        crm_lead_id: null,
        lines: [{ description: 'Nueva línea', quantity: 1, price_unit: 0, tax_id: null }],
      });
      window.location.href = `/admin/sales/quotations/${created.id}`;
    } catch (e) {
      showError(e.message);
    }
  });

  search.addEventListener('input', () => {
    const q = (search.value || '').toLowerCase().trim();
    if (!q) return render(rowsCache);
    render(
      rowsCache.filter((r) =>
        `${r.number} ${r.customer_id} ${r.status} ${r.salesperson_name || ''} ${r.salesperson_email || ''}`
          .toLowerCase()
          .includes(q),
      ),
    );
  });

  load().catch((e) => showError(e.message));
})();


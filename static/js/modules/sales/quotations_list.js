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

  async function api(url, method = 'GET', body = null) {
    const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : null });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || 'request_failed');
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
        <td><i class="fas fa-user-circle me-1 text-muted"></i> Administrador</td>
        <td><i class="far fa-clock"></i></td>
        <td class="text-end">${fmt(r.grand_total)}</td>
        <td>${statusBadge(r.status)}</td>`;
      tb.appendChild(tr);
    });
    qTotal.textContent = fmt(sum);
  }

  async function load() {
    clearError();
    rowsCache = await api('/quotations');
    render(rowsCache);
  }

  document.getElementById('btnNewQuotation').addEventListener('click', async () => {
    try {
      const created = await api('/quotations', 'POST', {
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
    render(rowsCache.filter((r) => `${r.number} ${r.customer_id} ${r.status}`.toLowerCase().includes(q)));
  });

  load().catch((e) => showError(e.message));
})();


/**
 * Listado admin de órdenes de taller (filtro por estado).
 */
(function () {
  const tbody = document.getElementById('woListBody');
  const err = document.getElementById('woListErr');
  const filterEl = document.getElementById('woFilterStatus');
  if (!tbody) return;

  const STATUS = {
    draft: 'Borrador',
    inspected: 'Inspeccionado',
    quoted: 'Cotizado',
    approved: 'Aprobado',
    in_progress: 'En proceso',
    qc: 'Control calidad',
    done: 'Terminado',
    delivered: 'Entregado',
    cancelled: 'Cancelado',
  };

  function showErr(m) {
    if (!err) return;
    err.textContent = m;
    err.classList.remove('d-none');
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function api(url) {
    const r = await fetch(url, { credentials: 'same-origin' });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || d.detail || r.status);
    return d;
  }

  function loadTable() {
    const st = filterEl && filterEl.value ? '?status=' + encodeURIComponent(filterEl.value) : '';
    api('/api/workshop/orders' + st)
      .then((rows) => {
        err.classList.add('d-none');
        if (!Array.isArray(rows) || !rows.length) {
          tbody.innerHTML = '<tr><td colspan="9" class="text-muted small p-3">Sin órdenes</td></tr>';
          return;
        }
        tbody.innerHTML = rows
          .map((o) => {
            const v = o.vehicle || {};
            const plate = esc([v.plate, v.brand, v.model].filter(Boolean).join(' · ') || 'ID ' + o.vehicle_id);
            const cname = esc(o.customer_name || '');
            const cid = o.customer_id ? '<span class="text-muted small">#' + o.customer_id + '</span>' : '';
            const cust = cname || cid ? '<div class="small">' + cname + '</div>' + cid : '—';
            const nPhotos = Number(o.photos_count || 0);
            const ph = nPhotos > 0 ? '<span class="badge bg-light text-dark border">' + nPhotos + '</span>' : '—';
            const q = o.quotation_id
              ? '<a href="/admin/sales/quotations/' +
                o.quotation_id +
                '">Q #' +
                esc(String(o.quotation_id)) +
                '</a>'
              : '—';
            const inv = o.invoice_id ? '<span class="text-muted">#' + esc(String(o.invoice_id)) + '</span>' : '—';
            return (
              '<tr style="cursor:pointer" data-href="/admin/workshop/orders/' +
              o.id +
              '"><td class="fw-semibold">' +
              esc(o.code) +
              '</td><td><span class="badge text-bg-secondary">' +
              (STATUS[o.status] || esc(o.status)) +
              '</span></td><td>' +
              cust +
              '</td><td>' +
              plate +
              '</td><td class="small">' +
              (o.entry_date || '').slice(0, 10) +
              '</td><td class="text-center">' +
              ph +
              '</td><td>B/. ' +
              (o.total_estimated || 0).toFixed(2) +
              '</td><td>' +
              q +
              '</td><td>' +
              inv +
              '</td></tr>'
            );
          })
          .join('');
        tbody.querySelectorAll('tr[data-href]').forEach((tr) =>
          tr.addEventListener('click', () => {
            location.href = tr.dataset.href;
          }),
        );
      })
      .catch((e) => {
        showErr(e.message || String(e));
        tbody.innerHTML = '';
      });
  }

  const params = new URLSearchParams(window.location.search);
  const urlStatus = params.get('status');
  if (filterEl && urlStatus) {
    const has = [...filterEl.options].some((o) => o.value === urlStatus);
    if (has) filterEl.value = urlStatus;
  }
  if (filterEl) {
    filterEl.addEventListener('change', () => {
      const u = new URL(window.location.href);
      if (filterEl.value) u.searchParams.set('status', filterEl.value);
      else u.searchParams.delete('status');
      const qs = u.searchParams.toString();
      history.replaceState({}, '', u.pathname + (qs ? '?' + qs : ''));
      loadTable();
    });
  }
  loadTable();
})();

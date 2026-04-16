/**
 * Monitor taller: tarjetas con SLA, KPIs y panel de alertas.
 */
(function () {
  const grid = document.getElementById('woCardGrid');
  const err = document.getElementById('woListErr');
  const filterEl = document.getElementById('woFilterStatus');
  const kpiStrip = document.getElementById('woKpiStrip');
  const alertsBody = document.getElementById('woAlertsBody');
  const heatmapHint = document.getElementById('woHeatmapHint');
  if (!grid) return;

  const STATUS = {
    draft: 'Recepción',
    inspected: 'Diagnóstico',
    quoted: 'Cotización',
    approved: 'Aprobación',
    in_progress: 'En proceso',
    qc: 'Control calidad',
    done: 'Terminado',
    delivered: 'Entrega',
    cancelled: 'Cancelado',
  };

  const SLA_LABEL = { green: 'En tiempo', yellow: 'En riesgo', red: 'Retrasado', gray: '—' };

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

  async function api(url, opts) {
    const r = await fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', ...(opts && opts.headers) },
      ...opts,
    });
    const text = await r.text().catch(() => '');
    const t = text.trim();
    if (t.startsWith('<')) {
      throw new Error('Sesión caducada o respuesta HTML. Recargue la página.');
    }
    let d;
    if (!t) d = {};
    else {
      try {
        d = JSON.parse(text);
      } catch {
        throw new Error(`Respuesta no JSON (HTTP ${r.status})`);
      }
    }
    if (!r.ok) {
      const msg =
        (d && (d.user_message || d.detail || d.error)) || `HTTP ${r.status}`;
      throw new Error(msg);
    }
    return d;
  }

  function fmtMin(n) {
    if (n == null || Number.isNaN(n)) return '—';
    const v = Math.round(Number(n));
    if (v >= 60 && v % 60 === 0) return `${v / 60} h`;
    if (v >= 60) return `${Math.floor(v / 60)} h ${v % 60} min`;
    return `${v} min`;
  }

  function slaRank(state) {
    const rank = { red: 0, yellow: 1, green: 2, gray: 3 };
    return rank[state] != null ? rank[state] : 4;
  }

  function renderKpis(monitor) {
    if (!kpiStrip) return;
    const k = monitor && monitor.kpis ? monitor.kpis : {};
    const onT = k.orders_on_time != null ? k.orders_on_time : '—';
    const risk = k.orders_at_risk != null ? k.orders_at_risk : '—';
    const del = k.orders_delayed != null ? k.orders_delayed : '—';
    const comp = k.sla_compliance_pct != null ? `${k.sla_compliance_pct}%` : '—';
    const eff = k.workshop_efficiency_pct != null ? `${k.workshop_efficiency_pct}%` : '—';
    const avgStage = k.avg_minutes_by_stage || {};
    const avgParts = Object.keys(avgStage).slice(0, 3);
    const avgTxt =
      avgParts.length > 0
        ? avgParts
            .map((sk) => esc(STATUS[sk] || sk) + ': ' + esc(String(fmtMin(avgStage[sk]))))
            .join(' · ')
        : 'Sin histórico reciente';

    kpiStrip.classList.remove('d-none');
    kpiStrip.innerHTML = [
      kpiCard('En tiempo', String(onT), 'text-success'),
      kpiCard('En riesgo', String(risk), 'text-warning'),
      kpiCard('Retrasadas', String(del), 'text-danger'),
      kpiCard('Cumplimiento SLA', comp, 'text-dark'),
      kpiCard('Eficiencia (hist.)', eff, 'text-dark'),
      kpiCard('T. medio / etapa', avgTxt, 'text-muted small', true),
    ].join('');
  }

  function kpiCard(title, val, valClass, long) {
    return (
      '<div class="col"><div class="border rounded p-2 bg-light h-100">' +
      '<div class="small text-muted text-truncate" title="' +
      esc(title) +
      '">' +
      esc(title) +
      '</div>' +
      '<div class="fw-semibold ' +
      (valClass || '') +
      (long ? ' small' : '') +
      '">' +
      val +
      '</div></div></div>'
    );
  }

  function renderAlerts(monitor) {
    if (!alertsBody) return;
    const al = monitor && monitor.alerts ? monitor.alerts : { critical: [], preventive: [] };
    const crit = al.critical || [];
    const prev = al.preventive || [];
    let html = '';
    if (crit.length) {
      html += '<div class="fw-semibold text-danger mb-1 small">Críticas</div><ul class="list-unstyled mb-2">';
      crit.slice(0, 12).forEach((a) => {
        html +=
          '<li class="mb-1"><a href="/admin/workshop/orders/' +
          esc(a.order_id) +
          '" class="link-danger text-decoration-none">' +
          esc(a.message) +
          '</a></li>';
      });
      html += '</ul>';
    }
    if (prev.length) {
      html += '<div class="fw-semibold text-warning mb-1 small">Preventivas</div><ul class="list-unstyled mb-0">';
      prev.slice(0, 12).forEach((a) => {
        html +=
          '<li class="mb-1"><a href="/admin/workshop/orders/' +
          esc(a.order_id) +
          '" class="link-dark text-decoration-none">' +
          esc(a.message) +
          '</a></li>';
      });
      html += '</ul>';
    }
    if (!html) {
      html = '<p class="text-muted mb-0 small">Sin alertas activas.</p>';
    }
    alertsBody.innerHTML = html;

    if (heatmapHint) {
      const top = monitor && monitor.top_delayed_stage;
      const heat = monitor && monitor.heatmap_delayed_by_stage;
      let h = '';
      if (top && top.count > 0) {
        h =
          '<span class="text-danger">Mayor retraso: ' +
          esc(STATUS[top.stage_key] || top.stage_key) +
          ' (' +
          top.count +
          ')</span>';
      } else if (heat && Object.keys(heat).length) {
        const parts = Object.entries(heat)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 4)
          .map(([k, n]) => esc(STATUS[k] || k) + ': ' + n);
        h = 'Retrasos por etapa: ' + parts.join(', ');
      } else {
        h = 'Heatmap: sin cuellos de botella detectados en esta muestra.';
      }
      heatmapHint.textContent = '';
      heatmapHint.innerHTML = h;
    }
  }

  function renderCards(rows) {
    if (!Array.isArray(rows) || !rows.length) {
      grid.innerHTML = '<div class="col-12 text-muted small py-4">Sin órdenes</div>';
      return;
    }
    const sorted = rows.slice().sort((a, b) => {
      const sa = (a.sla && a.sla.state) || 'gray';
      const sb = (b.sla && b.sla.state) || 'gray';
      const ra = slaRank(sa);
      const rb = slaRank(sb);
      if (ra !== rb) return ra - rb;
      return (b.id || 0) - (a.id || 0);
    });

    grid.innerHTML = sorted
      .map((o) => {
        const v = o.vehicle || {};
        const plate = esc([v.plate, v.brand, v.model].filter(Boolean).join(' · ') || 'Vehículo');
        const cname = esc(o.customer_name || '');
        const sla = o.sla || {};
        const st = sla.state || 'gray';
        const accent = esc(sla.color || '#6c757d');
        const bar = Math.min(100, Math.max(0, Number(sla.bar_pct) || 0));
        const pct = sla.pct != null ? Math.round(Number(sla.pct)) : null;
        const procName = esc(sla.stage_name || STATUS[o.status] || o.status || '');
        const slaLine =
          sla.applicable === false
            ? '<span class="text-muted">Sin SLA</span>'
            : '<span class="wo-sla-time">' +
              esc(fmtMin(sla.elapsed_minutes)) +
              ' / ' +
              esc(fmtMin(sla.expected_minutes)) +
              '</span>';
        const badge =
          st === 'green'
            ? '<span class="badge bg-success">🟢 ' + esc(SLA_LABEL.green) + '</span>'
            : st === 'yellow'
              ? '<span class="badge bg-warning text-dark">🟡 ' + esc(SLA_LABEL.yellow) + '</span>'
              : st === 'red'
                ? '<span class="badge bg-danger">🔴 ' + esc(SLA_LABEL.red) + '</span>'
                : '<span class="badge bg-secondary">' + esc(SLA_LABEL.gray) + '</span>';
        const barClass =
          st === 'green' ? 'bg-success' : st === 'yellow' ? 'bg-warning' : st === 'red' ? 'bg-danger' : 'bg-secondary';
        const pauseNote = o.sla_paused ? '<div class="small text-danger mt-1">Pausa SLA</div>' : '';
        return (
          '<div class="col-md-6 col-xl-4">' +
          '<div class="card wo-sla-card h-100 shadow-sm" role="button" data-href="/admin/workshop/orders/' +
          o.id +
          '" style="border-left:4px solid ' +
          accent +
          '">' +
          '<div class="card-body py-2 px-3">' +
          '<div class="d-flex justify-content-between align-items-start gap-2">' +
          '<div class="fw-semibold">' +
          esc(o.code || '') +
          '</div>' +
          badge +
          '</div>' +
          '<div class="small text-muted">' +
          cname +
          '</div>' +
          '<div class="small mb-1">' +
          plate +
          '</div>' +
          '<div class="small fw-medium text-body">' +
          procName +
          '</div>' +
          '<div class="d-flex align-items-center gap-2 mt-2 mb-1">' +
          '<span class="small">⏱</span>' +
          slaLine +
          '</div>' +
          '<div class="progress wo-sla-progress">' +
          '<div class="progress-bar ' +
          barClass +
          '" style="width:' +
          bar +
          '%"></div></div>' +
          '<div class="small text-muted mt-1">' +
          (pct != null ? '[' + '█'.repeat(Math.min(10, Math.round(bar / 10))) + '░'.repeat(Math.max(0, 10 - Math.round(bar / 10))) + '] ' + pct + '%' : '') +
          '</div>' +
          pauseNote +
          '</div></div></div>'
        );
      })
      .join('');

    grid.querySelectorAll('.wo-sla-card').forEach((el) => {
      el.addEventListener('click', () => {
        const href = el.getAttribute('data-href');
        if (href) location.href = href;
      });
    });
  }

  function loadAll() {
    const st = filterEl && filterEl.value ? '?status=' + encodeURIComponent(filterEl.value) : '';
    err.classList.add('d-none');
    Promise.all([api('/api/workshop/orders' + st), api('/api/workshop/sla/monitor')])
      .then(([rows, monitor]) => {
        renderKpis(monitor);
        renderAlerts(monitor);
        renderCards(rows);
      })
      .catch((e) => {
        showErr(e.message || String(e));
        grid.innerHTML = '';
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
      loadAll();
    });
  }
  loadAll();
  setInterval(loadAll, 45000);
})();

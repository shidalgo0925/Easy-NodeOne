/**
 * CRM — Modal «Nuevo Lead»: cliente (M2O) igual que Taller
 * (`GET/POST /api/workshop/customers/*`): búsqueda, Crear «…», Crear y editar…, Buscar más…
 */
(function () {
  'use strict';

  const CUST_DEBOUNCE_MS = 300;

  function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function escAttr(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  async function workshopApi(url, method, body) {
    const opt = { method: method || 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (body != null) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const r = await fetch(url, opt);
    const text = await r.text().catch(function () {
      return '';
    });
    const t = text.trim();
    if (t.startsWith('<')) {
      throw new Error('Sesión caducada o respuesta HTML. Recargue la página e inicie sesión de nuevo.');
    }
    let d;
    if (!t) {
      d = {};
    } else {
      try {
        d = JSON.parse(text);
      } catch (e) {
        throw new Error('La API no devolvió JSON válido.');
      }
    }
    if (!r.ok) throw new Error((d && (d.detail || d.error)) || 'HTTP ' + r.status);
    return d;
  }

  function initCrmNewLeadModal() {
    const form = document.getElementById('newLeadForm');
    if (!form) return;

    const apiBase = (form.getAttribute('data-workshop-api-base') || '/api/workshop').replace(/\/$/, '');

    const search = document.getElementById('leadCustomerSearch');
    const menu = document.getElementById('leadCustomerMenu');
    const memberIdHidden = document.getElementById('leadSelectedUserId');
    const inpContact = document.getElementById('leadContactName');
    const inpCompany = document.getElementById('leadCompanyName');
    const inpEmail = document.getElementById('leadEmail');
    const inpPhone = document.getElementById('leadPhone');
    const inpTitle = form.querySelector('[name="name"]');
    if (!search || !menu || !memberIdHidden || !inpContact || !inpEmail) return;

    let fetchId = 0;
    let custM2oIndex = 0;
    let custDeb = null;

    function closeMenu() {
      menu.classList.remove('show');
      menu.innerHTML = '';
      search.setAttribute('aria-expanded', 'false');
      custM2oIndex = 0;
    }

    function setHighlight(idx) {
      const opts = Array.prototype.slice.call(menu.querySelectorAll('.crm-cust-kbd-opt'));
      opts.forEach(function (el, i) {
        el.classList.toggle('odoo-m2o-item-active', i === idx);
      });
      if (opts[idx]) opts[idx].scrollIntoView({ block: 'nearest' });
      return opts;
    }

    function buildCustomerDropdownHtml(users, qRaw) {
      const q = (qRaw || '').trim();
      let head = '';
      if (q) {
        const qDisp = escHtml(q);
        const qAttr = escAttr(q);
        head =
          '<button type="button" class="odoo-m2o-item crm-cust-kbd-opt crm-cust-quick-create border-0 w-100 text-start" data-q="' +
          qAttr +
          '">Crear "' +
          qDisp +
          '"</button>' +
          '<button type="button" class="odoo-m2o-item crm-cust-kbd-opt crm-cust-open-edit border-0 w-100 text-start">Crear y editar…</button>';
      }
      const body = (users || [])
        .map(function (u) {
          const title = escHtml(u.name || u.email || '');
          const em =
            u.email && String(u.email) !== String(u.name || '')
              ? '<span class="odoo-m2o-item-meta">' + escHtml(u.email) + '</span>'
              : '';
          return (
            '<button type="button" class="odoo-m2o-item crm-cust-kbd-opt crm-cust-m2o-opt" data-id="' +
            u.id +
            '" data-name="' +
            escAttr(u.name || '') +
            '" data-email="' +
            escAttr(u.email || '') +
            '"><span class="odoo-m2o-item-title">' +
            title +
            '</span>' +
            em +
            '</button>'
          );
        })
        .join('');
      let mid = '';
      if (users && users.length) {
        mid = body;
      } else {
        mid =
          '<div class="px-3 py-2 small text-muted">' +
          (q ? 'Sin coincidencias en esta organización' : 'No hay contactos en el listado reciente') +
          '</div>';
      }
      const footer =
        '<div class="odoo-m2o-footer border-top">' +
        '<a href="/admin/users" target="_blank" rel="noopener" class="odoo-m2o-more">Buscar más…</a>' +
        '</div>';
      const hint = '<div class="odoo-m2o-hint">Empiece a escribir…</div>';
      return head + mid + footer + hint;
    }

    async function renderCustomerDropdown(q, limit) {
      fetchId += 1;
      const fid = fetchId;
      menu.innerHTML = '<div class="text-muted small px-3 py-2">Cargando…</div>';
      menu.classList.add('show');
      search.setAttribute('aria-expanded', 'true');
      try {
        const url =
          apiBase + '/customers/search?q=' + encodeURIComponent((q || '').trim()) + '&limit=' + (limit || 15);
        const r = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        const text = await r.text().catch(function () {
          return '';
        });
        if (fid !== fetchId) return;
        if (!r.ok) {
          let err = 'Error ' + r.status;
          try {
            const j = JSON.parse(text);
            err = (j && (j.detail || j.error)) || err;
          } catch (e) {
            /* ignore */
          }
          menu.innerHTML =
            '<div class="px-3 py-2 small text-danger">' +
            escHtml(err) +
            '</div><div class="odoo-m2o-hint small px-3 pb-2">Si el módulo Taller está desactivado, no hay API de clientes.</div>';
          return;
        }
        const list = JSON.parse(text || '[]');
        const arr = Array.isArray(list) ? list : [];
        menu.innerHTML = buildCustomerDropdownHtml(arr, q);
        const kbd = Array.prototype.slice.call(menu.querySelectorAll('.crm-cust-kbd-opt'));
        custM2oIndex = kbd.length ? 0 : -1;
        if (kbd.length) setHighlight(custM2oIndex);
      } catch (e) {
        if (fid !== fetchId) return;
        menu.innerHTML =
          '<div class="px-3 py-2 small text-danger">' + escHtml(e.message || 'Error de red') + '</div>';
      }
    }

    function applyPick(u) {
      memberIdHidden.value = String(u.id || '');
      const disp = u.email && u.name ? u.name + ' (' + u.email + ')' : u.name || u.email || '';
      search.value = disp;
      search.dataset.lockedLabel = disp;
      inpContact.value = u.name || '';
      inpEmail.value = u.email || '';
      if (inpPhone) inpPhone.value = u.phone || '';
      if (inpTitle && !inpTitle.value.trim()) {
        inpTitle.value = 'Oportunidad: ' + (u.name || u.email || 'Cliente');
      }
      closeMenu();
    }

    async function quickCreateFromTypedLabel(raw) {
      const t = String(raw || '').trim();
      if (!t) return;
      try {
        let res;
        if (t.includes('@')) {
          res = await workshopApi(apiBase + '/customers', 'POST', { email: t.toLowerCase() });
        } else {
          res = await workshopApi(apiBase + '/customers', 'POST', { quick_create_name: t });
        }
        applyPick({ id: res.id, name: res.name, email: res.email });
      } catch (e) {
        alert(e.message || 'No se pudo crear el contacto');
      }
    }

    function openNewCustomerModal(prefillOverride) {
      closeMenu();
      const raw =
        prefillOverride != null && String(prefillOverride).trim() !== ''
          ? String(prefillOverride).trim()
          : search.value
            ? search.value.trim()
            : '';
      const em = document.getElementById('crmNewCustEmail');
      const fn = document.getElementById('crmNewCustFirst');
      const ln = document.getElementById('crmNewCustLast');
      const ph = document.getElementById('crmNewCustPhone');
      const er = document.getElementById('crmNewCustErr');
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
      const modalEl = document.getElementById('crmNewCustomerModal');
      if (window.bootstrap && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }

    async function submitNewCustomer() {
      const em = document.getElementById('crmNewCustEmail');
      const fn = document.getElementById('crmNewCustFirst');
      const ln = document.getElementById('crmNewCustLast');
      const ph = document.getElementById('crmNewCustPhone');
      const er = document.getElementById('crmNewCustErr');
      const payload = {
        email: (em && em.value.trim()) || '',
        first_name: (fn && fn.value.trim()) || '',
        last_name: (ln && ln.value.trim()) || '',
        phone: (ph && ph.value.trim()) || '',
      };
      try {
        const res = await workshopApi(apiBase + '/customers', 'POST', payload);
        applyPick({ id: res.id, name: res.name, email: res.email });
        const modalEl = document.getElementById('crmNewCustomerModal');
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

    function clearMemberPick() {
      memberIdHidden.value = '';
      delete search.dataset.lockedLabel;
      search.value = '';
      closeMenu();
    }

    search.addEventListener('focusin', function () {
      renderCustomerDropdown((search.value || '').trim(), 15);
    });
    search.addEventListener('click', function () {
      renderCustomerDropdown((search.value || '').trim(), 15);
    });
    search.addEventListener('input', function () {
      if (search.dataset.lockedLabel && search.value !== search.dataset.lockedLabel) {
        memberIdHidden.value = '';
        delete search.dataset.lockedLabel;
      }
      const q = (search.value || '').trim();
      clearTimeout(custDeb);
      custDeb = setTimeout(function () {
        renderCustomerDropdown(q, 15);
      }, CUST_DEBOUNCE_MS);
    });

    search.addEventListener('keydown', function (e) {
      if (!menu.classList.contains('show')) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          renderCustomerDropdown((search.value || '').trim(), 15);
        }
        return;
      }
      const opts = Array.prototype.slice.call(menu.querySelectorAll('.crm-cust-kbd-opt'));
      if (!opts.length) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeMenu();
        }
        return;
      }
      let idx = typeof custM2oIndex === 'number' ? custM2oIndex : 0;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        idx = Math.min(idx + 1, opts.length - 1);
        custM2oIndex = idx;
        setHighlight(idx);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        idx = Math.max(idx - 1, 0);
        custM2oIndex = idx;
        setHighlight(idx);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        opts[idx].click();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeMenu();
      }
    });

    document.getElementById('leadCustomerM2o')?.addEventListener('click', function (e) {
      const qc = e.target.closest && e.target.closest('.crm-cust-quick-create');
      if (qc) {
        e.preventDefault();
        quickCreateFromTypedLabel(qc.getAttribute('data-q') || '');
        return;
      }
      const ed = e.target.closest && e.target.closest('.crm-cust-open-edit');
      if (ed) {
        e.preventDefault();
        openNewCustomerModal();
        return;
      }
      const btn = e.target.closest && e.target.closest('.crm-cust-m2o-opt');
      if (btn && btn.getAttribute('data-id')) {
        e.preventDefault();
        applyPick({
          id: btn.getAttribute('data-id'),
          name: btn.getAttribute('data-name') || '',
          email: btn.getAttribute('data-email') || '',
        });
      }
    });

    document.querySelector('#leadCustomerM2o .crm-cust-toggle')?.addEventListener('click', function (e) {
      e.preventDefault();
      search.focus();
      renderCustomerDropdown((search.value || '').trim(), 15);
    });

    document.addEventListener('click', function (e) {
      if (!search || !menu) return;
      if (e.target === search || search.contains(e.target) || menu.contains(e.target)) return;
      closeMenu();
    });

    const btnClear = document.getElementById('leadClearMemberPick');
    if (btnClear) {
      btnClear.addEventListener('click', function (e) {
        e.preventDefault();
        clearMemberPick();
      });
    }

    document.getElementById('btnCrmNewCustSave')?.addEventListener('click', function (e) {
      e.preventDefault();
      submitNewCustomer();
    });

    form.addEventListener('reset', function () {
      clearMemberPick();
    });

    const modalEl = document.getElementById('newLeadModal');
    if (modalEl) {
      modalEl.addEventListener('hidden.bs.modal', function () {
        closeMenu();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCrmNewLeadModal);
  } else {
    initCrmNewLeadModal();
  }
})();

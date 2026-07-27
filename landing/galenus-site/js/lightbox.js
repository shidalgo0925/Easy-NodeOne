(function () {
  const root = document.createElement('div');
  root.className = 'lightbox';
  root.setAttribute('role', 'dialog');
  root.setAttribute('aria-modal', 'true');
  root.setAttribute('aria-label', 'Galería de imágenes');
  root.innerHTML =
    '<button type="button" class="lb-close" aria-label="Cerrar">&times;</button>' +
    '<button type="button" class="lb-nav lb-prev" aria-label="Anterior">&#8249;</button>' +
    '<button type="button" class="lb-nav lb-next" aria-label="Siguiente">&#8250;</button>' +
    '<img alt="" />' +
    '<div class="lb-meta">' +
      '<span class="lb-counter" hidden></span>' +
      '<div class="lb-caption" hidden></div>' +
    '</div>';
  document.body.appendChild(root);

  const imgEl = root.querySelector('img');
  const capEl = root.querySelector('.lb-caption');
  const countEl = root.querySelector('.lb-counter');
  const closeBtn = root.querySelector('.lb-close');
  const prevBtn = root.querySelector('.lb-prev');
  const nextBtn = root.querySelector('.lb-next');

  let items = [];
  let index = 0;

  function show(i) {
    if (!items.length) return;
    index = (i + items.length) % items.length;
    const item = items[index];
    imgEl.src = item.src;
    imgEl.alt = item.alt || '';

    if (item.alt) {
      capEl.textContent = item.alt;
      capEl.hidden = false;
    } else {
      capEl.hidden = true;
    }

    if (items.length > 1) {
      countEl.textContent = `${index + 1} / ${items.length}`;
      countEl.hidden = false;
      prevBtn.hidden = false;
      nextBtn.hidden = false;
    } else {
      countEl.hidden = true;
      prevBtn.hidden = true;
      nextBtn.hidden = true;
    }
  }

  function openAt(list, start) {
    items = list.filter((x) => x && x.src);
    if (!items.length) return;
    index = Math.max(0, Math.min(start, items.length - 1));
    show(index);
    root.classList.add('is-open');
    document.body.classList.add('lb-open');
    closeBtn.focus();
  }

  function close() {
    root.classList.remove('is-open');
    document.body.classList.remove('lb-open');
    imgEl.removeAttribute('src');
    items = [];
  }

  function prev() {
    if (items.length > 1) show(index - 1);
  }
  function next() {
    if (items.length > 1) show(index + 1);
  }

  closeBtn.addEventListener('click', close);
  prevBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    prev();
  });
  nextBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    next();
  });
  root.addEventListener('click', (e) => {
    if (e.target === root) close();
  });

  document.addEventListener('keydown', (e) => {
    if (!root.classList.contains('is-open')) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'ArrowRight') next();
  });

  // Swipe básico en touch
  let touchX = null;
  root.addEventListener(
    'touchstart',
    (e) => {
      touchX = e.changedTouches[0].screenX;
    },
    { passive: true }
  );
  root.addEventListener(
    'touchend',
    (e) => {
      if (touchX == null) return;
      const dx = e.changedTouches[0].screenX - touchX;
      touchX = null;
      if (Math.abs(dx) < 50) return;
      if (dx > 0) prev();
      else next();
    },
    { passive: true }
  );

  function itemFromImg(el) {
    return {
      src: el.currentSrc || el.src,
      alt: el.alt || '',
      el
    };
  }

  function groupFor(el) {
    const strip = el.closest('.gallery-strip');
    if (strip) return [...strip.querySelectorAll('img')].map(itemFromImg);

    const pdp = el.closest('.pdp .gallery, .gallery');
    if (pdp) {
      const thumbs = [...pdp.querySelectorAll('[data-src]')];
      if (thumbs.length) {
        return thumbs.map((btn) => {
          const src = btn.getAttribute('data-src');
          const img = btn.querySelector('img');
          return { src, alt: (img && img.alt) || el.alt || '', el: img || btn };
        });
      }
      return [...pdp.querySelectorAll('img')].map(itemFromImg);
    }

    const sectors = el.closest('.sectors');
    if (sectors) return [...sectors.querySelectorAll('img')].map(itemFromImg);

    const featured = el.closest('.featured, #grid, .catalog-grid');
    if (featured) return [...featured.querySelectorAll('.pic img, .feat .pic img')].map(itemFromImg);

    const brands = el.closest('.brands');
    if (brands) return [...brands.querySelectorAll('img')].map(itemFromImg);

    const demos = el.closest('.demo-grid');
    if (demos) return [...demos.querySelectorAll('.demo-media img')].map(itemFromImg);

    return [itemFromImg(el)];
  }

  function bind(el) {
    if (!el || el.tagName !== 'IMG') return;
    if (el.closest('a.logo, .logo-plate, .v2-header, .brand-fallback')) return;
    if (el.dataset.zoomBound === '1') return;
    el.dataset.zoomBound = '1';
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const group = groupFor(el);
      const start = Math.max(
        0,
        group.findIndex((g) => g.el === el || g.src === (el.currentSrc || el.src))
      );
      openAt(group, start === -1 ? 0 : start);
    });
  }

  const selectors = [
    'img[data-zoom]',
    '.pic img',
    '.gallery .main img',
    '.gallery-strip img',
    '.sector img',
    '.feat .pic img',
    '.demo-media img',
    '.pdp .gallery .main img',
    '.about-visual img',
    '.brand img'
  ].join(',');

  document.querySelectorAll(selectors).forEach(bind);

  // Thumbs de ficha: abrir galería en esa imagen
  document.querySelectorAll('.pdp .gallery [data-src]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const gallery = btn.closest('.gallery');
      const thumbs = [...gallery.querySelectorAll('[data-src]')];
      const list = thumbs.map((b) => {
        const img = b.querySelector('img');
        return { src: b.getAttribute('data-src'), alt: (img && img.alt) || '', el: img || b };
      });
      const start = thumbs.indexOf(btn);
      openAt(list, start);
      const main = document.getElementById('mainImg');
      if (main) main.src = btn.getAttribute('data-src');
    });
  });

  window.galenusLightbox = { open: (src, alt) => openAt([{ src, alt }], 0), close, prev, next };
})();

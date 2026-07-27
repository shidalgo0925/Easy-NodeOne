(function () {
  const btn = document.getElementById('menuBtn');
  const nav = document.getElementById('mobileNav');
  if (btn && nav) {
    btn.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      nav.hidden = !open;
      btn.setAttribute('aria-expanded', String(open));
    });
    nav.querySelectorAll('a').forEach((a) =>
      a.addEventListener('click', () => {
        nav.classList.remove('open');
        nav.hidden = true;
        btn.setAttribute('aria-expanded', 'false');
      })
    );
  }

  const root = document.querySelector('[data-hero-carousel]');
  if (!root) return;

  const slides = [...root.querySelectorAll('.hero-slide')];
  const dots = [...root.querySelectorAll('.hero-dot')];
  const prev = root.querySelector('.hero-prev');
  const next = root.querySelector('.hero-next');
  const progress = root.querySelector('.hero-progress span');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const MS = 6500;
  let i = 0;
  let timer = null;

  root.style.setProperty('--hero-ms', MS + 'ms');

  function go(n) {
    i = (n + slides.length) % slides.length;
    slides.forEach((s, idx) => {
      const on = idx === i;
      s.classList.toggle('is-active', on);
      if (on) s.removeAttribute('hidden');
      else s.setAttribute('hidden', '');
    });
    dots.forEach((d, idx) => {
      const on = idx === i;
      d.classList.toggle('is-on', on);
      d.setAttribute('aria-selected', String(on));
    });
    restartProgress();
  }

  function restartProgress() {
    root.classList.remove('is-playing');
    if (progress) {
      progress.style.animation = 'none';
      void progress.offsetWidth;
      progress.style.animation = '';
    }
    if (!reduce) root.classList.add('is-playing');
  }

  function play() {
    stop();
    if (reduce) return;
    restartProgress();
    timer = window.setInterval(() => go(i + 1), MS);
  }

  function stop() {
    if (timer) window.clearInterval(timer);
    timer = null;
    root.classList.remove('is-playing');
  }

  prev?.addEventListener('click', () => {
    go(i - 1);
    play();
  });
  next?.addEventListener('click', () => {
    go(i + 1);
    play();
  });
  dots.forEach((d) =>
    d.addEventListener('click', () => {
      go(Number(d.getAttribute('data-goto')) || 0);
      play();
    })
  );

  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', play);
  root.addEventListener('focusin', stop);
  root.addEventListener('focusout', (e) => {
    if (!root.contains(e.relatedTarget)) play();
  });

  document.addEventListener('keydown', (e) => {
    if (!root.matches(':hover') && document.activeElement !== document.body) return;
    if (e.key === 'ArrowLeft') {
      go(i - 1);
      play();
    }
    if (e.key === 'ArrowRight') {
      go(i + 1);
      play();
    }
  });

  go(0);
  play();
})();

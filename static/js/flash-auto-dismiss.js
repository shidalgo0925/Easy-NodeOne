(function () {
    'use strict';

    var DEFAULT_MS = 10000;

    function dismissAlert(el) {
        if (!el.isConnected || !el.classList.contains('show')) {
            return;
        }
        try {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                bootstrap.Alert.getOrCreateInstance(el).close();
                return;
            }
        } catch (err) {
            /* fall through */
        }
        el.remove();
    }

    function ensureProgressBar(el, ms) {
        el.classList.add('flash-auto-dismiss');
        el.style.setProperty('--flash-dismiss-ms', ms + 'ms');
        if (!el.querySelector('.flash-auto-dismiss__progress')) {
            var bar = document.createElement('div');
            bar.className = 'flash-auto-dismiss__progress';
            bar.setAttribute('aria-hidden', 'true');
            el.appendChild(bar);
        }
    }

    function scheduleFlashDismiss() {
        document.querySelectorAll('[data-auto-dismiss-ms]').forEach(function (el) {
            var ms = parseInt(el.getAttribute('data-auto-dismiss-ms'), 10);
            if (!ms || ms < 1000) {
                ms = DEFAULT_MS;
            }
            ensureProgressBar(el, ms);
            setTimeout(function () {
                dismissAlert(el);
            }, ms);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scheduleFlashDismiss);
    } else {
        scheduleFlashDismiss();
    }
})();

/**
 * Vista previa de branding: mini-shell + tokens en vivo en la app (sidebar/botones).
 * Esperado: #brandPreviewShell, #identity_preset_field, .identity-preset-btn,
 * #identityCustomFields, inputs identity_primary_color*.
 * window.NODEONE_IDENTITY_PRESETS = { preset: { primary_color, ... } }
 */
(function (global) {
    'use strict';

    var ROOT_VARS = [
        '--color-primary',
        '--color-primary-dark',
        '--color-accent',
        '--en1-accent',
        '--en1-sorbet',
        '--en1-action',
        '--en1-sidebar',
        '--en1-icon',
    ];

    function normalizeHex(v, fallback) {
        var s = (v || '').trim();
        if (/^#[0-9A-Fa-f]{6}$/.test(s)) return s;
        return fallback;
    }

    function applyColors(target, primary, primaryDark, accent) {
        if (!target || !target.style) return;
        var p = normalizeHex(primary, '#2563EB');
        var d = normalizeHex(primaryDark, '#1E3A8A');
        var a = normalizeHex(accent, '#06B6D4');
        target.style.setProperty('--bp-primary', p);
        target.style.setProperty('--bp-primary-dark', d);
        target.style.setProperty('--bp-accent', a);
        target.style.setProperty('--bp-sidebar', d);
        target.style.setProperty('--color-primary', p);
        target.style.setProperty('--color-primary-dark', d);
        target.style.setProperty('--color-accent', a);
        target.style.setProperty('--en1-accent', p);
        target.style.setProperty('--en1-sorbet', p);
        target.style.setProperty('--en1-action', p);
        target.style.setProperty('--en1-action-hover', p);
        target.style.setProperty('--en1-sidebar', d);
        target.style.setProperty('--en1-icon', a);
        return { primary: p, primaryDark: d, accent: a };
    }

    function applyLiveRoot(primary, primaryDark, accent) {
        applyColors(document.documentElement, primary, primaryDark, accent);
    }

    function clearLiveRoot() {
        var root = document.documentElement;
        ROOT_VARS.forEach(function (name) {
            root.style.removeProperty(name);
        });
        root.style.removeProperty('--bp-primary');
        root.style.removeProperty('--bp-primary-dark');
        root.style.removeProperty('--bp-accent');
        root.style.removeProperty('--bp-sidebar');
        root.style.removeProperty('--en1-action-hover');
    }

    function initBrandPreview(options) {
        options = options || {};
        var presets = options.presets || global.NODEONE_IDENTITY_PRESETS || {};
        var presetField = document.getElementById('identity_preset_field');
        var customFields = document.getElementById('identityCustomFields');
        var presetBtns = document.querySelectorAll('.identity-preset-btn');
        var previewShell = document.getElementById('brandPreviewShell');
        var inputPrimary = document.getElementById('identity_primary_color');
        var inputPrimaryDark = document.getElementById('identity_primary_color_dark');
        var inputAccent = document.getElementById('identity_accent_color');
        var liveApp = options.liveApp !== false;

        function colorsForPreset(preset) {
            if (preset === 'custom') {
                return {
                    primary: inputPrimary ? inputPrimary.value : '#2563EB',
                    primaryDark: inputPrimaryDark ? inputPrimaryDark.value : '#1E3A8A',
                    accent: inputAccent ? inputAccent.value : '#06B6D4',
                };
            }
            var row = presets[preset] || presets.azul || {};
            return {
                primary: row.primary_color || '#2563EB',
                primaryDark: row.primary_color_dark || '#1E3A8A',
                accent: row.accent_color || '#06B6D4',
            };
        }

        function refreshPreview() {
            var preset = presetField ? presetField.value : 'azul';
            var c = colorsForPreset(preset);
            if (previewShell) applyColors(previewShell, c.primary, c.primaryDark, c.accent);
            if (liveApp) applyLiveRoot(c.primary, c.primaryDark, c.accent);
        }

        function setPreset(preset) {
            if (presetField) presetField.value = preset;
            presetBtns.forEach(function (b) {
                var p = b.getAttribute('data-preset');
                b.classList.toggle('btn-primary', p === preset);
                b.classList.toggle('btn-outline-secondary', p !== preset);
            });
            if (customFields) customFields.classList.toggle('d-none', preset !== 'custom');
            if (preset !== 'custom' && presets[preset]) {
                var row = presets[preset];
                if (inputPrimary) inputPrimary.value = row.primary_color;
                if (inputPrimaryDark) inputPrimaryDark.value = row.primary_color_dark;
                if (inputAccent) inputAccent.value = row.accent_color;
            }
            refreshPreview();
        }

        presetBtns.forEach(function (b) {
            b.addEventListener('click', function () {
                setPreset(b.getAttribute('data-preset'));
            });
        });
        [inputPrimary, inputPrimaryDark, inputAccent].forEach(function (el) {
            if (!el) return;
            el.addEventListener('input', function () {
                if (presetField && presetField.value === 'custom') refreshPreview();
            });
        });

        setPreset(presetField ? presetField.value : 'azul');
        return { setPreset: setPreset, refreshPreview: refreshPreview, clearLiveRoot: clearLiveRoot };
    }

    global.NodeOneBrandPreview = {
        init: initBrandPreview,
        applyColors: applyColors,
        applyLiveRoot: applyLiveRoot,
        clearLiveRoot: clearLiveRoot,
    };
})(window);

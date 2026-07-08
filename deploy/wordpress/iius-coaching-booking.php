<?php
/**
 * Plugin Name: IIUS Reserva coaching (shortcode)
 * Description: [iius_coaching_booking] — citas coaching vía EN1 ECalendar + Google Calendar.
 * Version: 1.0.0
 */
if (!defined('ABSPATH')) {
    exit;
}

const IIUS_COACHING_EN1_API_DEFAULT = 'https://apps.internationalinstitute.us/api/ecalendar';

function iius_coaching_en1_api_base() {
    $url = get_option('iius_coaching_en1_api', '');
    if ($url === '') {
        $url = IIUS_COACHING_EN1_API_DEFAULT;
    }
    return rtrim(apply_filters('iius_coaching_en1_api_base', $url), '/');
}

add_shortcode('iius_coaching_booking', 'iius_coaching_booking_shortcode');

function iius_coaching_booking_shortcode($atts) {
    $atts = shortcode_atts(
        array(
            'api' => iius_coaching_en1_api_base(),
        ),
        $atts,
        'iius_coaching_booking'
    );
    $api = esc_url_raw($atts['api']);
    if (!$api) {
        return '<p class="iius-booking-msg">Configuración de reservas no disponible.</p>';
    }

    static $assets_done = false;
    $uid = 'iius-book-' . wp_generate_password(6, false, false);

    ob_start();
    if (!$assets_done) {
        $assets_done = true;
        ?>
<style>
.iius-book-wrap{max-width:640px;margin:1.5rem auto;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#00042D;}
.iius-book-wrap *{box-sizing:border-box;}
.iius-book-step{margin-bottom:1.25rem;}
.iius-book-label{display:block;font-weight:700;font-size:.85rem;margin-bottom:.5rem;color:#00042D;}
.iius-book-products{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;}
@media(max-width:520px){.iius-book-products{grid-template-columns:1fr;}}
.iius-book-product{border:2px solid #e5e7eb;border-radius:12px;padding:.85rem 1rem;cursor:pointer;background:#fff;transition:border-color .15s,background .15s;text-align:left;}
.iius-book-product:hover{border-color:#8B60AA;}
.iius-book-product.is-selected{border-color:#8B60AA;background:#f5f7fb;}
.iius-book-product strong{display:block;font-size:.95rem;color:#00042D;}
.iius-book-product span{font-size:.78rem;color:#6b7280;}
.iius-book-date{width:100%;max-width:280px;padding:.55rem .75rem;border:1px solid #d1d5db;border-radius:8px;font-size:1rem;}
.iius-book-slots{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.65rem;min-height:2rem;}
.iius-book-slot{border:1px solid #8B60AA;background:#fff;color:#00042D;border-radius:999px;padding:.4rem .85rem;font-size:.82rem;font-weight:600;cursor:pointer;}
.iius-book-slot:hover,.iius-book-slot.is-selected{background:#8B60AA;color:#fff;}
.iius-book-slot:disabled{opacity:.45;cursor:not-allowed;}
.iius-book-field{margin-bottom:.75rem;}
.iius-book-field input,.iius-book-field textarea{width:100%;padding:.55rem .75rem;border:1px solid #d1d5db;border-radius:8px;font-size:.95rem;}
.iius-book-field textarea{min-height:72px;resize:vertical;}
.iius-book-actions{display:flex;flex-wrap:wrap;gap:.65rem;margin-top:1rem;}
.iius-book-btn{display:inline-flex;align-items:center;justify-content:center;padding:.6rem 1.25rem;border-radius:999px;font-weight:700;font-size:.88rem;border:none;cursor:pointer;text-decoration:none;}
.iius-book-btn-primary{background:#8B60AA;color:#fff!important;}
.iius-book-btn-primary:hover{background:#00042D;}
.iius-book-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.iius-book-btn-ghost{background:transparent;color:#8B60AA;border:1px solid #8B60AA;}
.iius-book-msg{padding:.75rem 1rem;border-radius:10px;font-size:.88rem;margin:.75rem 0;}
.iius-book-msg--info{background:#f5f7fb;color:#374151;border:1px solid #e5e7eb;}
.iius-book-msg--err{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;}
.iius-book-msg--ok{background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;}
.iius-book-loading{opacity:.65;pointer-events:none;}
.iius-book-hidden{display:none!important;}
</style>
        <?php
    }
    ?>
<div class="iius-book-wrap" id="<?php echo esc_attr($uid); ?>" data-api="<?php echo esc_attr($api); ?>">
    <div class="iius-book-msg iius-book-msg--info iius-book-status"><?php esc_html_e('Elige el tipo de coaching y un horario disponible.', 'iius-coaching-booking'); ?></div>

    <div class="iius-book-panel iius-book-panel-form">
        <div class="iius-book-step">
            <span class="iius-book-label"><?php esc_html_e('1. Tipo de coaching', 'iius-coaching-booking'); ?></span>
            <div class="iius-book-products" role="group" aria-label="<?php esc_attr_e('Tipo de coaching', 'iius-coaching-booking'); ?>">
                <button type="button" class="iius-book-product" data-product-id="coaching_personal" data-product-name="<?php esc_attr_e('Coaching Personal', 'iius-coaching-booking'); ?>">
                    <strong><?php esc_html_e('Coaching Personal', 'iius-coaching-booking'); ?></strong>
                    <span><?php esc_html_e('Desarrollo integral y objetivos de vida', 'iius-coaching-booking'); ?></span>
                </button>
                <button type="button" class="iius-book-product" data-product-id="coaching_ejecutivo" data-product-name="<?php esc_attr_e('Coaching Ejecutivo', 'iius-coaching-booking'); ?>">
                    <strong><?php esc_html_e('Coaching Ejecutivo', 'iius-coaching-booking'); ?></strong>
                    <span><?php esc_html_e('Liderazgo, equipos y desempeño profesional', 'iius-coaching-booking'); ?></span>
                </button>
            </div>
        </div>

        <div class="iius-book-step">
            <label class="iius-book-label" for="<?php echo esc_attr($uid); ?>-date"><?php esc_html_e('2. Fecha', 'iius-coaching-booking'); ?></label>
            <input type="date" class="iius-book-date" id="<?php echo esc_attr($uid); ?>-date" disabled />
            <div class="iius-book-slots" aria-live="polite"></div>
        </div>

        <div class="iius-book-step iius-book-step-details iius-book-hidden">
            <span class="iius-book-label"><?php esc_html_e('3. Tus datos', 'iius-coaching-booking'); ?></span>
            <div class="iius-book-field">
                <input type="text" name="name" placeholder="<?php esc_attr_e('Nombre completo *', 'iius-coaching-booking'); ?>" required autocomplete="name" />
            </div>
            <div class="iius-book-field">
                <input type="email" name="email" placeholder="<?php esc_attr_e('Correo electrónico *', 'iius-coaching-booking'); ?>" required autocomplete="email" />
            </div>
            <div class="iius-book-field">
                <input type="tel" name="whatsapp" placeholder="<?php esc_attr_e('WhatsApp (opcional)', 'iius-coaching-booking'); ?>" autocomplete="tel" />
            </div>
            <div class="iius-book-field">
                <textarea name="notes" placeholder="<?php esc_attr_e('Comentarios (opcional)', 'iius-coaching-booking'); ?>"></textarea>
            </div>
            <div class="iius-book-actions">
                <button type="button" class="iius-book-btn iius-book-btn-primary iius-book-submit"><?php esc_html_e('Confirmar cita', 'iius-coaching-booking'); ?></button>
                <button type="button" class="iius-book-btn iius-book-btn-ghost iius-book-back"><?php esc_html_e('Cambiar horario', 'iius-coaching-booking'); ?></button>
            </div>
        </div>
    </div>

    <div class="iius-book-panel iius-book-panel-done iius-book-hidden">
        <div class="iius-book-msg iius-book-msg--ok iius-book-done-text"></div>
    </div>
</div>
<script>
(function(){
    var root = document.getElementById(<?php echo wp_json_encode($uid); ?>);
    if (!root) return;
    var api = root.getAttribute('data-api') || '';
    var statusEl = root.querySelector('.iius-book-status');
    var dateInput = root.querySelector('.iius-book-date');
    var slotsEl = root.querySelector('.iius-book-slots');
    var detailsEl = root.querySelector('.iius-book-step-details');
    var formPanel = root.querySelector('.iius-book-panel-form');
    var donePanel = root.querySelector('.iius-book-panel-done');
    var doneText = root.querySelector('.iius-book-done-text');
    var productBtns = root.querySelectorAll('.iius-book-product');
    var submitBtn = root.querySelector('.iius-book-submit');
    var backBtn = root.querySelector('.iius-book-back');

    var state = { productId: '', productName: '', slotStart: '', slotLabel: '', timezone: '' };

    function msg(text, kind) {
        statusEl.className = 'iius-book-msg iius-book-status iius-book-msg--' + (kind || 'info');
        statusEl.textContent = text;
    }

    function setLoading(on) {
        root.classList.toggle('iius-book-loading', !!on);
    }

    function minDateStr() {
        var d = new Date();
        return d.toISOString().slice(0, 10);
    }

    function maxDateStr() {
        var d = new Date();
        d.setDate(d.getDate() + 30);
        return d.toISOString().slice(0, 10);
    }

    dateInput.min = minDateStr();
    dateInput.max = maxDateStr();

    function formatSlotLabel(iso, tz) {
        try {
            var d = new Date(iso);
            return d.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: tz || undefined });
        } catch (e) {
            return iso;
        }
    }

    function checkHealth() {
        setLoading(true);
        fetch(api + '/health', { credentials: 'omit' })
            .then(function(r){ return r.json(); })
            .then(function(j){
                if (!j || !j.ok) throw new Error('health');
                if (!j.enabled || !j.google_connected || !j.oauth_valid) {
                    msg('Las reservas en línea se activarán pronto. Mientras tanto contáctanos por correo.', 'info');
                    dateInput.disabled = true;
                    return;
                }
                msg('Elige el tipo de coaching y un horario disponible.', 'info');
            })
            .catch(function(){
                msg('No pudimos conectar con el sistema de citas. Intenta más tarde.', 'err');
            })
            .finally(function(){ setLoading(false); });
    }

    productBtns.forEach(function(btn){
        btn.addEventListener('click', function(){
            productBtns.forEach(function(b){ b.classList.remove('is-selected'); });
            btn.classList.add('is-selected');
            state.productId = btn.getAttribute('data-product-id') || '';
            state.productName = btn.getAttribute('data-product-name') || '';
            state.slotStart = '';
            detailsEl.classList.add('iius-book-hidden');
            dateInput.disabled = false;
            if (!dateInput.value) dateInput.value = minDateStr();
            loadSlots();
        });
    });

    function loadSlots() {
        if (!state.productId || !dateInput.value) {
            slotsEl.innerHTML = '';
            return;
        }
        setLoading(true);
        slotsEl.innerHTML = '';
        fetch(api + '/availability?date=' + encodeURIComponent(dateInput.value), { credentials: 'omit' })
            .then(function(r){ return r.json().then(function(j){ return { ok: r.ok, j: j }; }); })
            .then(function(res){
                var j = res.j || {};
                if (!res.ok || !j.ok) {
                    var err = (j.error || 'error');
                    if (err === 'ecalendar_disabled' || err === 'google_not_configured') {
                        msg('Las reservas en línea se activarán pronto.', 'info');
                    } else if (err === 'past_date') {
                        msg('Elige una fecha futura.', 'err');
                    } else {
                        msg('No hay horarios para esta fecha. Prueba otro día.', 'info');
                    }
                    return;
                }
                state.timezone = j.timezone || '';
                var slots = j.slots || [];
                if (!slots.length) {
                    msg('No hay horarios libres este día. Prueba otra fecha.', 'info');
                    return;
                }
                msg('Selecciona un horario.', 'info');
                slots.forEach(function(slot){
                    var b = document.createElement('button');
                    b.type = 'button';
                    b.className = 'iius-book-slot';
                    b.textContent = formatSlotLabel(slot.start, state.timezone);
                    b.setAttribute('data-start', slot.start);
                    b.addEventListener('click', function(){
                        root.querySelectorAll('.iius-book-slot').forEach(function(x){ x.classList.remove('is-selected'); });
                        b.classList.add('is-selected');
                        state.slotStart = slot.start;
                        state.slotLabel = b.textContent;
                        detailsEl.classList.remove('iius-book-hidden');
                        msg('Completa tus datos para confirmar: ' + state.slotLabel, 'info');
                    });
                    slotsEl.appendChild(b);
                });
            })
            .catch(function(){
                msg('Error al cargar horarios.', 'err');
            })
            .finally(function(){ setLoading(false); });
    }

    dateInput.addEventListener('change', loadSlots);

    backBtn.addEventListener('click', function(){
        detailsEl.classList.add('iius-book-hidden');
        state.slotStart = '';
        root.querySelectorAll('.iius-book-slot').forEach(function(x){ x.classList.remove('is-selected'); });
        msg('Selecciona otro horario.', 'info');
    });

    submitBtn.addEventListener('click', function(){
        if (!state.productId || !state.slotStart) {
            msg('Elige tipo de coaching y horario.', 'err');
            return;
        }
        var name = (root.querySelector('[name="name"]').value || '').trim();
        var email = (root.querySelector('[name="email"]').value || '').trim();
        var whatsapp = (root.querySelector('[name="whatsapp"]').value || '').trim();
        var notes = (root.querySelector('[name="notes"]').value || '').trim();
        if (name.length < 2 || !email) {
            msg('Nombre y correo son obligatorios.', 'err');
            return;
        }
        setLoading(true);
        fetch(api + '/bookings', {
            method: 'POST',
            credentials: 'omit',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({
                product_id: state.productId,
                name: name,
                email: email,
                whatsapp: whatsapp,
                notes: notes,
                slot_start: state.slotStart
            })
        })
            .then(function(r){ return r.json().then(function(j){ return { status: r.status, j: j }; }); })
            .then(function(res){
                var j = res.j || {};
                if (!j.ok) {
                    var errMap = {
                        slot_unavailable: 'Ese horario ya no está disponible. Elige otro.',
                        invalid_email: 'Correo inválido.',
                        invalid_name: 'Nombre demasiado corto.',
                        invalid_product: 'Tipo de coaching no válido.'
                    };
                    msg(errMap[j.error] || 'No se pudo confirmar la cita.', 'err');
                    if (j.error === 'slot_unavailable') loadSlots();
                    return;
                }
                formPanel.classList.add('iius-book-hidden');
                donePanel.classList.remove('iius-book-hidden');
                doneText.textContent = '¡Cita confirmada! Revisa tu correo (' + email + ') para la invitación de calendario.';
                statusEl.classList.add('iius-book-hidden');
            })
            .catch(function(){
                msg('Error de conexión al confirmar.', 'err');
            })
            .finally(function(){ setLoading(false); });
    });

    checkHealth();
})();
</script>
    <?php
    return ob_get_clean();
}

add_action('admin_menu', 'iius_coaching_booking_admin_menu');
add_action('admin_init', 'iius_coaching_booking_register_settings');

function iius_coaching_booking_register_settings() {
    register_setting(
        'iius_coaching_booking_group',
        'iius_coaching_en1_api',
        array(
            'type'              => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default'           => IIUS_COACHING_EN1_API_DEFAULT,
        )
    );
    if (get_option('iius_coaching_en1_api', '') === '') {
        update_option('iius_coaching_en1_api', IIUS_COACHING_EN1_API_DEFAULT, false);
    }
}

function iius_coaching_booking_admin_menu() {
    add_options_page(
        'IIUS Reserva coaching',
        'IIUS Coaching booking',
        'manage_options',
        'iius-coaching-booking',
        'iius_coaching_booking_admin_page'
    );
}

function iius_coaching_booking_admin_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    ?>
    <div class="wrap">
        <h1>IIUS — Reserva coaching (EN1)</h1>
        <p>Shortcode: <code>[iius_coaching_booking]</code> — colócalo en la sección <strong>Agendar Coaching Online</strong> de <code>/coaching/</code>.</p>
        <form method="post" action="options.php">
            <?php settings_fields('iius_coaching_booking_group'); ?>
            <table class="form-table">
                <tr>
                    <th scope="row"><label for="iius_coaching_en1_api">API EN1 ECalendar</label></th>
                    <td>
                        <input type="url" class="regular-text" id="iius_coaching_en1_api" name="iius_coaching_en1_api"
                               value="<?php echo esc_attr(get_option('iius_coaching_en1_api', IIUS_COACHING_EN1_API_DEFAULT)); ?>" />
                        <p class="description">Requiere ECalendar activo y OAuth en Apps → Agenda ECalendar. CORS: <code>https://internationalinstitute.us</code></p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

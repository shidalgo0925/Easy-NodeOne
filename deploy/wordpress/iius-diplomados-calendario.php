<?php
/**
 * Plugin Name: IIUS Calendario de diplomados (shortcode)
 * Description: [iius_diplomados_calendario] — títulos y fechas desde EN1 (apps) vía API pública.
 * Version: 1.2.0
 */
if (!defined('ABSPATH')) {
    exit;
}

const IIUS_DIPLOMADO_EN1_API_DEFAULT = 'https://apps.internationalinstitute.us/api/public/diplomado-inicios';
const IIUS_DIPLOMADO_EN1_APPS_BASE   = 'https://apps.internationalinstitute.us';
const IIUS_DIPLOMADO_EN1_CACHE_TTL   = 300;

/**
 * URL del JSON en EN1 (fuente única).
 */
function iius_diplomado_en1_api_url() {
    $url = get_option('iius_diplomado_sync_url', '');
    if ($url === '') {
        $url = IIUS_DIPLOMADO_EN1_API_DEFAULT;
    }
    return apply_filters('iius_diplomado_en1_api_url', $url);
}

/**
 * Etiquetas de respaldo si la API no envía name (legado).
 */
function iius_diplomado_cal_labels() {
    return array(
        'neuro-liderazgo-intercultural'                      => 'Neuro-Liderazgo y Coaching Ejecutivo Intercultural',
        'neuro-descodificacion-psicogenealogia-pnl'            => 'Neuro-Decodificación™, Psicogenealogía y PNL',
        'neuro-teologia-coaching-cristiano-transgeneracional' => 'Neuro-Teología™ y Coaching Espiritual Cristiano',
        'neuro-heuristica-coaching-vida'                       => 'Neuro-Heurística™ y Coaching de Vida',
    );
}

/**
 * Obtiene by_heading desde EN1 (transient) o opción local de respaldo.
 *
 * @return array<string, array>|WP_Error
 */
function iius_diplomado_fetch_rows_from_en1($force = false) {
    $api_url = iius_diplomado_en1_api_url();
    $cache_key = 'iius_cal_en1_' . md5($api_url);

    if (!$force) {
        $cached = get_transient($cache_key);
        if (is_array($cached) && !empty($cached['by_heading'])) {
            return $cached['by_heading'];
        }
    }

    $res = wp_remote_get(
        $api_url,
        array(
            'timeout' => 15,
            'headers' => array('Accept' => 'application/json'),
        )
    );
    if (is_wp_error($res)) {
        return $res;
    }
    $code = wp_remote_retrieve_response_code($res);
    $body = wp_remote_retrieve_body($res);
    if ($code < 200 || $code >= 300) {
        return new WP_Error('iius_cal_http', 'HTTP ' . $code);
    }
    $data = json_decode($body, true);
    if (!is_array($data) || empty($data['by_heading']) || !is_array($data['by_heading'])) {
        return new WP_Error('iius_cal_json', 'JSON EN1 inválido o vacío');
    }

    $by = $data['by_heading'];
    uasort(
        $by,
        static function ($a, $b) {
            $ia = isset($a['fecha_iso']) ? $a['fecha_iso'] : '';
            $ib = isset($b['fecha_iso']) ? $b['fecha_iso'] : '';
            return strcmp($ia, $ib);
        }
    );

    $payload = array(
        'updated'    => isset($data['updated']) ? $data['updated'] : current_time('mysql'),
        'timezone'   => isset($data['timezone']) ? $data['timezone'] : wp_timezone_string(),
        'by_heading' => $by,
    );
    update_option('iius_diplomado_inicios', $payload, false);
    set_transient($cache_key, $payload, IIUS_DIPLOMADO_EN1_CACHE_TTL);

    return $by;
}

/**
 * Filas para el calendario: EN1 primero, opción WP si falla la API.
 *
 * @return array<string, array>
 */
function iius_diplomado_cal_rows() {
    $live = iius_diplomado_fetch_rows_from_en1(false);
    if (!is_wp_error($live) && is_array($live) && !empty($live)) {
        return $live;
    }
    $opt = get_option('iius_diplomado_inicios', array());
    $rows = isset($opt['by_heading']) && is_array($opt['by_heading']) ? $opt['by_heading'] : array();
    if (!empty($rows)) {
        uasort(
            $rows,
            static function ($a, $b) {
                $ia = isset($a['fecha_iso']) ? $a['fecha_iso'] : '';
                $ib = isset($b['fecha_iso']) ? $b['fecha_iso'] : '';
                return strcmp($ia, $ib);
            }
        );
    }
    return $rows;
}

add_shortcode('iius_diplomados_calendario', 'iius_diplomados_calendario_shortcode');

function iius_diplomados_calendario_shortcode($atts) {
    $rows = iius_diplomado_cal_rows();

    if (empty($rows)) {
        return '<p class="iius-cal-empty" style="text-align:center;color:#6b7280;">Las fechas de inicio se publicarán pronto.</p>';
    }

    $labels_fallback = iius_diplomado_cal_labels();
    $meses           = array('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre');
    $apps_base       = apply_filters('iius_diplomado_apps_base', IIUS_DIPLOMADO_EN1_APPS_BASE);

    static $css_done = false;
    $css = '';
    if (!$css_done) {
        $css_done = true;
        $css     = '<style>
.iius-cal-wrap{max-width:1100px;margin:0 auto;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
.iius-cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem;}
.iius-cal-card{display:flex;border-radius:14px;overflow:hidden;border:1px solid #e5e7eb;background:#fff;box-shadow:0 8px 24px rgba(15,23,42,.06);}
.iius-cal-date{flex:0 0 88px;background:linear-gradient(160deg,#00042D,#8B60AA);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:.65rem .5rem;text-align:center;}
.iius-cal-day{font-size:1.75rem;font-weight:800;line-height:1;}
.iius-cal-month{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;opacity:.95;margin-top:.25rem;}
.iius-cal-year{font-size:.7rem;opacity:.85;margin-top:.15rem;}
.iius-cal-body{flex:1;padding:.85rem 1rem;display:flex;flex-direction:column;gap:.35rem;}
.iius-cal-title{font-size:.92rem;font-weight:700;color:#111827;margin:0;line-height:1.35;}
.iius-cal-meta{font-size:.78rem;color:#6b7280;margin:0;}
.iius-cal-cta{display:inline-block;margin-top:.35rem;align-self:flex-start;padding:.45rem .85rem;border-radius:999px;background:#8B60AA;color:#fff!important;text-decoration:none;font-weight:600;font-size:.8rem;}
.iius-cal-cta:hover{background:#00042D;filter:none;}
@media(max-width:480px){.iius-cal-card{flex-direction:column;}.iius-cal-date{flex-direction:row;gap:.75rem;width:100%;justify-content:center;padding:.75rem;}}
</style>';
    }

    $html = $css . '<div class="iius-cal-wrap"><div class="iius-cal-grid">';

    foreach ($rows as $slug => $item) {
        if (!is_array($item)) {
            continue;
        }
        $iso = isset($item['fecha_iso']) ? $item['fecha_iso'] : '';
        if (!$iso || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $iso)) {
            continue;
        }
        $dt   = DateTime::createFromFormat('Y-m-d', $iso, wp_timezone());
        $dia  = $dt ? $dt->format('d') : '';
        $mesi = $dt ? (int) $dt->format('n') : 1;
        $anio = $dt ? $dt->format('Y') : '';
        $mes  = isset($meses[ $mesi - 1 ]) ? $meses[ $mesi - 1 ] : '';

        $label = '';
        if (!empty($item['name'])) {
            $label = $item['name'];
        } elseif (!empty($item['title'])) {
            $label = $item['title'];
        } elseif (isset($labels_fallback[ $slug ])) {
            $label = $labels_fallback[ $slug ];
        } else {
            $label = $slug;
        }
        $texto = isset($item['fecha_texto']) ? $item['fecha_texto'] : '';
        $url   = rtrim($apps_base, '/') . '/inscripcion/' . rawurlencode($slug);

        $html .= '<article class="iius-cal-card">';
        $html .= '<div class="iius-cal-date"><span class="iius-cal-day">' . esc_html($dia) . '</span>';
        $html .= '<span class="iius-cal-month">' . esc_html($mes) . '</span>';
        $html .= '<span class="iius-cal-year">' . esc_html($anio) . '</span></div>';
        $html .= '<div class="iius-cal-body">';
        $html .= '<h3 class="iius-cal-title">' . esc_html($label) . '</h3>';
        if ($texto) {
            $html .= '<p class="iius-cal-meta">Inicio: ' . esc_html($texto) . '</p>';
        }
        $html .= '<a class="iius-cal-cta" href="' . esc_url($url) . '" target="_blank" rel="noopener noreferrer">Ver inscripción</a>';
        $html .= '</div></article>';
    }

    $html .= '</div></div>';

    return $html;
}

/* ---------- Admin: sincronizar desde backend ---------- */

add_action('admin_menu', 'iius_diplomado_cal_admin_menu');
add_action('admin_init', 'iius_diplomado_cal_register_settings');
add_action('admin_post_iius_diplomado_sync_now', 'iius_diplomado_sync_now_handler');

function iius_diplomado_cal_register_settings() {
    register_setting(
        'iius_diplomado_cal_group',
        'iius_diplomado_sync_url',
        array(
            'type'              => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default'           => IIUS_DIPLOMADO_EN1_API_DEFAULT,
        )
    );
    register_setting(
        'iius_diplomado_cal_group',
        'iius_diplomado_sync_token',
        array(
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default'           => '',
        )
    );
    if (get_option('iius_diplomado_sync_url', '') === '') {
        update_option('iius_diplomado_sync_url', IIUS_DIPLOMADO_EN1_API_DEFAULT, false);
    }
}

function iius_diplomado_cal_admin_menu() {
    add_options_page(
        'IIUS Calendario diplomados',
        'IIUS Calendario',
        'manage_options',
        'iius-calendario-diplomados',
        'iius_diplomado_cal_admin_page'
    );
}

function iius_diplomado_format_date_es($iso) {
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $iso)) {
        return '';
    }
    try {
        $tz = wp_timezone();
        $dt = new DateTimeImmutable($iso, $tz);
        $ts = $dt->getTimestamp();
        return wp_date('j \d\e F \d\e Y', $ts, $tz);
    } catch (Exception $e) {
        return $iso;
    }
}

/**
 * Convierte JSON del backend al formato guardado en iius_diplomado_inicios.
 *
 * @param array $data Datos decodificados.
 * @return array|WP_Error
 */
function iius_diplomado_normalize_sync_payload(array $data) {
    $by = array();

    if (!empty($data['by_heading']) && is_array($data['by_heading'])) {
        $by = $data['by_heading'];
    } elseif (!empty($data['programs']) && is_array($data['programs'])) {
        foreach ($data['programs'] as $p) {
            if (!is_array($p)) {
                continue;
            }
            $slug = isset($p['slug']) ? sanitize_title($p['slug']) : '';
            if ($slug === '') {
                continue;
            }
            $by[ $slug ] = array(
                'fecha_iso'            => isset($p['fecha_iso']) ? sanitize_text_field($p['fecha_iso']) : '',
                'fecha_texto'          => isset($p['fecha_texto']) ? sanitize_text_field($p['fecha_texto']) : '',
                'name'                 => isset($p['name']) ? sanitize_text_field($p['name']) : '',
                'heading_elementor_id' => isset($p['heading_elementor_id']) ? sanitize_text_field($p['heading_elementor_id']) : '',
            );
        }
    } else {
        return new WP_Error('iius_sync_format', 'JSON no reconocido. Use by_heading o programs[].');
    }

    $old = get_option('iius_diplomado_inicios', array());
    $old_bh = isset($old['by_heading']) && is_array($old['by_heading']) ? $old['by_heading'] : array();

    foreach ($by as $slug => &$row) {
        if (!is_array($row)) {
            unset($by[ $slug ]);
            continue;
        }
        $row['fecha_iso'] = isset($row['fecha_iso']) ? preg_replace('/[^0-9-]/', '', $row['fecha_iso']) : '';
        if ($row['fecha_iso'] !== '' && !preg_match('/^\d{4}-\d{2}-\d{2}$/', $row['fecha_iso'])) {
            return new WP_Error('iius_sync_date', 'fecha_iso inválida para: ' . $slug);
        }
        if ($row['fecha_iso'] !== '' && empty($row['fecha_texto'])) {
            $row['fecha_texto'] = iius_diplomado_format_date_es($row['fecha_iso']);
        }
        if (empty($row['heading_elementor_id']) && isset($old_bh[ $slug ]['heading_elementor_id'])) {
            $row['heading_elementor_id'] = $old_bh[ $slug ]['heading_elementor_id'];
        }
    }
    unset($row);

    $payload = array(
        'updated'    => current_time('mysql'),
        'timezone'   => wp_timezone_string(),
        'by_heading' => $by,
    );

    return apply_filters('iius_diplomado_sync_normalized', $payload, $data);
}

function iius_diplomado_fetch_remote_json($url, $token) {
    $args = array(
        'timeout' => 20,
        'headers' => array(
            'Accept' => 'application/json',
        ),
    );
    if ($token !== '') {
        $args['headers']['Authorization'] = 'Bearer ' . $token;
    }

    $res = wp_remote_get($url, $args);
    if (is_wp_error($res)) {
        return $res;
    }
    $code = wp_remote_retrieve_response_code($res);
    $body = wp_remote_retrieve_body($res);
    if ($code < 200 || $code >= 300) {
        return new WP_Error('iius_sync_http', 'HTTP ' . $code . ' — ' . wp_trim_words($body, 30, '…'));
    }
    $data = json_decode($body, true);
    if (!is_array($data)) {
        return new WP_Error('iius_sync_json', 'Respuesta no es JSON válido.');
    }
    return $data;
}

function iius_diplomado_sync_now_handler() {
    if (! current_user_can('manage_options')) {
        wp_die(esc_html__('No tienes permisos.', 'iius-cal'));
    }
    check_admin_referer('iius_diplomado_sync_now', 'iius_diplomado_sync_nonce');

    $live = iius_diplomado_fetch_rows_from_en1(true);
    if (is_wp_error($live)) {
        set_transient('iius_diplomado_sync_error', $live->get_error_message(), 120);
        wp_safe_redirect(
            add_query_arg('iius_sync', 'error', admin_url('options-general.php?page=iius-calendario-diplomados'))
        );
        exit;
    }

    wp_safe_redirect(
        add_query_arg('iius_sync', 'ok', admin_url('options-general.php?page=iius-calendario-diplomados'))
    );
    exit;
}

function iius_diplomado_cal_admin_page() {
    if (! current_user_can('manage_options')) {
        return;
    }

    $err = get_transient('iius_diplomado_sync_error');
    if ($err) {
        delete_transient('iius_diplomado_sync_error');
    }

    $sync = isset($_GET['iius_sync']) ? sanitize_text_field(wp_unslash($_GET['iius_sync'])) : '';

    ?>
    <div class="wrap">
        <h1><?php echo esc_html__('Calendario de diplomados IIUS', 'iius-cal'); ?></h1>

        <?php if ($sync === 'ok') : ?>
            <div class="notice notice-success is-dismissible"><p><?php echo esc_html__('Datos actualizados desde EN1.', 'iius-cal'); ?></p></div>
        <?php elseif ($sync === 'no_url') : ?>
            <div class="notice notice-warning is-dismissible"><p><?php echo esc_html__('Configura primero la URL del endpoint.', 'iius-cal'); ?></p></div>
        <?php elseif ($sync === 'error' && $err) : ?>
            <div class="notice notice-error is-dismissible"><p><strong><?php echo esc_html__('Error:', 'iius-cal'); ?></strong> <?php echo esc_html($err); ?></p></div>
        <?php endif; ?>

        <p><?php echo esc_html__('El calendario en /coaching/ lee en vivo', 'iius-cal'); ?>
            <code><?php echo esc_html(IIUS_DIPLOMADO_EN1_API_DEFAULT); ?></code>
            <?php echo esc_html__('(diplomados publicados en Apps con fecha de inicio). Caché', 'iius-cal'); ?>
            <?php echo (int) IIUS_DIPLOMADO_EN1_CACHE_TTL; ?>
            <?php echo esc_html__('s.', 'iius-cal'); ?></p>

        <h2 class="title"><?php echo esc_html__('Configuración del endpoint', 'iius-cal'); ?></h2>
        <form method="post" action="options.php">
            <?php settings_fields('iius_diplomado_cal_group'); ?>
            <table class="form-table" role="presentation">
                <tr>
                    <th scope="row"><label for="iius_diplomado_sync_url"><?php echo esc_html__('URL del JSON', 'iius-cal'); ?></label></th>
                    <td>
                        <input name="iius_diplomado_sync_url" id="iius_diplomado_sync_url" type="url" class="large-text code" value="<?php echo esc_attr(get_option('iius_diplomado_sync_url', IIUS_DIPLOMADO_EN1_API_DEFAULT)); ?>" />
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="iius_diplomado_sync_token"><?php echo esc_html__('Token Bearer (opcional)', 'iius-cal'); ?></label></th>
                    <td>
                        <input name="iius_diplomado_sync_token" id="iius_diplomado_sync_token" type="password" class="large-text code" value="<?php echo esc_attr(get_option('iius_diplomado_sync_token', '')); ?>" autocomplete="off" />
                    </td>
                </tr>
            </table>
            <?php submit_button(__('Guardar cambios', 'iius-cal')); ?>
        </form>

        <h2 class="title"><?php echo esc_html__('Actualizar ahora', 'iius-cal'); ?></h2>
        <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
            <?php wp_nonce_field('iius_diplomado_sync_now', 'iius_diplomado_sync_nonce'); ?>
            <input type="hidden" name="action" value="iius_diplomado_sync_now" />
            <?php submit_button(__('Refrescar desde EN1 (Apps)', 'iius-cal'), 'primary', 'submit', false); ?>
        </form>
    </div>
    <?php
}

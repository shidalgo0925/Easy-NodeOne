<?php
/**
 * Parche Elementor: /coaching/ (208) y home (32) — vitrina EN1.
 * wp eval-file /opt/easynodeone/app/deploy/wordpress/patch_iius_coaching_landing.php --path=/var/www/wordpress
 */
if (!defined('ABSPATH')) {
    exit(1);
}

function iius_elementor_walk_patch(&$elements, callable $fn) {
    if (!is_array($elements)) {
        return;
    }
    foreach ($elements as &$el) {
        if (!is_array($el)) {
            continue;
        }
        $fn($el);
        if (!empty($el['elements']) && is_array($el['elements'])) {
            iius_elementor_walk_patch($el['elements'], $fn);
        }
    }
}

function iius_patch_coaching_page_208() {
    $pid = 208;
    $raw = get_post_meta($pid, '_elementor_data', true);
    if (!is_string($raw) || $raw === '') {
        echo "skip 208: no elementor\n";
        return;
    }
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        echo "skip 208: json invalid\n";
        return;
    }

    $inserted_vitrina = false;
    $patched = false;

    iius_elementor_walk_patch(
        $data,
        static function (&$el) use (&$inserted_vitrina, &$patched) {
            if (($el['widgetType'] ?? '') !== 'heading') {
                return;
            }
            $title = isset($el['settings']['title']) ? (string) $el['settings']['title'] : '';
            if ($title === 'Agendar Coaching Online') {
                $el['settings']['title'] = 'Inscribirse en Coaching';
                $patched = true;
            }
            if ($title === 'Agendar Coaching Online' || ($el['settings']['title'] ?? '') === 'Inscribirse en Coaching') {
                // handled above
            }
        }
    );

    // Segunda pasada: textos e inyectar vitrina tras «Inscribirse en Coaching»
    $pending_vitrina_after = false;
    iius_elementor_walk_patch(
        $data,
        static function (&$el) use (&$pending_vitrina_after, &$inserted_vitrina, &$patched) {
            if (($el['widgetType'] ?? '') === 'heading') {
                $t = isset($el['settings']['title']) ? trim((string) $el['settings']['title']) : '';
                $pending_vitrina_after = ($t === 'Inscribirse en Coaching');
                return;
            }
            if ($pending_vitrina_after && ($el['widgetType'] ?? '') === 'text-editor' && !$inserted_vitrina) {
                $el['settings']['editor'] = '<p>Compra en nuestra plataforma segura. Si tu coaching incluye sesiones, después del pago elegirás fecha y hora en línea.</p>';
                $el['widgetType'] = 'shortcode';
                unset($el['settings']['editor']);
                $el['settings']['shortcode'] = '[iius_coaching_en1_vitrina]';
                $inserted_vitrina = true;
                $patched = true;
                $pending_vitrina_after = false;
                return;
            }
            if (($el['widgetType'] ?? '') === 'text-editor') {
                $ed = isset($el['settings']['editor']) ? (string) $el['settings']['editor'] : '';
                if (strpos($ed, 'Reserva tu sesión de coaching') !== false) {
                    $el['settings']['editor'] = '<p>Programas de coaching con inscripción y pago en línea. Las sesiones con agenda se reservan en la plataforma después del pago.</p>';
                    $patched = true;
                }
            }
        }
    );

    iius_elementor_walk_patch(
        $data,
        static function (&$el) use (&$patched) {
            if (($el['widgetType'] ?? '') === 'shortcode') {
                $sc = isset($el['settings']['shortcode']) ? (string) $el['settings']['shortcode'] : '';
                if ($sc === '[iius_diplomados_calendario]') {
                    // mantener solo diplomados (vitrina ya está arriba)
                    $patched = true;
                }
            }
        }
    );

    if (!$patched) {
        echo "unchanged 208\n";
        return;
    }

    update_post_meta($pid, '_elementor_data', wp_slash(wp_json_encode($data)));
    echo "patched 208 (vitrina=" . ($inserted_vitrina ? 'yes' : 'no') . ")\n";
}

function iius_patch_home_32() {
    $pid = 32;
    $raw = get_post_meta($pid, '_elementor_data', true);
    if (!is_string($raw) || $raw === '') {
        echo "skip 32\n";
        return;
    }
    $apps = 'https://apps.internationalinstitute.us/coaching';
    $new = str_replace(
        array('"url":"\\/coaching\\/"', '"url":"/coaching/"', 'Explorar Coaching'),
        array('"url":"' . $apps . '"', '"url":"' . $apps . '"', 'Ver coaching en Apps'),
        $raw
    );
    if ($new === $raw) {
        echo "unchanged 32\n";
        return;
    }
    update_post_meta($pid, '_elementor_data', wp_slash($new));
    echo "patched 32\n";
}

iius_patch_coaching_page_208();
iius_patch_home_32();

foreach (array(208, 32) as $pid) {
    if (class_exists('\Elementor\Plugin')) {
        try {
            \Elementor\Plugin::$instance->posts_css_manager->clear_cache();
        } catch (Exception $e) {
            // ignore
        }
    }
    delete_post_meta($pid, '_elementor_css');
}

echo "done\n";

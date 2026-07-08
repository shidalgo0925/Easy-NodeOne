<?php
/**
 * Plugin Name: IIUS Coaching EN1 (vitrina + landing sync)
 * Description: [iius_coaching_en1_vitrina] y [iius_coaching_landing_sync] — compra en Apps; agenda post-pago en EN1.
 * Version: 1.0.0
 */
if (!defined('ABSPATH')) {
    exit;
}

const IIUS_COACHING_EN1_APPS_BASE = 'https://apps.internationalinstitute.us';

function iius_coaching_en1_apps_base() {
    $url = get_option('iius_coaching_en1_apps_base', '');
    if ($url === '') {
        $url = IIUS_COACHING_EN1_APPS_BASE;
    }
    return rtrim(apply_filters('iius_coaching_en1_apps_base', $url), '/');
}

/**
 * Catálogo coaching publicado en EN1 (slugs canónicos).
 *
 * @return array<int, array{slug:string,name:string,note:string}>
 */
function iius_coaching_en1_programs() {
    return array(
        array('slug' => 'coaching-de-vida', 'name' => 'Coaching de vida', 'note' => ''),
        array('slug' => 'coaching-espiritual-y-de-proposito', 'name' => 'Coaching espiritual y de propósito', 'note' => ''),
        array('slug' => 'coaching-familiar', 'name' => 'Coaching familiar', 'note' => ''),
        array('slug' => 'coaching-financiero', 'name' => 'Coaching financiero', 'note' => ''),
        array('slug' => 'coaching-individual', 'name' => 'Coaching individual', 'note' => 'Incluye agenda tras el pago'),
        array('slug' => 'coaching-ejecutivo', 'name' => 'Coaching ejecutivo', 'note' => 'Incluye agenda tras el pago'),
        array('slug' => 'coaching-organizacional-empresarial', 'name' => 'Coaching organizacional empresarial', 'note' => ''),
    );
}

add_shortcode('iius_coaching_en1_vitrina', 'iius_coaching_en1_vitrina_shortcode');

function iius_coaching_en1_vitrina_shortcode($atts) {
    $atts = shortcode_atts(
        array('apps' => iius_coaching_en1_apps_base()),
        $atts,
        'iius_coaching_en1_vitrina'
    );
    $base = esc_url_raw($atts['apps']);
    if (!$base) {
        return '';
    }

    static $css_done = false;
    ob_start();
    if (!$css_done) {
        $css_done = true;
        ?>
<style>
.iius-coach-grid{display:grid;gap:1rem;grid-template-columns:1fr;margin:1rem 0 1.5rem}
@media(min-width:600px){.iius-coach-grid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:900px){.iius-coach-grid{grid-template-columns:repeat(3,1fr)}}
.iius-coach-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:1rem 1.1rem;display:flex;flex-direction:column;height:100%;box-shadow:0 4px 16px rgba(0,4,45,.06)}
.iius-coach-card h3{font-size:1rem;font-weight:700;color:#00042D;margin:0 0 .45rem;line-height:1.35}
.iius-coach-card p{font-size:.82rem;color:#6b7280;margin:0 0 .85rem;flex:1}
.iius-coach-card a{display:inline-block;text-align:center;padding:.55rem 1rem;border-radius:999px;background:#8B60AA;color:#fff!important;font-weight:700;font-size:.82rem;text-decoration:none}
.iius-coach-card a:hover{background:#00042D;color:#fff!important}
.iius-coach-lead{font-size:.95rem;color:#4b5563;max-width:52rem;line-height:1.5;margin-bottom:.5rem}
.iius-coach-all{margin:0 0 1rem}
.iius-coach-all a{font-weight:700;color:#8B60AA}
</style>
        <?php
    }
    ?>
<p class="iius-coach-lead">Compra tu programa en nuestra plataforma segura. Si el coaching incluye sesiones, después del pago podrás elegir fecha y hora en línea (Google Calendar).</p>
<p class="iius-coach-all"><a href="<?php echo esc_url($base . '/coaching'); ?>" target="_blank" rel="noopener noreferrer">Ver catálogo completo en Apps →</a></p>
<div class="iius-coach-grid">
<?php foreach (iius_coaching_en1_programs() as $prog) :
    $url = $base . '/inscripcion/' . rawurlencode($prog['slug']);
    ?>
    <article class="iius-coach-card">
        <h3><?php echo esc_html($prog['name']); ?></h3>
        <?php if ($prog['note'] !== '') : ?>
        <p><?php echo esc_html($prog['note']); ?></p>
        <?php else : ?>
        <p>Inscripción y pago en línea.</p>
        <?php endif; ?>
        <a href="<?php echo esc_url($url); ?>" target="_blank" rel="noopener noreferrer">Inscribirme</a>
    </article>
<?php endforeach; ?>
</div>
    <?php
    return ob_get_clean();
}

add_shortcode('iius_coaching_landing_sync', 'iius_coaching_landing_sync_shortcode');

function iius_coaching_landing_sync_shortcode($atts) {
    $out = do_shortcode('[iius_coaching_en1_vitrina]');
    $out .= '<h2 class="iius-coach-dipl-heading" style="font-size:1.25rem;font-weight:700;color:#00042D;margin:2rem 0 .75rem;">Calendario de inicios — Diplomados IIUS</h2>';
    $out .= do_shortcode('[iius_diplomados_calendario]');
    return $out;
}

add_action('admin_init', 'iius_coaching_en1_register_settings');

function iius_coaching_en1_register_settings() {
    register_setting(
        'iius_coaching_en1_group',
        'iius_coaching_en1_apps_base',
        array(
            'type'              => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default'           => IIUS_COACHING_EN1_APPS_BASE,
        )
    );
    if (get_option('iius_coaching_en1_apps_base', '') === '') {
        update_option('iius_coaching_en1_apps_base', IIUS_COACHING_EN1_APPS_BASE, false);
    }
}

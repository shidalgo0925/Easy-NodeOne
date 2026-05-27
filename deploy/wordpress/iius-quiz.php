<?php
/**
 * Plugin Name: IIUS Quiz de orientación
 * Description: Shortcode [iius_quiz] — flujo tipo Strawberry (roadmap, pastillas, rueda de vida, resultado).
 * Version: 2.2.0
 */
if (!defined('ABSPATH')) {
    exit;
}

add_shortcode('iius_quiz', 'iius_quiz_shortcode');

/**
 * Bloque editorial superior (literales) — no altera la lógica del quiz.
 */
function iius_quiz_hero_markup() {
    $u_coaching = esc_url(home_url('/coaching/'));
    $u_contact  = esc_url(home_url('/contact/'));
    ob_start();
    ?>
<section class="iius-quiz-hero" aria-label="<?php echo esc_attr__('Información sobre coaching IIUS', 'iius-quiz'); ?>">
  <header class="iius-quiz-hero__head">
    <h2 class="iius-quiz-hero__title"><?php echo esc_html__('¿Por qué elegir el coaching?', 'iius-quiz'); ?></h2>
    <p class="iius-quiz-hero__lead"><?php echo esc_html__('Tanto si buscas un cambio, quieres crecer más rápido, te sientes estancado o enfrentas una gran decisión — un coach personal te ayuda a ganar claridad, construir confianza, superar obstáculos, establecer metas y pasar a la acción.', 'iius-quiz'); ?></p>
    <p class="iius-quiz-hero__tagline"><?php echo esc_html__('Claridad · Impulso · Progreso', 'iius-quiz'); ?></p>
  </header>

  <figure class="iius-quiz-hero__quote">
    <blockquote>
      <p><?php echo esc_html__('Si estás en un momento de tu vida donde sabes que necesitas hacer cambios pero no sabes por dónde empezar, te recomiendo totalmente el coaching personal para alcanzar nuevas metas en tu carrera y vida personal.', 'iius-quiz'); ?></p>
    </blockquote>
    <figcaption class="iius-quiz-hero__cite"><?php echo esc_html__('— Alisha W.', 'iius-quiz'); ?></figcaption>
  </figure>

  <div class="iius-quiz-hero__block">
    <h3 class="iius-quiz-hero__h3"><?php echo esc_html__('Claridad en días, no en meses', 'iius-quiz'); ?></h3>
    <ul class="iius-quiz-hero__list">
      <li><?php echo esc_html__('Deja de esperar una epifanía', 'iius-quiz'); ?></li>
      <li><?php echo esc_html__('Corta el ruido y descubre lo que realmente quieres', 'iius-quiz'); ?></li>
      <li><?php echo esc_html__('Haz las preguntas que has estado evitando', 'iius-quiz'); ?></li>
      <li><?php echo esc_html__('Sal de tu primera sesión con un panorama más claro, no con más confusión', 'iius-quiz'); ?></li>
    </ul>
    <a class="iius-quiz-hero__cta" href="#iius-quiz-start"><?php echo esc_html__('Obtén claridad ahora', 'iius-quiz'); ?></a>
  </div>

  <div class="iius-quiz-hero__block">
    <h3 class="iius-quiz-hero__h3"><?php echo esc_html__('Coaches profesionales de alto nivel, comprometidos con tu crecimiento', 'iius-quiz'); ?></h3>
    <ul class="iius-quiz-hero__list iius-quiz-hero__list--checks">
      <li><strong><?php echo esc_html__('Evaluación rigurosa', 'iius-quiz'); ?></strong> — <?php echo esc_html__('valorados por su formación, entrenamiento y experiencia en coaching', 'iius-quiz'); ?></li>
      <li><strong><?php echo esc_html__('Experiencia real', 'iius-quiz'); ?></strong> — <?php echo esc_html__('más de 16 años de experiencia en más de 37 industrias y 900 empresas', 'iius-quiz'); ?></li>
      <li><strong><?php echo esc_html__('Trayectoria comprobada', 'iius-quiz'); ?></strong> — <?php echo esc_html__('mediante evaluaciones continuas con retroalimentación de clientes, métricas de desempeño y evaluaciones de calidad', 'iius-quiz'); ?></li>
      <li><strong><?php echo esc_html__('Profesionales de confianza', 'iius-quiz'); ?></strong> — <?php echo esc_html__('comprometidos con un estricto Código de Ética que garantiza conducta profesional, confidencialidad y prevención de conflictos de interés', 'iius-quiz'); ?></li>
    </ul>
    <p class="iius-quiz-hero__links">
      <a class="iius-quiz-hero__link" href="<?php echo esc_url($u_coaching); ?>"><?php echo esc_html__('Conoce a mi coach', 'iius-quiz'); ?></a>
    </p>
    <p class="iius-quiz-hero__coach-cta"><?php echo esc_html__('¿Eres un coach certificado interesado en unirte a nuestra red?', 'iius-quiz'); ?> <a href="<?php echo esc_url($u_contact); ?>"><?php echo esc_html__('Aplica aquí.', 'iius-quiz'); ?></a></p>
  </div>

  <div class="iius-quiz-hero__block">
    <h3 class="iius-quiz-hero__h3"><?php echo esc_html__('Cómo funciona', 'iius-quiz'); ?></h3>
    <ol class="iius-quiz-hero__steps">
      <li>
        <span class="iius-quiz-hero__step-num">1</span>
        <div>
          <strong><?php echo esc_html__('Encuentra al coach ideal para ti', 'iius-quiz'); ?></strong>
          <p><?php echo esc_html__('Responde un quiz para definir tus áreas de enfoque, metas deseadas y preferencias personales. Te conectaremos con el coach ideal de un grupo diverso de coaches profesionales de alto nivel.', 'iius-quiz'); ?></p>
        </div>
      </li>
      <li>
        <span class="iius-quiz-hero__step-num">2</span>
        <div>
          <strong><?php echo esc_html__('Coaching que se adapta a tu vida', 'iius-quiz'); ?></strong>
          <p><?php echo esc_html__('El coaching en IIUS está diseñado para ser cómodo y flexible. Reúnete con tu coach desde cualquier lugar a través de videosesiones. Mantente conectado entre sesiones mediante mensajería para compartir avances y recibir apoyo continuo.', 'iius-quiz'); ?></p>
        </div>
      </li>
      <li>
        <span class="iius-quiz-hero__step-num">3</span>
        <div>
          <strong><?php echo esc_html__('Gana claridad, crea un plan y mantente acompañado', 'iius-quiz'); ?></strong>
          <p><?php echo esc_html__('Trabaja 1 a 1 con tu coach para profundizar en tus aspiraciones y desafíos, y desbloquear perspectivas valiosas. Recibe orientación continua y accountability para superar obstáculos, mantenerte en curso y lograr avances reales.', 'iius-quiz'); ?></p>
        </div>
      </li>
    </ol>
    <a class="iius-quiz-hero__cta" href="#iius-quiz-start"><?php echo esc_html__('Tomar el quiz', 'iius-quiz'); ?></a>
  </div>

  <div class="iius-quiz-hero__block">
    <h3 class="iius-quiz-hero__h3"><?php echo esc_html__('¿Qué nos hace diferentes?', 'iius-quiz'); ?></h3>
    <p class="iius-quiz-hero__lead iius-quiz-hero__lead--tight"><?php echo esc_html__('Con IIUS obtienes un match personalizado con tu coach según tus metas, acompañamiento continuo entre sesiones y la flexibilidad de cancelar cuando quieras.', 'iius-quiz'); ?></p>
    <div class="iius-quiz-hero__table-wrap" role="region" aria-label="<?php echo esc_attr__('Comparación IIUS y práctica privada', 'iius-quiz'); ?>">
      <table class="iius-quiz-hero__table">
        <thead>
          <tr>
            <th scope="col"></th>
            <th scope="col"><?php echo esc_html__('IIUS', 'iius-quiz'); ?></th>
            <th scope="col"><?php echo esc_html__('Práctica privada', 'iius-quiz'); ?></th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row"><?php echo esc_html__('Match personalizado con coach', 'iius-quiz'); ?></th>
            <td class="iius-quiz-hero__ok"><?php echo esc_html__('✓', 'iius-quiz'); ?></td>
            <td><?php echo esc_html__('—', 'iius-quiz'); ?></td>
          </tr>
          <tr>
            <th scope="row"><?php echo esc_html__('Sesiones de video 1 a 1', 'iius-quiz'); ?></th>
            <td class="iius-quiz-hero__ok"><?php echo esc_html__('✓', 'iius-quiz'); ?></td>
            <td class="iius-quiz-hero__ok"><?php echo esc_html__('✓', 'iius-quiz'); ?></td>
          </tr>
          <tr>
            <th scope="row"><?php echo esc_html__('Mensajes a tu coach en cualquier momento', 'iius-quiz'); ?></th>
            <td class="iius-quiz-hero__ok"><?php echo esc_html__('✓', 'iius-quiz'); ?></td>
            <td><?php echo esc_html__('Variable', 'iius-quiz'); ?></td>
          </tr>
          <tr>
            <th scope="row"><?php echo esc_html__('Ejercicios entre sesiones', 'iius-quiz'); ?></th>
            <td class="iius-quiz-hero__ok"><?php echo esc_html__('✓', 'iius-quiz'); ?></td>
            <td><?php echo esc_html__('Variable', 'iius-quiz'); ?></td>
          </tr>
          <tr>
            <th scope="row"><?php echo esc_html__('Cancela cuando quieras', 'iius-quiz'); ?></th>
            <td class="iius-quiz-hero__ok"><?php echo esc_html__('✓', 'iius-quiz'); ?></td>
            <td><?php echo esc_html__('Variable', 'iius-quiz'); ?></td>
          </tr>
          <tr>
            <th scope="row"><?php echo esc_html__('Compromiso inicial requerido', 'iius-quiz'); ?></th>
            <td><?php echo esc_html__('No', 'iius-quiz'); ?></td>
            <td><?php echo esc_html__('Sí', 'iius-quiz'); ?></td>
          </tr>
        </tbody>
      </table>
    </div>
    <a class="iius-quiz-hero__cta" href="#iius-quiz-start"><?php echo esc_html__('Comenzar', 'iius-quiz'); ?></a>
  </div>

  <p class="iius-quiz-hero__disclaimer"><?php echo esc_html__('IIUS no facilita servicios de salud. Si bien algunos coaches pueden ser también profesionales de la salud, no actúan en esa capacidad dentro de IIUS. Los coaches no ofrecen diagnósticos, tratamientos, prescripción de medicamentos ni ningún otro servicio clínico. Para trastornos o preocupaciones de salud mental, por favor busca ayuda de un psicoterapeuta o psiquiatra con licencia.', 'iius-quiz'); ?></p>
</section>
    <?php
    return ob_get_clean();
}

function iius_quiz_shortcode($atts) {
    $chart_cdn = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
    ob_start();
    ?>
<div class="iius-quiz-page">
<?php echo iius_quiz_hero_markup(); ?>
<div class="iius-sb" id="iius-sb-root" data-base-url="<?php echo esc_url(home_url('/')); ?>">
  <span id="iius-quiz-start" class="iius-quiz-anchor" tabindex="-1"></span>
  <div class="iius-sb__progress-track">
    <div class="iius-sb__progress-fill" id="iius-sb-progress" style="width:4%"></div>
    <span class="iius-sb__progress-icon" id="iius-sb-fruit" aria-hidden="true">🎓</span>
  </div>
  <h1 class="iius-sb__site-title">Encontrá tu acompañamiento en IIUS</h1>
  <div class="iius-sb__card">
    <button type="button" class="iius-sb__back" id="iius-sb-back" aria-label="Volver" hidden>←</button>
    <div id="iius-sb-view"></div>
  </div>
</div>
</div>
<script src="<?php echo esc_url($chart_cdn); ?>"></script>
<style><?php echo iius_sb_css(); ?></style>
<script><?php echo iius_sb_js(); ?></script>
    <?php
    return ob_get_clean();
}

function iius_sb_css() {
    return <<<'CSS'
.iius-quiz-page{--iius-navy:#00042D;--iius-violet:#8B60AA;--iius-gold:#E6BF75;--iius-bg:#f5f7fb;--iius-text:#374151;--iius-muted:#6b7280;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background:var(--iius-bg);padding:1rem .75rem 3rem;margin:0 auto;max-width:720px;}
.iius-quiz-anchor{display:block;height:0;overflow:hidden;scroll-margin-top:88px;}
.iius-quiz-hero{color:var(--iius-navy);padding-bottom:.5rem;margin-bottom:1.25rem;}
.iius-quiz-hero__title{font-size:1.35rem;font-weight:800;line-height:1.25;margin:0 0 .75rem;color:var(--iius-navy);}
.iius-quiz-hero__lead{font-size:.95rem;line-height:1.6;margin:0 0 .75rem;color:var(--iius-text);}
.iius-quiz-hero__lead--tight{margin-top:.25rem;}
.iius-quiz-hero__tagline{font-size:.85rem;font-weight:700;letter-spacing:.04em;color:var(--iius-violet);margin:0 0 1.25rem;}
.iius-quiz-hero__quote{margin:0 0 1.25rem;padding:0;border:none;border-left:3px solid var(--iius-gold);padding-left:.85rem;}
.iius-quiz-hero__quote blockquote{margin:0;padding:0;border:none;font-size:.95rem;line-height:1.55;color:var(--iius-text);}
.iius-quiz-hero__quote blockquote p{margin:0;}
.iius-quiz-hero__cite{margin:.5rem 0 0;font-size:.88rem;font-style:normal;color:var(--iius-muted);}
.iius-quiz-hero__block{background:#fff;border-radius:14px;box-shadow:0 8px 28px rgba(0,4,45,.08);padding:1.1rem 1rem 1.25rem;margin-bottom:1rem;border:1px solid #e8eaf0;}
.iius-quiz-hero__h3{font-size:1.02rem;font-weight:700;margin:0 0 .65rem;line-height:1.35;color:var(--iius-navy);}
.iius-quiz-hero__list{margin:.5rem 0 1rem;padding-left:1.15rem;font-size:.9rem;line-height:1.5;color:var(--iius-text);}
.iius-quiz-hero__list--checks{padding-left:1rem;list-style:disc;}
.iius-quiz-hero__list li{margin-bottom:.35rem;}
.iius-quiz-hero__cta{display:inline-block;width:100%;text-align:center;padding:.85rem 1rem;border-radius:999px;background:var(--iius-violet);color:#fff!important;font-weight:700;font-size:.92rem;text-decoration:none;margin-top:.25rem;box-sizing:border-box;}
.iius-quiz-hero__cta:hover{background:var(--iius-navy);}
.iius-quiz-hero__links{margin:.75rem 0 0;}
.iius-quiz-hero__link{color:var(--iius-violet)!important;font-weight:700;text-decoration:underline;font-size:.92rem;}
.iius-quiz-hero__link:hover{color:var(--iius-navy)!important;}
.iius-quiz-hero__coach-cta{font-size:.88rem;line-height:1.5;color:var(--iius-text);margin:.75rem 0 0;}
.iius-quiz-hero__coach-cta a{color:var(--iius-violet)!important;font-weight:600;}
.iius-quiz-hero__coach-cta a:hover{color:var(--iius-navy)!important;}
.iius-quiz-hero__steps{list-style:none;margin:0;padding:0;counter-reset:iiusstep;}
.iius-quiz-hero__steps li{display:flex;gap:.75rem;margin-bottom:1rem;align-items:flex-start;}
.iius-quiz-hero__step-num{flex-shrink:0;width:1.75rem;height:1.75rem;border-radius:50%;background:var(--iius-navy);color:#fff;font-weight:800;font-size:.85rem;display:flex;align-items:center;justify-content:center;line-height:1;}
.iius-quiz-hero__steps strong{display:block;font-size:.92rem;margin-bottom:.25rem;color:var(--iius-navy);}
.iius-quiz-hero__steps p{margin:0;font-size:.88rem;line-height:1.5;color:var(--iius-text);}
.iius-quiz-hero__table-wrap{overflow-x:auto;margin:.75rem 0 1rem;-webkit-overflow-scrolling:touch;}
.iius-quiz-hero__table{width:100%;min-width:280px;border-collapse:collapse;font-size:.78rem;}
.iius-quiz-hero__table th,.iius-quiz-hero__table td{padding:.5rem .4rem;text-align:center;border-bottom:1px solid #e5e7eb;vertical-align:middle;}
.iius-quiz-hero__table thead th{background:var(--iius-bg);font-weight:700;color:var(--iius-navy);}
.iius-quiz-hero__table tbody th[scope="row"]{text-align:left;font-weight:600;color:var(--iius-text);max-width:42%;}
.iius-quiz-hero__ok{color:var(--iius-violet);font-weight:700;}
.iius-quiz-hero__disclaimer{font-size:.72rem;line-height:1.5;color:var(--iius-muted);margin:1.25rem 0 0;padding-top:1rem;border-top:1px solid #e5e7eb;}
.iius-sb{font-family:inherit;background:transparent;min-height:60vh;padding:0 0 1rem;margin:0 auto;max-width:520px;}
.iius-sb__progress-track{position:relative;height:4px;background:#e5e7eb;border-radius:99px;margin:0 auto 1rem;max-width:100%;}
.iius-sb__progress-fill{height:100%;background:linear-gradient(90deg,var(--iius-navy),var(--iius-violet));border-radius:99px;transition:width .35s ease;}
.iius-sb__progress-icon{position:absolute;top:50%;left:var(--iius-pct,4%);transform:translate(-50%,-50%);font-size:1.1rem;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.15));transition:left .35s ease;}
.iius-sb__site-title{text-align:center;font-size:1.05rem;font-weight:700;color:var(--iius-navy);margin:0 0 1.25rem;line-height:1.35;padding:0 .5rem;}
.iius-sb__card{background:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(0,4,45,.1);padding:1.1rem 1rem 1.5rem;position:relative;min-height:280px;border:1px solid #e8eaf0;}
.iius-sb__back{position:absolute;top:12px;left:12px;background:none;border:none;font-size:1.35rem;line-height:1;cursor:pointer;color:var(--iius-navy);padding:.25rem;z-index:2;}
.iius-sb__back:hover{color:var(--iius-violet);}
.iius-sb__back[hidden]{display:none!important;}
.iius-sb h2.iius-sb__q{font-size:1.05rem;font-weight:700;color:var(--iius-navy);margin:2rem 0 .75rem;line-height:1.35;}
.iius-sb__hint{font-size:.82rem;color:var(--iius-muted);margin:-0.25rem 0 1rem;line-height:1.45;}
.iius-sb__pills{display:flex;flex-direction:column;gap:.55rem;}
.iius-sb__pill{display:block;width:100%;padding:.85rem 1rem;border:none;border-radius:999px;background:var(--iius-violet);color:#fff!important;font-weight:600;font-size:.9rem;text-align:left;cursor:pointer;transition:background .15s,transform .1s;font:inherit;}
.iius-sb__pill:hover{background:var(--iius-navy);}
.iius-sb__pill:active{transform:scale(.99);}
.iius-sb__pill--outline{background:#fff;color:var(--iius-violet)!important;border:2px solid var(--iius-violet);}
.iius-sb__check-list{display:flex;flex-direction:column;gap:.45rem;margin-bottom:1rem;}
.iius-sb__check{display:flex;align-items:flex-start;gap:.6rem;padding:.65rem .75rem;border-radius:12px;background:var(--iius-bg);border:2px solid transparent;cursor:pointer;text-align:left;font:inherit;width:100%;}
.iius-sb__check.is-on{background:var(--iius-violet);color:#fff;border-color:var(--iius-violet);}
.iius-sb__check.is-on .iius-sb__check-box{border-color:#fff;color:#fff;}
.iius-sb__check-box{flex-shrink:0;width:1.1rem;height:1.1rem;border:2px solid #9ca3af;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:.7rem;}
.iius-sb__check-text{font-size:.88rem;line-height:1.35;}
.iius-sb__btn-next{display:block;width:100%;padding:.9rem;border:none;border-radius:999px;background:var(--iius-violet);color:#fff;font-weight:700;font-size:.95rem;cursor:pointer;margin-top:.5rem;font:inherit;}
.iius-sb__btn-next:hover{background:var(--iius-navy);}
.iius-sb__btn-next:disabled{opacity:.45;cursor:not-allowed;}
.iius-sb__skip{display:block;text-align:center;margin-top:.75rem;color:var(--iius-violet);font-size:.85rem;text-decoration:underline;cursor:pointer;background:none;border:none;width:100%;font:inherit;}
.iius-sb__skip:hover{color:var(--iius-navy);}
.iius-sb__stepper{list-style:none;margin:0;padding:0 0 0 .25rem;}
.iius-sb__step{display:flex;align-items:flex-start;gap:.65rem;padding:.55rem .4rem;border-radius:10px;margin-bottom:.15rem;position:relative;}
.iius-sb__step.is-active{background:rgba(139,96,170,.12);}
.iius-sb__step-dot{width:22px;height:22px;border-radius:50%;border:2px solid var(--iius-violet);flex-shrink:0;margin-top:2px;background:#fff;display:flex;align-items:center;justify-content:center;font-size:.65rem;}
.iius-sb__step.done .iius-sb__step-dot{background:var(--iius-violet);color:#fff;border-color:var(--iius-violet);}
.iius-sb__step-body{flex:1;display:flex;justify-content:space-between;align-items:baseline;gap:.5rem;}
.iius-sb__step-title{font-weight:600;font-size:.88rem;color:var(--iius-navy);}
.iius-sb__step-time{font-size:.72rem;color:var(--iius-muted);white-space:nowrap;}
.iius-sb__step-line{position:absolute;left:12px;top:28px;bottom:-8px;width:2px;background:#e5e7eb;}
.iius-sb__step.done + .iius-sb__step .iius-sb__step-line,.iius-sb__step:last-child .iius-sb__step-line{display:none;}
.iius-sb__rate-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.35rem;margin:1rem 0;}
@media(min-width:400px){.iius-sb__rate-grid{grid-template-columns:repeat(5,1fr);max-width:340px;margin-left:auto;margin-right:auto;}}
.iius-sb__rate-btn{padding:.55rem 0;border:2px solid rgba(139,96,170,.45);border-radius:10px;background:#fff;color:var(--iius-navy);font-weight:700;font-size:.9rem;cursor:pointer;font:inherit;}
.iius-sb__rate-btn.is-sel{background:var(--iius-violet);color:#fff;border-color:var(--iius-violet);}
.iius-sb__wheel-wrap{position:relative;height:220px;margin:1rem auto;max-width:280px;}
.iius-sb__cat-tag{display:inline-block;padding:.15rem .45rem;border-radius:6px;font-size:.78rem;font-weight:700;margin-bottom:.5rem;background:rgba(139,96,170,.15);color:var(--iius-navy);}
.iius-sb__result-score{font-size:2.4rem;font-weight:800;color:var(--iius-violet);margin:.25rem 0 .5rem;}
.iius-sb__result-lead{font-size:.95rem;color:var(--iius-text);line-height:1.55;margin:0 0 .75rem;}
.iius-sb__result-list{margin:0 0 1rem;padding-left:1.1rem;color:var(--iius-text);font-size:.9rem;line-height:1.5;}
.iius-sb__result-actions{display:flex;flex-wrap:wrap;gap:.5rem;}
.iius-sb__result-actions a{display:inline-block;padding:.55rem .9rem;border-radius:999px;background:var(--iius-navy);color:#fff!important;text-decoration:none;font-weight:600;font-size:.82rem;}
.iius-sb__result-actions a:hover{background:var(--iius-violet);}
.iius-sb__result-actions a.sec{background:#fff;color:var(--iius-violet)!important;border:2px solid var(--iius-violet);}
.iius-sb__result-actions a.sec:hover{background:var(--iius-bg);}
CSS;
}

function iius_sb_js() {
    return <<<'JS'
(function(){
var baseEl = document.getElementById("iius-sb-root");
if (!baseEl) return;
var BASE = (baseEl.getAttribute("data-base-url") || "/").replace(/\/?$/, "/");
var view = document.getElementById("iius-sb-view");
var backBtn = document.getElementById("iius-sb-back");
var progressEl = document.getElementById("iius-sb-progress");
var fruit = document.getElementById("iius-sb-fruit");

var state = {
  step: 0,
  age: null,
  gender: null,
  situation: null,
  wheel: {},
  wheelKeys: [
    { key: "carrera", label: "Carrera", color: "rgba(0,4,45,0.88)" },
    { key: "bienestar", label: "Bienestar y autocuidado", color: "rgba(139,96,170,0.88)" },
    { key: "familia", label: "Familia y amigos", color: "rgba(230,191,117,0.92)" },
    { key: "proposito", label: "Propósito y sentido", color: "rgba(0,4,45,0.65)" },
    { key: "enfoque", label: "Enfoque y productividad", color: "rgba(139,96,170,0.65)" },
    { key: "confianza", label: "Confianza y autoestima", color: "rgba(230,191,117,0.75)" }
  ],
  wheelIdx: 0,
  obstacles: [],
  decision: null
};

var chartInstance = null;

function totalSteps() {
  return 1 + 1 + 1 + 1 + state.wheelKeys.length + 1 + 1 + 1;
}

function stepIndex() {
  var s = state.step;
  if (s === 0) return 1;
  if (s === 1) return 2;
  if (s === 2) return 3;
  if (s === 3) return 4;
  if (s >= 4 && s < 4 + state.wheelKeys.length) return 5 + (s - 4);
  if (s === 4 + state.wheelKeys.length) return 5 + state.wheelKeys.length;
  if (s === 5 + state.wheelKeys.length) return 6 + state.wheelKeys.length;
  return totalSteps();
}

function setProgress() {
  var t = totalSteps();
  var i = stepIndex();
  var pct = Math.min(96, Math.round((i / t) * 100));
  if (state.step > 4 + state.wheelKeys.length) pct = 96;
  if (progressEl) progressEl.style.width = pct + "%";
  if (fruit) fruit.style.setProperty("--iius-pct", pct + "%");
  if (fruit) fruit.style.left = pct + "%";
}

function esc(s) {
  var d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function render() {
  setProgress();
  if (backBtn) backBtn.hidden = state.step === 0;
  if (!view) return;

  if (state.step === 0) {
    view.innerHTML =
      "<h2 class=\"iius-sb__q\" style=\"margin-top:.5rem\">Tu recorrido</h2>" +
      "<p class=\"iius-sb__hint\">Como en un acompañamiento profesional: áreas de vida, metas, datos básicos y preferencias.</p>" +
      "<ol class=\"iius-sb__stepper\">" +
      stepRow("Mis áreas de vida", "2–3 min", true) +
      stepRow("Mis metas", "4–5 min", false) +
      stepRow("Sobre mí", "1 min", false) +
      stepRow("Preferencias", "1 min", false) +
      "<li class=\"iius-sb__step\"><span class=\"iius-sb__step-dot\">🎓</span><div class=\"iius-sb__step-body\"><span class=\"iius-sb__step-title\">Conectar con IIUS</span></div></li>" +
      "</ol>" +
      "<button type=\"button\" class=\"iius-sb__btn-next\" id=\"iius-sb-go\">Continuar</button>";
    document.getElementById("iius-sb-go").onclick = function() { state.step = 1; render(); };
    return;
  }

  if (state.step === 1) {
    view.innerHTML =
      "<h2 class=\"iius-sb__q\">¿Cuál es tu rango de edad?</h2>" +
      pills(["20–29", "30–39", "40–49", "50–59", "60–69", "70+", "Prefiero no decir"], "age");
    return;
  }

  if (state.step === 2) {
    view.innerHTML =
      "<h2 class=\"iius-sb__q\">¿Cómo te identificás?</h2>" +
      pills(["Hombre", "Mujer", "No binario", "Prefiero no decir", "Otra identidad"], "gender");
    return;
  }

  if (state.step === 3) {
    view.innerHTML =
      "<h2 class=\"iius-sb__q\">¿Qué describe mejor tu situación actual?</h2>" +
      pills(["Empleado/a", "Estudiante", "Emprendedor/a o freelance", "En transición laboral", "Jubilado/a", "Otro"], "situation");
    return;
  }

  if (state.step >= 4 && state.step < 4 + state.wheelKeys.length) {
    var wi = state.step - 4;
    var cat = state.wheelKeys[wi];
    var cur = state.wheel[cat.key] || null;
    var nums = [];
    for (var n = 1; n <= 10; n++) nums.push(n);
    view.innerHTML =
      "<p class=\"iius-sb__hint\" style=\"margin-top:.5rem\">Área " + (wi + 1) + " de " + state.wheelKeys.length + "</p>" +
      "<h2 class=\"iius-sb__q\">¿Cómo calificarías <span class=\"iius-sb__cat-tag\">" + esc(cat.label) + "</span> hoy?</h2>" +
      "<p class=\"iius-sb__hint\">1 = muy bajo · 10 = excelente</p>" +
      "<div class=\"iius-sb__rate-grid\" id=\"iius-rate-grid\"></div>" +
      "<div class=\"iius-sb__wheel-wrap\"><canvas id=\"iius-wheel-canvas\" aria-label=\"Rueda de vida\"></canvas></div>" +
      "<button type=\"button\" class=\"iius-sb__btn-next\" id=\"iius-wheel-next\" disabled>Siguiente</button>";
    var grid = document.getElementById("iius-rate-grid");
    nums.forEach(function(num) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "iius-sb__rate-btn" + (cur === num ? " is-sel" : "");
      b.textContent = num;
      b.onclick = function() {
        state.wheel[cat.key] = num;
        grid.querySelectorAll(".iius-sb__rate-btn").forEach(function(x) { x.classList.remove("is-sel"); });
        b.classList.add("is-sel");
        document.getElementById("iius-wheel-next").disabled = false;
        drawWheel();
      };
      grid.appendChild(b);
    });
    setTimeout(drawWheel, 0);
    document.getElementById("iius-wheel-next").onclick = function() {
      state.step++;
      render();
    };
    return;
  }

  if (state.step === 4 + state.wheelKeys.length) {
    view.innerHTML =
      "<h2 class=\"iius-sb__q\" style=\"margin-top:.5rem\">Tu rueda de vida</h2>" +
      "<p class=\"iius-sb__hint\">Así se ven tus prioridades hoy. Podés refinarlas después con un coach IIUS.</p>" +
      "<div class=\"iius-sb__wheel-wrap\" style=\"height:240px\"><canvas id=\"iius-wheel-canvas2\"></canvas></div>" +
      "<button type=\"button\" class=\"iius-sb__btn-next\" id=\"iius-after-wheel\">Continuar</button>";
    setTimeout(function() { drawWheelFull("iius-wheel-canvas2"); }, 50);
    document.getElementById("iius-after-wheel").onclick = function() { state.step++; render(); };
    return;
  }

  if (state.step === 5 + state.wheelKeys.length) {
    var opts = [
      "Falta de claridad o dirección",
      "Miedo al fracaso o al cambio",
      "Tiempo y prioridades",
      "Motivación o disciplina",
      "Personas o circunstancias externas",
      "Otro"
    ];
    view.innerHTML =
      "<h2 class=\"iius-sb__q\" style=\"margin-top:.5rem\">¿Qué sentís que más te frena?</h2>" +
      "<p class=\"iius-sb__hint\">Podés elegir varias opciones.</p>" +
      "<div class=\"iius-sb__check-list\" id=\"iius-obs\"></div>" +
      "<button type=\"button\" class=\"iius-sb__btn-next\" id=\"iius-obs-next\" disabled>Siguiente</button>";
    var obs = document.getElementById("iius-obs");
    opts.forEach(function(t, i) {
      var row = document.createElement("button");
      row.type = "button";
      row.className = "iius-sb__check" + (state.obstacles.indexOf(t) >= 0 ? " is-on" : "");
      row.innerHTML = "<span class=\"iius-sb__check-box\">" + (state.obstacles.indexOf(t) >= 0 ? "✓" : "") + "</span><span class=\"iius-sb__check-text\">" + esc(t) + "</span>";
      row.onclick = function() {
        var ix = state.obstacles.indexOf(t);
        if (ix >= 0) state.obstacles.splice(ix, 1); else state.obstacles.push(t);
        row.classList.toggle("is-on", state.obstacles.indexOf(t) >= 0);
        row.querySelector(".iius-sb__check-box").textContent = state.obstacles.indexOf(t) >= 0 ? "✓" : "";
        document.getElementById("iius-obs-next").disabled = state.obstacles.length === 0;
      };
      obs.appendChild(row);
    });
    document.getElementById("iius-obs-next").disabled = state.obstacles.length === 0;
    document.getElementById("iius-obs-next").onclick = function() { state.step++; render(); };
    return;
  }

  if (state.step === 6 + state.wheelKeys.length) {
    view.innerHTML =
      "<h2 class=\"iius-sb__q\">¿Cómo describirías tu forma de decidir?</h2>" +
      pills([
        { v: "lento", t: "A veces tardo más de lo que quisiera" },
        { v: "rapido", t: "A veces decido rápido sin analizar del todo" },
        { v: "balance", t: "Busco equilibrio según la decisión" }
      ], "decision");
    return;
  }

  resultView();
}

function stepRow(title, time, done) {
  return "<li class=\"iius-sb__step" + (done ? " done" : "") + "\"><span class=\"iius-sb__step-dot\">" + (done ? "✓" : "") + "</span><div class=\"iius-sb__step-body\"><span class=\"iius-sb__step-title\">" + esc(title) + "</span><span class=\"iius-sb__step-time\">" + esc(time) + "</span></div><span class=\"iius-sb__step-line\"></span></li>";
}

function pills(items, field) {
  var h = "<div class=\"iius-sb__pills\">";
  items.forEach(function(it) {
    var val = typeof it === "string" ? it : it.v;
    var txt = typeof it === "string" ? it : it.t;
    h += "<button type=\"button\" class=\"iius-sb__pill\" data-v=\"" + esc(val) + "\">" + esc(txt) + "</button>";
  });
  h += "</div>";
  setTimeout(function() {
    view.querySelectorAll(".iius-sb__pill").forEach(function(btn) {
      btn.onclick = function() {
        state[field] = btn.getAttribute("data-v");
        state.step++;
        render();
      };
    });
  }, 0);
  return h;
}

function drawWheel() {
  if (typeof Chart === "undefined") return;
  var wi = state.step - 4;
  var labels = [];
  var data = [];
  var colors = [];
  state.wheelKeys.forEach(function(k, i) {
    labels.push(k.label);
    var v = state.wheel[k.key];
    if (i < wi) {
      data.push(v || 0);
      colors.push(k.color);
    } else if (i === wi) {
      data.push(state.wheel[k.key] || 0);
      colors.push(k.color);
    } else {
      data.push(0);
      colors.push("rgba(229,231,235,0.6)");
    }
  });
  var ctx = document.getElementById("iius-wheel-canvas");
  if (!ctx) return;
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "polarArea",
    data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderWidth: 1 }] },
    options: {
      scales: { r: { min: 0, max: 10, ticks: { stepSize: 2 } } },
      plugins: { legend: { display: false } }
    }
  });
}

function drawWheelFull(canvasId) {
  if (typeof Chart === "undefined") return;
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;
  var labels = [];
  var data = [];
  var colors = [];
  state.wheelKeys.forEach(function(k) {
    labels.push(k.label);
    data.push(state.wheel[k.key] || 0);
    colors.push(k.color);
  });
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "polarArea",
    data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderWidth: 1 }] },
    options: {
      scales: { r: { min: 0, max: 10, ticks: { stepSize: 2 } } },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 9 } } } }
    }
  });
}

function hashScore() {
  var str = JSON.stringify({ age: state.age, gender: state.gender, situation: state.situation, wheel: state.wheel, obstacles: state.obstacles, decision: state.decision });
  var h = 0;
  for (var i = 0; i < str.length; i++) {
    h = ((h << 5) - h) + str.charCodeAt(i);
    h |= 0;
  }
  return 72 + (Math.abs(h) % 25);
}

function resultView() {
  var pct = hashScore();
  var avgWheel = 0, n = 0;
  state.wheelKeys.forEach(function(k) {
    if (state.wheel[k.key]) { avgWheel += state.wheel[k.key]; n++; }
  });
  avgWheel = n ? (avgWheel / n).toFixed(1) : "—";

  var lead = "Según tu rueda de vida y tus respuestas, tu perfil encaja con trayectos que combinan formación IIUS y acompañamiento práctico.";
  var benefits = [
    "Promedio en áreas clave: " + avgWheel + " / 10",
    state.obstacles.length ? "Focos a trabajar: " + state.obstacles.slice(0, 2).join(", ") : "Buen punto de partida para definir metas con claridad."
  ];

  view.innerHTML =
    "<h2 class=\"iius-sb__q\" style=\"margin-top:.5rem\">Tu recomendación</h2>" +
    "<div class=\"iius-sb__result-score\">" + pct + "% compatibilidad</div>" +
    "<p class=\"iius-sb__result-lead\">" + esc(lead) + "</p>" +
    "<ul class=\"iius-sb__result-list\">" + benefits.map(function(b) { return "<li>" + esc(b) + "</li>"; }).join("") + "</ul>" +
    "<div class=\"iius-sb__result-actions\">" +
    "<a href=\"" + BASE + "diplomados/\">Ver diplomados</a>" +
    "<a class=\"sec\" href=\"" + BASE + "entrenamientos/\">Entrenamientos</a>" +
    "<a class=\"sec\" href=\"" + BASE + "coaching/\">Coaching</a>" +
    "<a class=\"sec\" href=\"" + BASE + "contact/\">Contacto</a>" +
    "</div>" +
    "<button type=\"button\" class=\"iius-sb__skip\" id=\"iius-restart\">Reiniciar quiz</button>";

  document.getElementById("iius-restart").onclick = function() {
    state = {
      step: 0,
      age: null,
      gender: null,
      situation: null,
      wheel: {},
      wheelKeys: state.wheelKeys,
      wheelIdx: 0,
      obstacles: [],
      decision: null
    };
    if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
    render();
  };
  setProgress();
}

if (backBtn) backBtn.onclick = function() {
  if (state.step > 0) { state.step--; render(); }
};

render();
})();
JS;
}

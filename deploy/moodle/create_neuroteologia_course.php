<?php
/**
 * CLI: curso Moodle — Diplomado Neuro-Teología y Coaching Cristiano Transgeneracional.
 *
 * Copiar a MOODLEDIR/admin/cli/create_neuroteologia_course.php y ejecutar:
 *   sudo -u www-data php admin/cli/create_neuroteologia_course.php
 */
define('CLI_SCRIPT', true);

require(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->dirroot . '/course/lib.php');

cli_heading('IIUS — Neuro-Teología / Coaching Cristiano (crear curso)');

$shortname = 'IIUS-NEUROTEO-COACH-2026';
$existing = $DB->get_record('course', ['shortname' => $shortname], 'id,fullname', IGNORE_MISSING);
if ($existing) {
    cli_writeln("Ya existe curso id={$existing->id} shortname={$shortname}");
    exit(0);
}

$data = new stdClass();
$data->fullname = 'Diplomado Internacional en Neuro-Teología y Coaching Cristiano Transgeneracional';
$data->shortname = $shortname;
$data->category = 1;
$data->summary = '<p>Diez meses (220 h académicas + retiro opcional): neuro-teología, coaching cristiano, psicogenealogía bíblica, genosociograma, sanación transgeneracional, epigenética, perdón/adoración, PNL cristiana, protocolos integrados y práctica supervisada.</p>';
$data->summary_format = FORMAT_HTML;
$data->format = 'topics';
$data->numsections = 10;
$data->startdate = time();
$data->newsitems = 0;
$data->showgrades = 1;
$data->visible = 1;
$data->enablecompletion = 1;
$data->lang = 'es';

$course = create_course($data);
cli_writeln("Curso creado id={$course->id} shortname={$shortname}");

$titles = [
    'Módulo 1: Fundamentos de neuro-teología — el cerebro que cree',
    'Módulo 2: Coaching cristiano — fundamentos, ética y marco teológico',
    'Módulo 3: Psicogenealogía bíblica y patrones transgeneracionales en las Escrituras',
    'Módulo 4: Genosociograma cristiano y detección de patrones',
    'Módulo 5: Sanación transgeneracional — teología, protocolos y liberación genealógica',
    'Módulo 6: Neuroplasticidad, epigenética y transformación del linaje',
    'Módulo 7: Neurociencia del perdón, la gratitud y la adoración',
    'Módulo 8: PNL y coaching para sanación interior profunda',
    'Módulo 9: Protocolos integrados de neuro-coaching cristiano transgeneracional',
    'Módulo 10: Práctica supervisada, proyecto final y lanzamiento ministerial/profesional',
];

$summaries = [
    '<p>Neuro-teología, neuroanatomía de la experiencia espiritual, neuroquímica de la fe, Imago Dei, estados de conciencia en la Biblia. Perfil neuro-espiritual y cuestionario de experiencias.</p>',
    '<p>Coaching cristiano vs consejería/discipulado, ICF adaptado, GROW/OSCAR/CLEAR, ética, Espíritu Santo como paráclito. Contrato y código ético.</p>',
    '<p>Psicogenealogía y lectura bíblica, linajes, maldiciones vs bendiciones, Gálatas 3:13, genealogía de Jesús. Genosociograma de linaje bíblico.</p>',
    '<p>Genograma vs genosociograma cristiano, símbolos, 3–7 generaciones, lealtades, mandatos, secretos, fechas aniversario. Plantilla cristiana.</p>',
    '<p>Fundamentos teológicos, rituales bíblicos, oración de linaje, perdón a ancestros, bendiciones, renuncias. Protocolo de 7 pasos.</p>',
    '<p>Neuroplasticidad, epigenética, trauma transgeneracional, oración/meditación, trauma religioso, legado en Cristo. EPI-Faith.</p>',
    '<p>Correlatos del perdón y gratitud, adoración y DMN, perdón transgeneracional, Salmos. Protocolo 7 semanas y diario bíblico.</p>',
    '<p>PNL cristiana, VAKOG, anclajes, reimprinting, líneas de tiempo, creencias sobre Dios, niño interior. Protocolo de reimprinting cristiano.</p>',
    '<p>Sesión 90–120 min, algoritmo de intervención, ética pastoral, derivación, abreakciones, documentación. Plantillas y consentimiento.</p>',
    '<p>Cinco sesiones supervisadas, caso integrador, panel, plan ministerial, certificación, ética legal. Portafolio y video de filosofía.</p>',
];

for ($i = 1; $i <= 10; $i++) {
    $sec = $DB->get_record('course_sections', ['course' => $course->id, 'section' => $i], '*', IGNORE_MISSING);
    if (!$sec) {
        continue;
    }
    $sec->name = $titles[$i - 1];
    $sec->summary = $summaries[$i - 1];
    $sec->summaryformat = FORMAT_HTML;
    $DB->update_record('course_sections', $sec);
}

rebuild_course_cache($course->id, true);
cli_writeln('Secciones 1–10 actualizadas. rebuild_course_cache OK.');
exit(0);

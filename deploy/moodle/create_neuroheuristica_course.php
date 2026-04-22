<?php
/**
 * CLI: curso Moodle — Diplomado Neuro-Heurística™ y Coaching de Vida.
 *
 * Copiar a MOODLEDIR/admin/cli/create_neuroheuristica_course.php y ejecutar:
 *   sudo -u www-data php admin/cli/create_neuroheuristica_course.php
 */
define('CLI_SCRIPT', true);

require(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->dirroot . '/course/lib.php');

cli_heading('IIUS — Neuro-Heurística / Coaching de Vida (crear curso)');

$shortname = 'IIUS-NEUROHEUR-COACH-2026';
$existing = $DB->get_record('course', ['shortname' => $shortname], 'id,fullname', IGNORE_MISSING);
if ($existing) {
    cli_writeln("Ya existe curso id={$existing->id} shortname={$shortname}");
    exit(0);
}

$data = new stdClass();
$data->fullname = 'Diplomado Internacional en Neuro-Heurística™ y Coaching de Vida';
$data->shortname = $shortname;
$data->category = 1;
$data->summary = '<p>Diez meses (200 h + retiro opcional): Neuro-Heurística™, coaching ICF, objetivos neuro-compatibles, creencias, regulación emocional, decisiones y sesgos, hábitos, resiliencia, identidad/propósito, comunicación neuro-efectiva e integración profesional.</p>';
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
    'Módulo 1: Fundamentos de Neuro-Heurística™ y coaching',
    'Módulo 2: Arquitectura de objetivos neuro-compatible',
    'Módulo 3: Reprogramación de creencias limitantes y disfuncionales',
    'Módulo 4: Gestión emocional desde el cerebro',
    'Módulo 5: Toma de decisiones y heurísticas cognitivas',
    'Módulo 6: Hábitos, rutinas y neuro-automatización',
    'Módulo 7: Resiliencia neural y gestión del estrés',
    'Módulo 8: Identidad, propósito y neuro-alineación',
    'Módulo 9: Comunicación neuro-efectiva y rapport profundo',
    'Módulo 10: Integración, práctica supervisada y lanzamiento profesional',
];

$summaries = [
    '<p>Definición Neuro-Heurística™, neuroanatomía esencial, neuroplasticidad, SCARF, heurísticas, DMN y red ejecutiva, ética neuro-coach. Perfil neuro-cognitivo.</p>',
    '<p>Metas y dopamina, intención-acción, SMART neural, rueda de la vida, visualización, obstáculos. Mapa de objetivos y contrato neural.</p>',
    '<p>Creencias y consolidación, sesgos disfuncionales, laddering, protocolo de 5 pasos, reencuadre, emoción y re-consolidación. Inventario y protocolo.</p>',
    '<p>Circuitos emocionales, regulación top-down/bottom-up, protocolos ansiedad/estrés, cuerpo y vagal, integración. Termómetro y diario.</p>',
    '<p>Sistema 1 y 2, sesgos, pausa Neuro-Heurística™, matriz de decisiones, fatiga decisional. Checklist y guía de pausa.</p>',
    '<p>Ciclo hábito, 21-66-90, hábitos keystone, entorno, romper hábitos, sueño/movimiento. Tracker 66 días.</p>',
    '<p>Eje HHA, estrés agudo/crónico, resiliencia, HRV, recuperación, conexión social. Plan de estrés y resiliencia.</p>',
    '<p>DMN y yo, identidad dinámica, propósito, valores-acción, yo futuro neural. Brújula de propósito.</p>',
    '<p>Neuronas espejo, preguntas poderosas, escucha, rapport, feedback SBI, SCARF bajo amenaza. Protocolo de sesión 60–90 min.</p>',
    '<p>5 sesiones supervisadas, caso integrador, panel, plan de negocio, certificación ICF/EMCC, ética legal. Portafolio y video filosofía.</p>',
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

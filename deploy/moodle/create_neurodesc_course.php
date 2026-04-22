<?php
/**
 * CLI: crea el curso Moodle del diplomado Neuro-Decodificación / Psicogenealogía / PNL.
 *
 * Uso (en el servidor Moodle, como www-data):
 *   php admin/cli/create_neurodesc_course.php
 *
 * Copiar este archivo a: MOODLEDIR/admin/cli/create_neurodesc_course.php
 * Ajustar $CFG->category si hace falta (por defecto 1).
 */
define('CLI_SCRIPT', true);

require(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->dirroot . '/course/lib.php');

cli_heading('IIUS — Diplomado Neuro-Descodificación (crear curso)');

$shortname = 'IIUS-NEURODESC-PNL-2026';
$existing = $DB->get_record('course', ['shortname' => $shortname], 'id,fullname', IGNORE_MISSING);
if ($existing) {
    cli_writeln("Ya existe curso id={$existing->id} shortname={$shortname}");
    exit(0);
}

$data = new stdClass();
$data->fullname = 'Diplomado Internacional Neuro-Decodificación™, Psicogenealogía y PNL';
$data->shortname = $shortname;
$data->category = 1;
$data->summary = '<p>Programa de 10 meses (240 h): PNL aplicada, biodescodificación, psicogenealogía, análisis transgeneracional, psicosomática, epigenética conductual e integración clínica. Metodología experiencial con supervisión.</p>';
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
    'Módulo 1: Fundamentos de PNL aplicada a la biodescodificación',
    'Módulo 2: Biodescodificación I — Fundamentos y leyes biológicas',
    'Módulo 3: Biodescodificación II — Decodificación por sistemas',
    'Módulo 4: Psicogenealogía y construcción del genosociograma',
    'Módulo 5: Análisis transgeneracional de patrones repetitivos',
    'Módulo 6: Psicosomática clínica y el lenguaje del cuerpo',
    'Módulo 7: Epigenética conductual y transformación generacional',
    'Módulo 8: Herramientas avanzadas de PNL para sanación transgeneracional',
    'Módulo 9: Protocolos integrados de sesión terapéutica',
    'Módulo 10: Práctica supervisada, proyecto final y lanzamiento profesional',
];

$summaries = [
    '<p>PNL y biodescodificación: presuposiciones, VAKOG, rapport, anclajes, metamodelo, modelo SCORE. Entregables: perfil VAKOG, línea de vida sintomática, inventario de creencias sobre la salud.</p>',
    '<p>Nueva Medicina Germánica (introducción), 5 leyes biológicas, DHS, fases, cerebro triuno, ética y derivación. Herramientas: biograma inicial, BIO-QUEST.</p>',
    '<p>Decodificación por sistemas: digestivo, respiratorio, reproductivo/urinario, piel/inmune, musculoesquelético, endocrino, cardiovascular. DECODIFICA-360.</p>',
    '<p>Psicogenealogía, genosociograma vs genograma, 3–7 generaciones, lealtades invisibles, mandatos, proyecto sentido. Plantilla genosociograma y cuestionario de lealtades.</p>',
    '<p>Patrones repetitivos, fechas aniversario, secretos familiares, duelos, exclusiones, ancestro sustituto, trauma histórico colectivo. Matriz de patrones, línea de tiempo aniversario.</p>',
    '<p>Psicosomática: conversión vs somatización, enfermedades de alta carga emocional, dolor crónico, alexitimia, memoria traumática corporal. Diario psicosomático, body scan.</p>',
    '<p>Epigenética, estudios de trauma transgeneracional, ambiente y expresión génica, neuroplasticidad, legado saludable. EPI-GEN y plan de legado.</p>',
    '<p>Reimprinting transgeneracional, líneas de tiempo y árbol, partes internas, metáforas, perdón genealógico. Protocolos y biblioteca de metáforas.</p>',
    '<p>Sesión 90–120 min, algoritmo de intervención, ética, derivación, abreakciones, seguimiento. Plantillas de sesión, consentimiento informado.</p>',
    '<p>5 sesiones supervisadas, caso integrador, panel oral, plan de negocio, certificación. Portafolio: 5 casos, genosociograma, testimonios, plan de negocio.</p>',
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

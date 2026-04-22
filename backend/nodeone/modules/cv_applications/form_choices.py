"""Opciones de listas para el formulario público de CV (coherente con referencia UX)."""

# (valor interno, etiqueta)
SALARY_CHOICES = [
    ('', 'Seleccionar…'),
    ('no_indicar', 'Prefiero no indicar'),
    ('lt_18k', 'Menos de 18.000 €'),
    ('18k_24k', '18.000 € – 24.000 €'),
    ('24k_32k', '24.000 € – 32.000 €'),
    ('32k_45k', '32.000 € – 45.000 €'),
    ('45k_60k', '45.000 € – 60.000 €'),
    ('gt_60k', 'Más de 60.000 €'),
]

PROFESSIONAL_STATUS_CHOICES = [
    ('', 'Seleccionar…'),
    ('employed', 'Empleado/a por cuenta ajena'),
    ('self_employed', 'Autónomo/a / freelance'),
    ('unemployed', 'En búsqueda activa'),
    ('student', 'Estudiante'),
    ('first_job', 'Primer empleo'),
    ('retired', 'Jubilado/a'),
    ('other', 'Otro'),
]

NATIVE_LANGUAGE_CHOICES = [
    ('', 'Seleccionar…'),
    ('es', 'Español'),
    ('en', 'Inglés'),
    ('fr', 'Francés'),
    ('de', 'Alemán'),
    ('it', 'Italiano'),
    ('pt', 'Portugués'),
    ('ca', 'Catalán'),
    ('eu', 'Euskera'),
    ('gl', 'Gallego'),
    ('other', 'Otro'),
]

SECTOR_CHOICES = [
    ('', 'Seleccionar…'),
    ('tech', 'Tecnología e informática'),
    ('education', 'Educación y formación'),
    ('health', 'Salud y ciencias'),
    ('finance', 'Finanzas y seguros'),
    ('retail', 'Comercio y retail'),
    ('hospitality', 'Hostelería y turismo'),
    ('logistics', 'Logística y transporte'),
    ('construction', 'Construcción e ingeniería'),
    ('legal', 'Legal y consultoría'),
    ('marketing', 'Marketing y comunicación'),
    ('hr', 'Recursos humanos'),
    ('ngo', 'ONG / tercer sector'),
    ('public', 'Administración pública'),
    ('other', 'Otro (indica en comentarios)'),
]

YEARS_EXPERIENCE_CHOICES = [
    ('', 'Seleccionar…'),
    ('0', 'Sin experiencia'),
    ('lt_1', 'Menos de 1 año'),
    ('1_3', '1 – 3 años'),
    ('3_5', '3 – 5 años'),
    ('5_10', '5 – 10 años'),
    ('gt_10', 'Más de 10 años'),
]

REFERRAL_CHOICES = [
    ('', 'Seleccionar…'),
    ('web', 'Sitio web / buscador'),
    ('linkedin', 'LinkedIn'),
    ('social', 'Redes sociales'),
    ('friend', 'Recomendación de persona conocida'),
    ('event', 'Evento o feria'),
    ('job_board', 'Portal de empleo'),
    ('news', 'Noticias / prensa'),
    ('other', 'Otro'),
]

EDUCATION_LEVEL_CHOICES = [
    ('', 'Seleccionar…'),
    ('eso', 'ESO / secundaria'),
    ('bach', 'Bachillerato / FP básica'),
    ('fp_sup', 'FP superior / técnico'),
    ('univ_under', 'Universidad (grado)'),
    ('univ_post', 'Universidad (máster / posgrado)'),
    ('doctorate', 'Doctorado'),
    ('other', 'Otro'),
]

#!/usr/bin/env python3
"""
Script para crear categorías de servicios y asignarlas a servicios existentes
basándose en análisis de nombres de servicios.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, Service, ServiceCategory

def categorize_service(service_name):
    """Asignar categoría basándose en el nombre del servicio"""
    name = service_name.lower()
    
    if 'artículo' in name or 'revista' in name or 'libro' in name or 'postulación' in name or 'ojs' in name or 'omp' in name or 'indexación' in name:
        return 'publicaciones'
    elif 'curso' in name or 'taller' in name or 'seminario' in name or 'diplomado' in name or 'posdoctorado' in name:
        return 'formacion'
    elif 'asesoría' in name or 'apoyo' in name:
        return 'asesoria'
    elif 'redacción' in name:
        return 'redaccion'
    elif 'revisión' in name or 'antiplagio' in name:
        return 'revision'
    elif 'proyecto' in name and 'investigación' in name:
        return 'proyectos'
    elif 'evento' in name or 'organización' in name:
        return 'eventos'
    elif 'sistema' in name or 'acreditación' in name:
        return 'sistemas'
    elif 'convenio' in name or 'internacional' in name:
        return 'convenios'
    elif 'convocatoria' in name or 'fondo' in name:
        return 'financiamiento'
    elif 'grupo' in name or 'semillero' in name:
        return 'investigacion'
    elif 'innovación' in name or 'propiedad' in name:
        return 'propiedad-intelectual'
    elif 'sala' in name or 'transmisión' in name:
        return 'infraestructura'
    elif 'cartel' in name or 'póster' in name:
        return 'diseno-grafico'
    else:
        return None

def create_categories():
    """Crear categorías base si no existen"""
    categories_data = [
        {
            'name': 'Publicaciones',
            'slug': 'publicaciones',
            'description': 'Servicios relacionados con publicaciones científicas, revistas, libros y artículos',
            'icon': 'fas fa-book',
            'color': 'primary',
            'display_order': 1
        },
        {
            'name': 'Formación',
            'slug': 'formacion',
            'description': 'Cursos, talleres, seminarios, diplomados y programas de formación',
            'icon': 'fas fa-graduation-cap',
            'color': 'success',
            'display_order': 2
        },
        {
            'name': 'Asesoría',
            'slug': 'asesoria',
            'description': 'Asesorías y apoyo en investigación, proyectos y consultoría',
            'icon': 'fas fa-handshake',
            'color': 'info',
            'display_order': 3
        },
        {
            'name': 'Redacción',
            'slug': 'redaccion',
            'description': 'Servicios de redacción científica y académica',
            'icon': 'fas fa-pen',
            'color': 'warning',
            'display_order': 4
        },
        {
            'name': 'Revisión',
            'slug': 'revision',
            'description': 'Revisión de documentos, antiplagio y control de calidad',
            'icon': 'fas fa-check-circle',
            'color': 'success',
            'display_order': 5
        },
        {
            'name': 'Proyectos',
            'slug': 'proyectos',
            'description': 'Gestión y desarrollo de proyectos de investigación',
            'icon': 'fas fa-project-diagram',
            'color': 'primary',
            'display_order': 6
        },
        {
            'name': 'Eventos',
            'slug': 'eventos',
            'description': 'Organización y gestión de eventos científicos',
            'icon': 'fas fa-calendar-alt',
            'color': 'info',
            'display_order': 7
        },
        {
            'name': 'Sistemas',
            'slug': 'sistemas',
            'description': 'Sistemas de administración académica y acreditación',
            'icon': 'fas fa-server',
            'color': 'secondary',
            'display_order': 8
        },
        {
            'name': 'Convenios',
            'slug': 'convenios',
            'description': 'Convenios internacionales, estancias y becas',
            'icon': 'fas fa-globe',
            'color': 'primary',
            'display_order': 9
        },
        {
            'name': 'Financiamiento',
            'slug': 'financiamiento',
            'description': 'Convocatorias para fondos y financiamiento de proyectos',
            'icon': 'fas fa-dollar-sign',
            'color': 'success',
            'display_order': 10
        },
        {
            'name': 'Investigación',
            'slug': 'investigacion',
            'description': 'Grupos de investigación y semilleros',
            'icon': 'fas fa-flask',
            'color': 'info',
            'display_order': 11
        },
        {
            'name': 'Propiedad Intelectual',
            'slug': 'propiedad-intelectual',
            'description': 'Proyectos de innovación y propiedad intelectual',
            'icon': 'fas fa-lightbulb',
            'color': 'warning',
            'display_order': 12
        },
        {
            'name': 'Infraestructura',
            'slug': 'infraestructura',
            'description': 'Alquiler de salas virtuales y servicios de transmisión',
            'icon': 'fas fa-building',
            'color': 'secondary',
            'display_order': 13
        },
        {
            'name': 'Diseño Gráfico',
            'slug': 'diseno-grafico',
            'description': 'Diseño de carteles, pósteres y material gráfico',
            'icon': 'fas fa-palette',
            'color': 'info',
            'display_order': 14
        }
    ]
    
    created = 0
    for cat_data in categories_data:
        existing = ServiceCategory.query.filter_by(slug=cat_data['slug']).first()
        if not existing:
            category = ServiceCategory(**cat_data)
            db.session.add(category)
            created += 1
            print(f"✓ Creada categoría: {cat_data['name']}")
        else:
            print(f"→ Categoría ya existe: {cat_data['name']}")
    
    db.session.commit()
    return created

def assign_categories_to_services():
    """Asignar categorías a servicios existentes"""
    services = Service.query.all()
    assigned = 0
    
    for service in services:
        if not service.category_id:
            category_slug = categorize_service(service.name)
            if category_slug:
                category = ServiceCategory.query.filter_by(slug=category_slug).first()
                if category:
                    service.category_id = category.id
                    assigned += 1
                    print(f"✓ Asignada categoría '{category.name}' a: {service.name}")
    
    db.session.commit()
    return assigned

def main():
    with app.app_context():
        print("=" * 80)
        print("MIGRACIÓN: Crear Categorías de Servicios")
        print("=" * 80)
        print()
        
        print("1. Creando categorías base...")
        created = create_categories()
        print(f"   → {created} categorías creadas\n")
        
        print("2. Asignando categorías a servicios existentes...")
        assigned = assign_categories_to_services()
        print(f"   → {assigned} servicios categorizados\n")
        
        print("=" * 80)
        print("✅ Migración completada")
        print("=" * 80)

if __name__ == '__main__':
    main()

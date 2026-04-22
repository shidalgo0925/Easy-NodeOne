/**
 * Tour guiado para administradores de Easy NodeOne
 * Incluye todas las funciones del tour de usuarios + funciones administrativas
 */

(function() {
    'use strict';

    // Configuración del tour para administradores - Versión interactiva
    const adminTourSteps = [
        {
            element: '#left-panel',
            intro: '<h3>¡Bienvenido Administrador!</h3><p>Este tour interactivo te enseñará cómo usar todas las funciones administrativas del sistema paso a paso.</p><p><strong>💡 Tip:</strong> Puedes iniciar este tour en cualquier momento desde el icono <i class="fas fa-route"></i> en el menú superior o lateral.</p><div class="mt-3"><label class="d-flex align-items-center"><input type="checkbox" id="dontShowTourAgain" class="me-2"> <span>No mostrar más este tour</span></label></div>',
            position: 'right'
        },
        {
            element: 'a[href*="dashboard"]:first-of-type',
            intro: '<h4>📊 Dashboard</h4><p><strong>¿Qué es?</strong> Tu panel principal con resumen de actividad y acceso rápido.</p><p><strong>¿Cómo usarlo?</strong> Haz clic aquí para ver estadísticas generales del sistema.</p>',
            position: 'right'
        },
        {
            element: '.nav-group:first-of-type',
            intro: '<h4>👥 Sección Miembros</h4><p><strong>¿Qué contiene?</strong> Opciones para miembros: Beneficios, Servicios, Office 365, Eventos y Citas.</p><p><strong>Nota:</strong> Como admin, también puedes acceder a estas funciones para probarlas.</p>',
            position: 'right'
        },
        {
            element: '.nav-group:last-of-type',
            intro: '<h4>⚙️ Sección Administración</h4><p><strong>🔐 Función exclusiva de administradores:</strong> Desde aquí gestionas todo el sistema.</p><p><strong>¿Cómo usarlo?</strong> Haz clic en "Administración" para expandir y ver todas las opciones administrativas disponibles.</p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_dashboard"]',
            intro: '<h4>📈 Panel Admin</h4><p><strong>¿Qué encontrarás?</strong> Dashboard administrativo con estadísticas del sistema.</p><p><strong>¿Cómo usarlo?</strong><ol><li>Haz clic aquí para acceder al panel</li><li>Verás usuarios activos, membresías y pagos recientes</li><li>Usa las acciones rápidas para tareas comunes</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_users"]',
            intro: '<h4>👤 Gestión de Usuarios</h4><p><strong>¿Qué puedes hacer?</strong> Administrar todos los usuarios del sistema.</p><p><strong>¿Cómo gestionar usuarios?</strong><ol><li>Haz clic aquí para ver la lista de usuarios</li><li>Usa "Crear Usuario" para agregar nuevos</li><li>Edita, activa o desactiva cuentas según necesites</li><li>Filtra y busca usuarios específicos</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_memberships"]',
            intro: '<h4>👑 Gestión de Membresías</h4><p><strong>¿Qué puedes hacer?</strong> Gestionar membresías activas y verificar estados.</p><p><strong>¿Cómo gestionar?</strong><ol><li>Haz clic aquí para ver todas las membresías</li><li>Revisa estados activos/inactivos</li><li>Renueva membresías manualmente si es necesario</li><li>Consulta el historial de membresías</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_payments"]',
            intro: '<h4>💳 Ver Pagos</h4><p><strong>¿Qué puedes hacer?</strong> Revisar todos los pagos del sistema.</p><p><strong>⚠️ Importante:</strong> El badge rojo indica pagos pendientes que requieren revisión OCR.</p><p><strong>¿Cómo revisar pagos?</strong><ol><li>Haz clic aquí para ver todos los pagos</li><li>Filtra por estado (pendiente, aprobado, rechazado)</li><li>Revisa pagos con OCR pendiente haciendo clic en "Revisar Pagos OCR"</li><li>Aproba o rechaza pagos manuales según corresponda</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_events"]',
            intro: '<h4>📅 Gestión de Eventos</h4><p><strong>¿Qué puedes hacer?</strong> Crear y administrar eventos del sistema.</p><p><strong>¿Cómo crear un evento?</strong><ol><li>Haz clic aquí para ver la lista de eventos</li><li>Haz clic en "Crear Evento"</li><li>Completa la información del evento</li><li>Configura precios, descuentos y fechas</li><li>Gestiona participantes y certificados</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_appointments"]',
            intro: '<h4>⏰ Gestión de Citas</h4><p><strong>¿Qué puedes hacer?</strong> Administrar asesores y citas agendadas.</p><p><strong>¿Cómo configurar?</strong><ol><li>Haz clic aquí para acceder a la gestión de citas</li><li>Configura tipos de servicios disponibles</li><li>Agrega asesores y sus horarios disponibles</li><li>Gestiona las citas agendadas por los miembros</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_email"]',
            intro: '<h4>📧 Configuración de Email</h4><p><strong>¿Qué puedes hacer?</strong> Configurar el servidor de correo y plantillas.</p><p><strong>¿Cómo configurar?</strong><ol><li>Haz clic aquí para acceder a la configuración</li><li>Configura el servidor SMTP (Gmail, O365, etc.)</li><li>Personaliza las plantillas de emails</li><li>Prueba el envío de correos</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="admin_notifications"]',
            intro: '<h4>🔔 Notificaciones</h4><p><strong>¿Qué puedes hacer?</strong> Gestionar las notificaciones del sistema.</p><p><strong>¿Cómo configurar?</strong><ol><li>Haz clic aquí para ver la configuración</li><li>Activa o desactiva tipos de notificaciones</li><li>Personaliza los mensajes de notificación</li><li>Envía notificaciones manuales si es necesario</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="/admin/backup"]',
            intro: '<h4>💾 Respaldos de BD</h4><p><strong>⚠️ MUY IMPORTANTE:</strong> Crea respaldos regulares de la base de datos.</p><p><strong>¿Cómo hacer respaldo?</strong><ol><li>Haz clic aquí para acceder a respaldos</li><li>Haz clic en "Crear y Descargar Respaldo"</li><li>Descarga el archivo .db a tu computadora</li><li>Guarda los respaldos en un lugar seguro</li><li>Para restaurar, selecciona un backup y haz clic en "Restaurar"</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="cart"]',
            intro: '<h4>🛒 Carrito de Compras</h4><p><strong>¿Qué es?</strong> Donde se guardan las compras de membresías, eventos y servicios.</p><p><strong>Como admin también puedes:</strong> Usar el carrito para probar el proceso de compra.</p>',
            position: 'bottom'
        },
        {
            element: 'a[href*="notifications"]',
            intro: '<h4>🔔 Notificaciones</h4><p><strong>¿Qué recibirás?</strong> Notificaciones sobre eventos, pagos y actualizaciones del sistema.</p><p><strong>El badge rojo muestra:</strong> Cuántas notificaciones nuevas tienes.</p>',
            position: 'bottom'
        },
        {
            element: '#tourNavBtn',
            intro: '<h4>🗺️ Tour Guiado</h4><p><strong>¿Qué es?</strong> Este botón te permite iniciar el tour guiado en cualquier momento.</p><p><strong>¿Cómo usarlo?</strong> Haz clic en este icono <i class="fas fa-route"></i> cuando quieras repasar las funciones del sistema.</p>',
            position: 'bottom'
        },
        {
            element: 'a[href*="help"]',
            intro: '<h4>❓ Centro de Ayuda</h4><p><strong>¿Qué encontrarás?</strong> Guías, documentación y soporte técnico.</p><p><strong>También puedes:</strong> Reiniciar este tour desde el botón "Iniciar Tour Guiado" en la página de ayuda.</p>',
            position: 'bottom'
        }
    ];

    /**
     * Inicializar el tour para administradores
     * NOTA: El tour NO se inicia automáticamente, solo cuando el usuario hace clic en el icono
     */
    function initAdminTour() {
        // El tour solo se inicia manualmente cuando el usuario hace clic en el icono
        // No se inicia automáticamente al cargar la página
        return;
    }

    /**
     * Iniciar el tour manualmente
     */
    function startAdminTour() {
        // Configurar Intro.js con los pasos del tour
        introJs()
            .setOptions({
                steps: adminTourSteps,
                showProgress: true,
                showBullets: true,
                exitOnOverlayClick: false,
                exitOnEsc: true,
                nextLabel: 'Siguiente →',
                prevLabel: '← Anterior',
                skipLabel: 'Saltar Tour',
                doneLabel: 'Finalizar',
                tooltipClass: 'customTooltip',
                highlightClass: 'customHighlight',
                buttonClass: 'btn btn-primary',
                exitIntroOnEsc: true
            })
            .onbeforechange(function(targetElement) {
                // Verificar el checkbox en el primer paso
                if (targetElement && targetElement.querySelector('#dontShowTourAgain')) {
                    const checkbox = targetElement.querySelector('#dontShowTourAgain');
                    if (checkbox && checkbox.checked) {
                        localStorage.setItem('nodeone_tour_admin_dont_show', 'true');
                    }
                }
            })
            .oncomplete(function() {
                // Verificar si el usuario marcó "no mostrar más"
                const checkbox = document.querySelector('#dontShowTourAgain');
                if (checkbox && checkbox.checked) {
                    localStorage.setItem('nodeone_tour_admin_dont_show', 'true');
                }
                
                // Marcar el tour como completado
                localStorage.setItem('nodeone_tour_admin_completed', 'true');
                showTourCompletionMessage();
            })
            .onexit(function() {
                // Verificar si el usuario marcó "no mostrar más" al salir
                const checkbox = document.querySelector('#dontShowTourAgain');
                if (checkbox && checkbox.checked) {
                    localStorage.setItem('nodeone_tour_admin_dont_show', 'true');
                }
                // Si el usuario sale del tour, no marcarlo como completado
            })
            .start();
    }

    /**
     * Mostrar mensaje de finalización del tour
     */
    function showTourCompletionMessage() {
        // Crear y mostrar un mensaje de éxito
        const message = document.createElement('div');
        message.className = 'alert alert-success alert-dismissible fade show position-fixed';
        message.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
        message.innerHTML = `
            <strong><i class="fas fa-check-circle me-2"></i>¡Tour completado!</strong>
            <p class="mb-0">Ya conoces todas las funciones del sistema administrativo. Puedes reiniciar el tour desde el Centro de Ayuda.</p>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(message);

        // Auto-cerrar después de 5 segundos
        setTimeout(function() {
            message.remove();
        }, 5000);
    }

    // Exponer función para iniciar el tour manualmente
    window.startAdminTour = startAdminTour;

    // Inicializar automáticamente cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAdminTour);
    } else {
        initAdminTour();
    }
})();


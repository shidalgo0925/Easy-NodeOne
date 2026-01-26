/**
 * Tour guiado para usuarios comunes de RELATIC Panamá
 * Usa Intro.js para explicar las funcionalidades del sistema
 */

(function() {
    'use strict';

    // Configuración del tour para usuarios comunes - Versión interactiva
    const userTourSteps = [
        {
            element: '#left-panel',
            intro: '<h3>¡Bienvenido a RELATIC Panamá!</h3><p>Este tour interactivo te enseñará cómo usar todas las funciones del sistema paso a paso.</p><p><strong>💡 Tip:</strong> Puedes iniciar este tour en cualquier momento desde el icono <i class="fas fa-route"></i> en el menú superior.</p><div class="mt-3"><label class="d-flex align-items-center"><input type="checkbox" id="dontShowTourAgain" class="me-2"> <span>No mostrar más este tour</span></label></div>',
            position: 'right'
        },
        {
            element: 'a[href*="dashboard"]:first-of-type',
            intro: '<h4>📊 Dashboard</h4><p><strong>¿Qué es?</strong> Tu panel principal con resumen de actividad y membresía.</p><p><strong>¿Cómo usarlo?</strong> Haz clic aquí para ver estadísticas, membresía activa y acceso rápido a funciones importantes.</p>',
            position: 'right'
        },
        {
            element: '.nav-group:first-of-type',
            intro: '<h4>👥 Sección Miembros</h4><p><strong>¿Qué contiene?</strong> Todas las opciones para miembros: Beneficios, Servicios, Office 365, Eventos y Citas.</p><p><strong>¿Cómo usarlo?</strong> Haz clic en "Miembros" para expandir el menú y ver todas las opciones disponibles.</p>',
            position: 'right'
        },
        {
            element: 'a[href*="benefits"]',
            intro: '<h4>🎁 Beneficios</h4><p><strong>¿Qué encontrarás?</strong> Todos los beneficios de tu plan de membresía.</p><p><strong>¿Cómo verlos?</strong> Haz clic aquí para ver descuentos, recursos exclusivos y ventajas de tu membresía.</p>',
            position: 'right'
        },
        {
            element: 'a[href*="services"]',
            intro: '<h4>🔔 Servicios</h4><p><strong>¿Qué son?</strong> Servicios exclusivos para miembros: contenido premium y recursos educativos.</p><p><strong>¿Cómo acceder?</strong> Haz clic aquí para explorar y acceder a los servicios disponibles.</p>',
            position: 'right'
        },
        {
            element: 'a[href*="events"]',
            intro: '<h4>📅 Eventos</h4><p><strong>¿Qué puedes hacer?</strong> Explorar y registrarte en eventos, conferencias y actividades.</p><p><strong>¿Cómo registrarte?</strong><ol><li>Haz clic aquí para ver eventos disponibles</li><li>Selecciona un evento que te interese</li><li>Haz clic en "Registrarse" y completa el proceso</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="appointments"]',
            intro: '<h4>⏰ Citas</h4><p><strong>¿Qué puedes hacer?</strong> Agendar citas con asesores y consultores.</p><p><strong>¿Cómo agendar?</strong><ol><li>Haz clic aquí para ver tipos de servicios</li><li>Elige un asesor disponible</li><li>Selecciona fecha y hora</li><li>Confirma tu cita</li></ol></p>',
            position: 'right'
        },
        {
            element: 'a[href*="cart"]',
            intro: '<h4>🛒 Carrito de Compras</h4><p><strong>¿Qué es?</strong> Donde se guardan tus compras de membresías, eventos y servicios.</p><p><strong>¿Cómo comprar?</strong><ol><li>Agrega items al carrito desde cualquier página</li><li>Haz clic aquí para ver tu carrito</li><li>Revisa los items y procede al pago</li></ol></p>',
            position: 'bottom'
        },
        {
            element: 'a[href*="notifications"]',
            intro: '<h4>🔔 Notificaciones</h4><p><strong>¿Qué recibirás?</strong> Notificaciones sobre eventos, pagos, actualizaciones y más.</p><p><strong>¿Cómo verlas?</strong> Haz clic aquí para ver todas tus notificaciones. El badge rojo muestra cuántas nuevas tienes.</p>',
            position: 'bottom'
        },
        {
            element: 'a[href*="help"]',
            intro: '<h4>❓ Centro de Ayuda</h4><p><strong>¿Qué encontrarás?</strong> Respuestas a preguntas frecuentes, guías de uso y soporte técnico.</p><p><strong>¿Cómo usarlo?</strong> Haz clic aquí cuando necesites ayuda. También puedes reiniciar este tour desde allí.</p>',
            position: 'bottom'
        },
        {
            element: '#tourNavBtn',
            intro: '<h4>🗺️ Tour Guiado</h4><p><strong>¿Qué es?</strong> Este botón te permite iniciar el tour guiado en cualquier momento.</p><p><strong>¿Cómo usarlo?</strong> Haz clic en este icono <i class="fas fa-route"></i> cuando quieras repasar las funciones del sistema.</p>',
            position: 'bottom'
        },
        {
            element: '#navbarDropdown',
            intro: '<h4>👤 Menú de Usuario</h4><p><strong>¿Qué contiene?</strong> Acceso a tu perfil, configuración de membresía y opciones de cuenta.</p><p><strong>¿Cómo acceder?</strong> Haz clic en tu nombre para ver opciones como:<ul><li>Ver tu perfil</li><li>Gestionar tu membresía</li><li>Cerrar sesión</li></ul></p>',
            position: 'bottom'
        }
    ];

    /**
     * Inicializar el tour para usuarios comunes
     * NOTA: El tour NO se inicia automáticamente, solo cuando el usuario hace clic en el icono
     */
    function initUserTour() {
        // El tour solo se inicia manualmente cuando el usuario hace clic en el icono
        // No se inicia automáticamente al cargar la página
        return;
    }

    /**
     * Iniciar el tour manualmente
     */
    function startUserTour() {
        // Configurar Intro.js con los pasos del tour
        introJs()
            .setOptions({
                steps: userTourSteps,
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
                        localStorage.setItem('relatic_tour_user_dont_show', 'true');
                    }
                }
            })
            .oncomplete(function() {
                // Verificar si el usuario marcó "no mostrar más"
                const checkbox = document.querySelector('#dontShowTourAgain');
                if (checkbox && checkbox.checked) {
                    localStorage.setItem('relatic_tour_user_dont_show', 'true');
                }
                
                // Marcar el tour como completado
                localStorage.setItem('relatic_tour_user_completed', 'true');
                showTourCompletionMessage();
            })
            .onexit(function() {
                // Verificar si el usuario marcó "no mostrar más" al salir
                const checkbox = document.querySelector('#dontShowTourAgain');
                if (checkbox && checkbox.checked) {
                    localStorage.setItem('relatic_tour_user_dont_show', 'true');
                }
                // Si el usuario sale del tour, no marcarlo como completado
                // para que pueda iniciarlo de nuevo desde el menú de ayuda
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
            <p class="mb-0">Ya conoces las funciones principales del sistema. Puedes iniciar el tour nuevamente desde el Centro de Ayuda.</p>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(message);

        // Auto-cerrar después de 5 segundos
        setTimeout(function() {
            message.remove();
        }, 5000);
    }

    // Exponer función para iniciar el tour manualmente
    window.startUserTour = startUserTour;

    // Inicializar automáticamente cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUserTour);
    } else {
        initUserTour();
    }
})();


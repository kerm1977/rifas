// detall_rifa.js (Lógica JS de Selección/Exportación)
// Todo el código está encapsulado en una IIFE para evitar conflictos de alcance (scope).
(function() {

// --- VARIABLES GLOBALES PARA ESTADO Y ACCESO RÁPIDO (Módulo Scope) ---

// Se usa window.deferredPrompt para exponer la variable para la PWA globalmente.
window.deferredPrompt = undefined; 

// Almacenamiento de números seleccionados (se usa window.selectedNumbers para asegurar persistencia global).
window.selectedNumbers = [];

// Elementos DOM (Constantes encapsuladas en el módulo)
const numbersGrid = document.getElementById('numbers-grid');
const floatingSelectButton = document.getElementById('floating-select-button');

// Elementos de formulario/display de escritorio
const desktopSelectedNumbersDisplay = document.getElementById('selected_numbers_display');
const desktopSelectedNumbersInput = document.getElementById('selected_numbers_input');
const desktopSubmitButton = document.getElementById('submit_button');
// CORRECCIÓN: Usamos el ID correcto para el display del monto
const desktopTotalAmount = document.getElementById('desktop_total_amount');

// Elementos de formulario/display del modal (Mobile)
const modalSelectedNumbersDisplay = document.getElementById('modal_selected_numbers_display');
const modalSelectedNumbersInput = document.getElementById('modal_selected_numbers_input');
const modalSubmitButton = document.getElementById('modal_submit_button');
// CORRECCIÓN: Usamos el ID correcto para el display del monto del modal
const modalTotalAmount = document.getElementById('modal_total_amount');

// Elementos de Modales (para manejo programático si es necesario)
const editModalElement = document.getElementById('edit-modal-bs');
const cancelConfirmModalElement = document.getElementById('cancel-confirm-modal-bs');

let rafflePrice = 0; // Se inicializa en DOMContentLoaded.


// --- FUNCIONES DE UTILIDAD ---

/**
 * Función que asume el precio de la rifa fue inyectado en el HTML.
 * @returns {number} El precio de la rifa.
 */
function getRafflePrice() {
    // Busca el precio en el span de precio por número en el modal de info
    const priceElement = document.querySelector('#raffle-info-modal-bs .text-xl.font-extrabold.text-green-600');
    if (priceElement) {
        // Limpiamos el texto (ej. "₡1,000.00" -> "1000.00")
        const text = priceElement.textContent.replace(/₡|,/g, '').trim(); // Elimina ₡ y comas
        return parseFloat(text) || 0; // Asegura devolver 0 si no es un número válido
    }
    // Fallback si no se puede leer
    return 1000.00; 
}


/**
 * Sincroniza el estado de la selección (input, display, botones y monto total).
 * @param {number} price Precio de la rifa para calcular el total.
 */
function updateFormDisplays(price) {
    const selected = window.selectedNumbers;
    const isSelected = selected.length > 0;
    
    selected.sort((a, b) => parseInt(a) - parseInt(b));
    // CORRECCIÓN: El display debe ser la lista de números.
    const displayStr = isSelected ? selected.join(', ') : 'Ninguno';
    const displayCount = selected.length;
    const inputValue = isSelected ? selected.join(',') : '';

    // CÁLCULO Y FORMATO DEL TOTAL (Corregido: Antes faltaba el cálculo de totalAmount)
    const totalAmount = displayCount * price; 
    
    // Formato de moneda, usando toLocaleString para un formato correcto (ej: ₡1.000,00)
    const totalDisplayFormatted = totalAmount.toLocaleString('es-CR', { 
        style: 'currency', 
        currency: 'CRC', // Código de moneda para Costa Rica (Colón)
        minimumFractionDigits: 2,
        maximumFractionDigits: 2 
    });
    
    // Displays de números seleccionados e inputs ocultos
    if (desktopSelectedNumbersDisplay) desktopSelectedNumbersDisplay.textContent = displayStr;
    if (modalSelectedNumbersDisplay) modalSelectedNumbersDisplay.textContent = displayStr;
    if (desktopSelectedNumbersInput) desktopSelectedNumbersInput.value = inputValue;
    if (modalSelectedNumbersInput) modalSelectedNumbersInput.value = inputValue;

    // Display de Monto Total
    if (desktopTotalAmount) desktopTotalAmount.textContent = isSelected ? `(Total: ${totalDisplayFormatted})` : '';
    if (modalTotalAmount) modalTotalAmount.textContent = isSelected ? `(Total: ${totalDisplayFormatted})` : '';


    // Botones de enviar (ESCRITORIO Y MODAL)
    [desktopSubmitButton, modalSubmitButton].forEach(btn => {
        if (btn) {
            btn.disabled = !isSelected;
            
            // Texto del botón: Deshabilitado vs Habilitado
            btn.innerHTML = isSelected 
                ? `<i class="fas fa-shopping-cart me-2"></i> Comprar ${displayCount} Núm. ${totalDisplayFormatted}` 
                : `<i class="fas fa-hand-pointer me-2"></i> Seleccione Números`;
        }
    });

    // Botón flotante (MOBILE)
    if (floatingSelectButton) {
        floatingSelectButton.disabled = !isSelected;
        
        floatingSelectButton.innerHTML = isSelected
            ? `<i class="fas fa-shopping-cart me-2"></i> Comprar ${displayCount} Núm. ${totalDisplayFormatted}`
            : `<i class="fas fa-hand-pointer me-2"></i> Seleccionar Números`;
    }
}

/**
 * Actualiza las clases visuales de un botón numérico, aplicando el color celeste si está seleccionado.
 * @param {HTMLElement} button El elemento botón.
 * @param {boolean} isSelectedNow Indica si el número está seleccionado en el array.
 * @param {boolean} isSold Indica si el número está vendido/ocupado.
 */
function updateButtonStyles(button, isSelectedNow, isSold) {
    // Definimos un conjunto de clases de color dinámicas que se pueden intercambiar.
    const DYNAMIC_COLOR_CLASSES = [
        // Clases de Fondo y Texto
        'bg-pastel-green', 'text-green-800', 'hover:bg-green-300', 'border-green-300', 
        
        // Clases de Fondo y Texto para SELECCIONADO (Celeste)
        'bg-pastel-blue', 'text-blue-800', 'hover:bg-blue-300', 'border-blue-300' 
    ];

    // 1. Limpiar TODAS las clases de color dinámicas del botón.
    button.classList.remove(...DYNAMIC_COLOR_CLASSES);
    
    // Obtener el estado de cancelación del HTML original (si existe)
    const isCanceledFromHTML = button.classList.contains('bg-green-500'); 
    
    // Si está vendido o cancelado por Jinja, no hacemos nada.
    if (isSold || isCanceledFromHTML) {
        button.disabled = true;
        return; // Detener la ejecución si el estado es permanente.
    } 
    
    // 2. Aplicar las clases según el estado actual
    if (isSelectedNow) {
        // Seleccionado (Celeste Pastel)
        // Agregamos las clases CELestes
        button.classList.add('bg-pastel-blue', 'text-blue-800', 'hover:bg-blue-300', 'border-blue-300'); 
        button.disabled = false;
    } else {
        // Disponible (Verde Pastel)
        // Agregamos las clases VERDES
        button.classList.add('bg-pastel-green', 'text-green-800', 'hover:bg-green-300', 'border-green-300'); 
        button.disabled = false;
    }
    
    // Aseguramos que la clase 'border' base siempre esté presente si no es vendido/cancelado
    if (!button.classList.contains('border')) {
        button.classList.add('border');
    }
}


// --- MANEJADORES DE EVENTOS GLOBALES ---

// Handler de click en los botones de número
if (numbersGrid) {
    numbersGrid.addEventListener('click', function(e) {
        const button = e.target.closest('.number-button');
        if (!button) return; 
        
        const number = button.dataset.number;
        // La propiedad 'data-sold' incluye tanto Vendido como Cancelado desde Jinja
        const isSold = button.dataset.sold === 'true'; 

        // Si está vendido o cancelado, no se puede seleccionar
        if (isSold) return;

        const index = window.selectedNumbers.indexOf(number);

        if (index > -1) {
            // Deseleccionar: Remover de la lista y actualizar estilos
            window.selectedNumbers.splice(index, 1);
            updateButtonStyles(button, false, isSold);
        } else {
            // Seleccionar: Agregar a la lista y actualizar estilos
            window.selectedNumbers.push(number);
            updateButtonStyles(button, true, isSold);
        }

        // Sincronizar UI (displays y botones de submit)
        updateFormDisplays(rafflePrice);
    });
}


// --- FUNCIONES LLAMADAS DESDE EL HTML (onclick) ---
// Estas funciones se adjuntan a 'window' para ser accesibles desde los atributos onclick en el HTML.

window.togglePasswordVisibility = function(id) {
    const input = document.getElementById(id);
    const icon = document.getElementById(`toggle_${id}_icon`);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}

window.returnToSelection = function() {
    // Función llamada al cerrar el modal de selección.
    console.log("Modal de selección cerrado. Se mantiene la selección actual.");
    updateFormDisplays(rafflePrice);
}

window.openZoomModal = function(src) {
    const imgElement = document.getElementById('zoom-image');
    if (imgElement) {
        imgElement.src = src;
        imgElement.style.transform = 'scale(1)'; 
        window.zoomLevel = 1; 
    }
}

window.handleZoom = function(direction) {
    if (typeof window.zoomLevel === 'undefined') window.zoomLevel = 1;
    const step = 0.2;
    const minZoom = 1;
    const maxZoom = 3;

    window.zoomLevel += direction * step;

    if (window.zoomLevel < minZoom) window.zoomLevel = minZoom;
    if (window.zoomLevel > maxZoom) window.zoomLevel = maxZoom;
    
    const imgElement = document.getElementById('zoom-image');
    if (imgElement) {
        imgElement.style.transform = `scale(${window.zoomLevel})`;
    }
}

window.openEditModal = function(selectionIds, numbersList, customerName, customerPhone) {
    document.getElementById('modal-selection-ids').value = selectionIds;
    document.getElementById('modal-number-display').textContent = numbersList;
    
    document.getElementById('customer_name_display').value = customerName;
    document.getElementById('customer_phone_display').value = customerPhone;
    
    document.getElementById('edit_password').value = ''; 
    
    if (typeof bootstrap !== 'undefined' && editModalElement) {
        const modalInstance = bootstrap.Modal.getInstance(editModalElement) || new bootstrap.Modal(editModalElement);
        modalInstance.show();
    }
}

window.confirmCancellation = function(selectionIds, customerName, isCanceled) {
    if (isCanceled === 1) {
        console.log(`La selección para "${customerName}" ya está marcada como CANCELADA.`); 
        return;
    }
    
    const numberDisplay = document.getElementById('modal-cancel-customer-name');
    const idsInput = document.getElementById('modal-cancel-selection-ids');
    
    if (numberDisplay) numberDisplay.textContent = customerName;
    if (idsInput) idsInput.value = selectionIds;

    if (typeof bootstrap !== 'undefined' && cancelConfirmModalElement) {
        const modalInstance = bootstrap.Modal.getInstance(cancelConfirmModalElement) || new bootstrap.Modal(cancelConfirmModalElement);
        modalInstance.show();
    }
}

window.filterCards = function() {
    const searchInput = document.getElementById('search-input');
    const filterText = searchInput.value.toLowerCase().trim();
    const cardsContainer = document.getElementById('search-results-container');
    
    if (!cardsContainer) {
        console.error('El contenedor de resultados de búsqueda no existe.');
        return;
    }

    const cards = cardsContainer.querySelectorAll('.search-card');

    cards.forEach(card => {
        const name = card.dataset.name || '';
        const phone = card.dataset.phone || '';
        const numbers = card.dataset.numbers || ''; 

        let matches = false;

        if (filterText.length > 0) {
            if (name.includes(filterText)) {
                matches = true;
            }
            else if (phone.includes(filterText)) {
                matches = true;
            }
            else if (numbers.includes(filterText)) {
                matches = true;
            }
        } else {
            matches = true;
        }

        if (matches) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}


/**
 * Lógica de PWA (Instalación).
 */

// Escucha el evento beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    window.deferredPrompt = e;
    const installButton = document.getElementById('install-pwa-button');
    if (installButton) {
        installButton.style.display = 'block';
        installButton.addEventListener('click', (e) => {
            const btn = e.currentTarget;
            if (window.deferredPrompt) {
                btn.style.display = 'none';
                window.deferredPrompt.prompt();
                window.deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('El usuario aceptó instalar la PWA');
                    } else {
                        console.log('El usuario rechazó la instalación de la PWA');
                    }
                    window.deferredPrompt = null;
                });
            }
        });
    }
});


/**
 * Lógica de Exportar Card a PNG.
 * (Función exportCardToPng se mantiene global para ser accesible desde el HTML)
 */
window.exportCardToPng = function(cardId, customerName, raffleNumber, customerPhone, waMessage) {
    const cardElement = document.getElementById(cardId);

    if (!cardElement || typeof html2canvas === 'undefined') {
        console.error('Elemento de tarjeta no encontrado o html2canvas no cargado.');
        return;
    }

    const elementsToHide = cardElement.querySelectorAll('.action-buttons');
    elementsToHide.forEach(el => el.classList.add('d-none'));

    const cleanName = customerName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const fileName = `rifa_${raffleNumber}_${cleanName}.png`;

    const options = {
        allowTaint: true,
        useCORS: true,
        backgroundColor: '#ffffff',
        scale: 2
    };

    html2canvas(cardElement, options).then(canvas => {
        elementsToHide.forEach(el => el.classList.remove('d-none'));

        const image = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = image;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        let waUrl;
        if (!customerPhone) {
            waUrl = `https://wa.me/?text=${waMessage}`;
        } else {
            waUrl = `https://wa.me/506${customerPhone}?text=${waMessage}`;
        }
        window.open(waUrl, '_blank');

        console.log('Imagen descargada. Se abrió WhatsApp. Adjuntar la imagen manualmente.');

    }).catch(error => {
        elementsToHide.forEach(el => el.classList.remove('d-none'));
        console.error('Error al generar la imagen:', error);
    });
}


// --- INICIALIZACIÓN ---

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar el precio de la rifa (solo necesario si no se inyecta directamente)
    rafflePrice = getRafflePrice();
    
    // Asegurar que el estado inicial se renderice
    updateFormDisplays(rafflePrice);
    
    // Inicializar el estado visual de los botones que no están vendidos, 
    // asegurando que tengan la clase de borde correcta.
    document.querySelectorAll('.number-button[data-sold="false"]').forEach(button => {
        // Asumimos que inicialmente no están seleccionados, por lo que aplicamos el estilo "disponible" (false)
        // La función updateButtonStyles manejará si se deben agregar o no las clases de borde.
        updateButtonStyles(button, false, false);
    });

    window.filterCards(); 
});

})();

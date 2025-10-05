// FIX 1: Se elimina la inicialización explícita de `new bootstrap.Modal(...)` si ya se usa `data-bs-toggle`. 
// Esto previene errores de inicialización si el script se ejecuta antes de que bootstrap.bundle.min.js termine de cargar.
// Dejamos las variables como referencia para un uso posterior más seguro.
const raffleInfoModalElement = document.getElementById('raffle-info-modal-bs');
const selectionModalElement = document.getElementById('selection-modal-bs');
const editModalElement = document.getElementById('edit-modal-bs');
const zoomModalElement = document.getElementById('image-zoom-modal-bs'); 
const cancelConfirmModalElement = document.getElementById('cancel-confirm-modal-bs'); // NEW: Referencia al nuevo modal

// Almacenamiento de números seleccionados (azul pastel)
let selectedNumbers = [];
const numbersGrid = document.getElementById('numbers-grid');

// Elementos del formulario de escritorio
const desktopSelectedNumbersDisplay = document.getElementById('selected_numbers_display');
const desktopSelectedNumbersInput = document.getElementById('selected_numbers_input');
const desktopSubmitButton = document.getElementById('submit_button');

// Elementos del modal de selección (Mobile)
const modalSelectedNumbersDisplay = document.getElementById('modal_selected_numbers_display');
const modalSelectedNumbersInput = document.getElementById('modal_selected_numbers_input');
const modalSubmitButton = document.getElementById('modal_submit_button');

// Función de actualización de estilos de botones
function updateButtonStyles(button, isSelectedNow, isSold) {
    // Remover clases de color (siempre mejor remover antes de añadir)
    button.classList.remove('bg-pastel-blue', 'text-blue-800', 'bg-pastel-green', 'text-green-800');
    
    // Obtener el estado de cancelación del botón
    // Nota: La clase 'bg-green-500' es usada para el estado 'Cancelado' por el Superusuario en Jinja
    const isCanceled = button.classList.contains('bg-green-500') && button.dataset.sold === 'true'; 

    if (isSold) {
         // Si está vendido y cancelado (verde sólido)
         if (isCanceled && !isSelectedNow) {
            button.classList.add('bg-green-500', 'text-white', 'cursor-not-allowed', 'hover:shadow-inner');
            button.disabled = true;
         } else {
            // Estilo de Vendido (rojo pastel)
            button.classList.add('bg-pastel-red', 'text-red-800', 'cursor-not-allowed', 'hover:shadow-inner');
            button.disabled = true;
         }
    } else if (isSelectedNow) {
        button.classList.add('bg-pastel-blue', 'text-blue-800'); // Azul Pastel: Seleccionado
        button.disabled = false;
    } else {
        button.classList.add('bg-pastel-green', 'text-green-800', 'hover:bg-green-300', 'hover:shadow-md'); // Verde Pastel: Disponible
        button.disabled = false;
    }
}

function updateSelectionState() {
    // 1. Actualizar el display y los inputs ocultos (Escritorio y Móvil)
    const isSelected = selectedNumbers.length > 0;
    
    selectedNumbers.sort((a, b) => parseInt(a) - parseInt(b));
    const displayValue = isSelected ? selectedNumbers.join(', ') : 'Ninguno';
    const inputValue = isSelected ? selectedNumbers.join(',') : '';

    // Botones y estado de envío
    const submitClasses = ['bg-indigo-600', 'hover:bg-indigo-700', 'focus:ring-indigo-500'];
    const disabledClasses = ['bg-gray-400', 'hover:bg-gray-500', 'focus:ring-gray-500'];
    
    [desktopSubmitButton, modalSubmitButton].forEach(btn => {
        if (btn) { // Verificar si el botón existe antes de manipularlo
            btn.disabled = !isSelected;
            
            // Toggle de clases de color
            if (isSelected) {
                btn.classList.add(...submitClasses);
                btn.classList.remove(...disabledClasses);
            } else {
                btn.classList.add(...disabledClasses);
                btn.classList.remove(...submitClasses);
            }
        }
    });
    
    // Actualizar displays
    if (desktopSelectedNumbersDisplay) desktopSelectedNumbersDisplay.textContent = displayValue;
    if (desktopSelectedNumbersInput) desktopSelectedNumbersInput.value = inputValue;
    if (modalSelectedNumbersDisplay) modalSelectedNumbersDisplay.textContent = displayValue;
    if (modalSelectedNumbersInput) modalSelectedNumbersInput.value = inputValue;

    // 2. Aplicar/remover estilos de selección en la grilla
    numbersGrid.querySelectorAll('.number-button').forEach(button => {
        const number = button.dataset.number;
        const isSelectedNow = selectedNumbers.includes(number);
        const isSold = button.dataset.sold === 'true';

        updateButtonStyles(button, isSelectedNow, isSold);
    });
}

numbersGrid.addEventListener('click', (e) => {
    // FIX 2: Simplificación del listener. Si el target tiene la clase 'number-button' o es su hijo directo, funciona.
    let button = e.target.closest('.number-button');
    
    if (!button) return; 
    
    const number = button.dataset.number;
    const isSold = button.dataset.sold === 'true';

    if (isSold) return;

    const index = selectedNumbers.indexOf(number);

    if (index > -1) {
        // Deseleccionar
        selectedNumbers.splice(index, 1);
    } else {
        // Seleccionar
        selectedNumbers.push(number);
    }

    updateSelectionState();
});

// --- Lógica de Zoom (NEW) ---

let zoomLevel = 1; 

function openZoomModal(src) {
    const imgElement = document.getElementById('zoom-image');
    imgElement.src = src;
    imgElement.style.transform = 'scale(1)'; // Reset zoom
    zoomLevel = 1; // Reset zoom level
    // El modal se abre automáticamente con data-bs-toggle
}

function handleZoom(direction) {
    // direction: 1 for zoom in, -1 for zoom out
    const step = 0.2;
    const minZoom = 1;
    const maxZoom = 3;

    zoomLevel += direction * step;

    if (zoomLevel < minZoom) zoomLevel = minZoom;
    if (zoomLevel > maxZoom) zoomLevel = maxZoom;
    
    const imgElement = document.getElementById('zoom-image');
    imgElement.style.transform = `scale(${zoomLevel})`;
}

// --- Lógica del Modal de Edición/Liberación (BS) ---

function openEditModal(selectionIds, numbersList, customerName, customerPhone) {
    // Cargar datos en los inputs ocultos y de solo lectura
    document.getElementById('modal-selection-ids').value = selectionIds;
    document.getElementById('modal-number-display').textContent = numbersList;
    
    // Cargar datos en los campos de visualización del cliente (FIX: se asegura la carga aquí)
    document.getElementById('customer_name_display').value = customerName;
    document.getElementById('customer_phone_display').value = customerPhone;
    
    document.getElementById('edit_password').value = ''; // Limpiar campo de contraseña
    
    // Mostrar el modal (usando la API de Bootstrap JS)
    if (typeof bootstrap !== 'undefined' && editModalElement) {
        const modalInstance = bootstrap.Modal.getInstance(editModalElement) || new bootstrap.Modal(editModalElement);
        modalInstance.show();
    }
}

// --- NUEVA FUNCIÓN: CONFIRMACIÓN DE CANCELACIÓN (USA MODAL DE BOOTSTRAP) ---

function confirmCancellation(selectionIds, customerName, isCanceled) {
    // CORRECCIÓN: Si ya está cancelado (isCanceled == 1), no hacemos nada o mostramos un mensaje de consola.
    if (isCanceled === 1) {
        console.log(`La selección para "${customerName}" ya está marcada como CANCELADA.`); 
        // El botón ya debería estar deshabilitado en el HTML
        return;
    }
    
    // 1. Cargar datos en el Modal de Confirmación
    const numberDisplay = document.getElementById('modal-cancel-customer-name');
    const idsInput = document.getElementById('modal-cancel-selection-ids');
    
    if (numberDisplay) numberDisplay.textContent = customerName;
    if (idsInput) idsInput.value = selectionIds;

    // 2. Mostrar el modal (usando la API de Bootstrap JS)
    if (typeof bootstrap !== 'undefined' && cancelConfirmModalElement) {
        const modalInstance = bootstrap.Modal.getInstance(cancelConfirmModalElement) || new bootstrap.Modal(cancelConfirmModalElement);
        modalInstance.show();
    }
}

// Función para alternar la visibilidad de la contraseña
function togglePasswordVisibility(fieldId) {
    const field = document.getElementById(fieldId);
    const icon = document.getElementById(`toggle_${fieldId}_icon`);
    
    if (field.type === 'password') {
        field.type = 'text';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        field.type = 'password';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}

// --- NUEVA FUNCIÓN: Filtrar tarjetas de números vendidos ---
function filterCards() {
    const searchInput = document.getElementById('search-input');
    const filterText = searchInput.value.toLowerCase().trim();
    const cardsContainer = document.getElementById('search-results-container');
    
    // Verificar si el contenedor existe
    if (!cardsContainer) {
        console.error('El contenedor de resultados de búsqueda no existe.');
        return;
    }

    const cards = cardsContainer.querySelectorAll('.search-card');

    cards.forEach(card => {
        // Obtener los datos almacenados en los atributos data-
        const name = card.dataset.name || '';
        const phone = card.dataset.phone || '';
        // Los números vienen como "01,05,12" (eliminando espacios)
        const numbers = card.dataset.numbers || ''; 

        let matches = false;

        if (filterText.length > 0) {
            // Verificar si el texto coincide con el nombre
            if (name.includes(filterText)) {
                matches = true;
            }
            // Verificar si el texto coincide con el teléfono
            else if (phone.includes(filterText)) {
                matches = true;
            }
            // Verificar si el texto coincide con un número de rifa exacto (ej. "05")
            // Buscamos si el texto (ej. "05") está dentro de la lista de números ("01,05,12")
            // También chequeamos por números de un solo dígito para que el buscador sea más flexible
            else if (numbers.includes(filterText)) {
                matches = true;
            }
        } else {
            // Si el campo de búsqueda está vacío, mostrar todas las tarjetas
            matches = true;
        }

        // Mostrar u ocultar la tarjeta
        if (matches) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// Asegurar que el estado inicial se renderice
document.addEventListener('DOMContentLoaded', () => {
    updateSelectionState();
    // Ejecutar filtro inicial si hay texto precargado (aunque no debería)
    filterCards(); 
});

// detall_rifa.js (Lógica JS de Selección/Exportación - Lógica de Edición/Cancelación Eliminada)
(function() {

// --- VARIABLES GLOBALES ---
window.deferredPrompt = undefined; 
window.selectedNumbers = [];

// --- ELEMENTOS DEL DOM ---
const numbersGrid = document.getElementById('numbers-grid');
const floatingSelectButton = document.getElementById('floating-select-button');

const desktopSelectedNumbersDisplay = document.getElementById('selected_numbers_display');
const desktopSelectedNumbersInput = document.getElementById('selected_numbers_input');
const desktopSubmitButton = document.getElementById('submit_button');
const desktopTotalAmount = document.getElementById('desktop_total_amount');

const modalSelectedNumbersDisplay = document.getElementById('modal_selected_numbers_display');
const modalSelectedNumbersInput = document.getElementById('modal_selected_numbers_input');
const modalSubmitButton = document.getElementById('modal_submit_button');
const modalTotalAmount = document.getElementById('modal_total_amount');

let rafflePrice = 0;

// --- FUNCIONES DE UTILIDAD ---

function getRafflePrice() {
    // CORRECCIÓN: Se lee el precio directamente de un input oculto para garantizar
    // que el valor sea exacto y no dependa de la estructura del DOM.
    const priceInput = document.getElementById('raffle_price_input');
    if (priceInput && priceInput.value) {
        const price = parseFloat(priceInput.value);
        // Si el parseo falla, retorna 0 para evitar errores de cálculo.
        return isNaN(price) ? 0 : price;
    }
    
    // Valor de respaldo SOLO si el input no se encuentra.
    console.error("Error: Elemento #raffle_price_input no encontrado. Usando precio de respaldo.");
    return 1000.00;
}

function updateFormDisplays(price) {
    const selected = window.selectedNumbers;
    const isSelected = selected.length > 0;
    
    selected.sort((a, b) => parseInt(a) - parseInt(b));
    const displayStr = isSelected ? selected.join(', ') : 'Ninguno';
    const displayCount = selected.length;
    const inputValue = isSelected ? selected.join(',') : '';
    const totalAmount = displayCount * price; 
    
    const totalDisplayFormatted = totalAmount.toLocaleString('es-CR', { 
        style: 'currency', 
        currency: 'CRC',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2 
    });
    
    if (desktopSelectedNumbersDisplay) desktopSelectedNumbersDisplay.textContent = displayStr;
    if (modalSelectedNumbersDisplay) modalSelectedNumbersDisplay.textContent = displayStr;
    if (desktopSelectedNumbersInput) desktopSelectedNumbersInput.value = inputValue;
    if (modalSelectedNumbersInput) modalSelectedNumbersInput.value = inputValue;

    if (desktopTotalAmount) desktopTotalAmount.textContent = isSelected ? `(Total: ${totalDisplayFormatted})` : '';
    if (modalTotalAmount) modalTotalAmount.textContent = isSelected ? `(Total: ${totalDisplayFormatted})` : '';

    [desktopSubmitButton, modalSubmitButton].forEach(btn => {
        if (btn) {
            btn.disabled = !isSelected;
            btn.innerHTML = isSelected 
                ? `<i class="fas fa-shopping-cart me-2"></i> Comprar ${displayCount} Núm. ${totalDisplayFormatted}` 
                : `<i class="fas fa-hand-pointer me-2"></i> Seleccione Números`;
        }
    });

    if (floatingSelectButton) {
        floatingSelectButton.disabled = !isSelected;
        floatingSelectButton.innerHTML = isSelected
            ? `<i class="fas fa-shopping-cart me-2"></i> Comprar ${displayCount} Núm. ${totalDisplayFormatted}`
            : `<i class="fas fa-hand-pointer me-2"></i> Seleccionar Números`;
    }
}

function updateButtonStyles(button, isSelectedNow, isSold) {
    const DYNAMIC_COLOR_CLASSES = [
        'bg-pastel-green', 'text-green-800', 'hover:bg-green-300', 'border-green-300', 
        'bg-pastel-blue', 'text-blue-800', 'hover:bg-blue-300', 'border-blue-300',
        'bg-pastel-red', 'text-red-800', 'border-red-700'
    ];

    button.classList.remove(...DYNAMIC_COLOR_CLASSES);
    
    // El color de Cancelado (Verde Sólido) se aplica en Jinja, lo respetamos.
    const isCanceledFromHTML = button.classList.contains('bg-green-500'); 
    
    if (isSold || isCanceledFromHTML) {
        button.disabled = true;
        // Si está vendido (no cancelado), aseguramos el color rojo pastel
        if (!isCanceledFromHTML) {
            button.classList.add('bg-pastel-red', 'text-red-800', 'border-red-700');
        }
        return;
    } 
    
    // Si no está vendido/cancelado, manejamos el estado de selección temporal
    if (isSelectedNow) {
        button.classList.add('bg-pastel-blue', 'text-blue-800', 'hover:bg-blue-300', 'border-blue-300'); 
    } else {
        button.classList.add('bg-pastel-green', 'text-green-800', 'hover:bg-green-300', 'border-green-300'); 
    }
    
    if (!button.classList.contains('border')) {
        button.classList.add('border');
    }
}

// --- MANEJADORES DE EVENTOS ---

if (numbersGrid) {
    numbersGrid.addEventListener('click', function(e) {
        const button = e.target.closest('.number-button');
        if (!button) return; 
        
        const number = button.dataset.number;
        const isSold = button.dataset.sold === 'true'; 

        if (isSold) return;

        const index = window.selectedNumbers.indexOf(number);

        if (index > -1) {
            window.selectedNumbers.splice(index, 1);
            updateButtonStyles(button, false, isSold);
        } else {
            window.selectedNumbers.push(number);
            updateButtonStyles(button, true, isSold);
        }

        updateFormDisplays(rafflePrice);
    });
}

// --- FUNCIONES GLOBALES (Llamadas desde HTML) ---

window.togglePasswordVisibility = function(id) {
    const input = document.getElementById(id);
    const icon = document.getElementById(`toggle_${id}_icon`);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    }
}

window.returnToSelection = function() {
    // Se ejecuta al cerrar el modal de selección para asegurar el estado
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
    window.zoomLevel = window.zoomLevel || 1;
    const step = 0.2;
    window.zoomLevel += direction * step;
    window.zoomLevel = Math.max(1, Math.min(window.zoomLevel, 3));
    
    const imgElement = document.getElementById('zoom-image');
    if (imgElement) {
        imgElement.style.transform = `scale(${window.zoomLevel})`;
    }
}


// MEJORA: Función de filtrado con contador y mensaje de "no resultados"
window.filterCards = function() {
    const searchInput = document.getElementById('search-input');
    const filterText = searchInput.value.toLowerCase().trim();
    const cardsContainer = document.getElementById('search-results-container');
    const noResultsMessage = document.getElementById('no-results-message');
    const resultsCountSpan = document.getElementById('results-count');
    
    if (!cardsContainer) return;

    const cards = cardsContainer.querySelectorAll('.search-card');
    let visibleCount = 0;

    cards.forEach(card => {
        const name = card.dataset.name || '';
        const phone = card.dataset.phone || '';
        const numbers = card.dataset.numbers || ''; 
        
        // Convertimos el texto filtrado a una cadena sin espacios ni comas para la búsqueda de números
        const normalizedFilter = filterText.replace(/[^a-z0-9]/g, '');

        const matches = name.includes(filterText) || phone.includes(filterText) || numbers.includes(normalizedFilter);

        if (matches) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    // Actualizar contador
    if(resultsCountSpan) {
        resultsCountSpan.textContent = `${visibleCount} / ${cards.length} mostrados`;
    }

    // Mostrar u ocultar mensaje de no resultados
    if (noResultsMessage) {
        if (visibleCount === 0 && filterText.length > 0) {
            noResultsMessage.classList.remove('d-none');
        } else {
            noResultsMessage.classList.add('d-none');
        }
    }
}

// --- Lógica PWA ---
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    window.deferredPrompt = e;
    const installButton = document.getElementById('install-pwa-button');
    if (installButton) {
        installButton.style.display = 'block';
        installButton.addEventListener('click', () => {
            if (window.deferredPrompt) {
                installButton.style.display = 'none';
                window.deferredPrompt.prompt();
                window.deferredPrompt.userChoice.then(() => {
                    window.deferredPrompt = null;
                });
            }
        });
    }
});

// --- Lógica de Exportar a PNG ---
window.exportCardToPng = function(cardId, customerName, raffleNumber, customerPhone, waMessage) {
    const cardElement = document.getElementById(cardId);
    if (!cardElement || typeof html2canvas === 'undefined') return;

    const elementsToHide = cardElement.querySelectorAll('.action-buttons');
    elementsToHide.forEach(el => el.classList.add('d-none'));

    const cleanName = customerName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const fileName = `rifa_${raffleNumber}_${cleanName}.png`;

    html2canvas(cardElement, { allowTaint: true, useCORS: true, scale: 2 }).then(canvas => {
        elementsToHide.forEach(el => el.classList.remove('d-none'));
        const image = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = image;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        const waUrl = customerPhone 
            ? `https://wa.me/506${customerPhone}?text=${waMessage}`
            : `https://wa.me/?text=${waMessage}`;
        window.open(waUrl, '_blank');
    }).catch(error => {
        elementsToHide.forEach(el => el.classList.remove('d-none'));
        console.error('Error al generar la imagen:', error);
    });
}

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    rafflePrice = getRafflePrice();
    updateFormDisplays(rafflePrice);
    
    document.querySelectorAll('.number-button[data-sold="false"]').forEach(button => {
        updateButtonStyles(button, false, false);
    });

    // Llamar al filtro al cargar para inicializar el contador
    window.filterCards(); 
});

})();

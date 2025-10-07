// detalle_btns.js (Lógica específica para botones de acción en detalle_rifa.html)

/**
 * Muestra el modal de eliminación y precarga los datos de la selección.
 * @param {string} selectionIds - Lista de IDs de selección separada por comas (ej: "12,13,14").
 * @param {string} customerName - Nombre del cliente.
 * @param {string} numbersList - Números seleccionados (ej: "45, 46, 47").
 */
window.openDeleteModal = function(selectionIds, customerName, numbersList) {
    // CRÍTICO: Obtener el ID de la rifa desde el campo oculto principal
    const raffleIdInput = document.getElementById('raffle_id_input');
    const raffleId = raffleIdInput ? raffleIdInput.value : null;

    // 1. Asegurar que selectionIds sea un string, aunque esté vacío
    const idsString = String(selectionIds);

    // 2. Asignar los IDs de selección al campo oculto del modal
    const idsInput = document.getElementById('modal-delete-ids');
    if (idsInput) {
        idsInput.value = idsString;
    } else {
        console.error("Error JS: Elemento #modal-delete-ids no encontrado.");
    }
    
    // 3. Asignar la URL de acción del formulario
    const deleteForm = document.getElementById('delete-selection-form');
    if (deleteForm && raffleId) {
        // La acción POST debe ir a /rifas/<id_de_rifa>
        deleteForm.action = `/rifas/${raffleId}`; 
    } else {
        console.error("Error JS: Formulario #delete-selection-form no encontrado o Raffle ID faltante.");
    }

    // 4. Actualizar elementos visuales del modal
    document.getElementById('modal-delete-numbers-display').textContent = numbersList;
    document.getElementById('modal-delete-name-display').textContent = customerName;
    document.getElementById('delete_password_input').value = ''; // Limpiar campo de contraseña
    
    // La visibilidad de la contraseña es manejada por la función togglePasswordVisibility
};

// Función para alternar visibilidad de contraseña (usada en varios modales)
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

// Función para marcar como cancelado (solo Superusuario)
// CRÍTICO: Flask ya maneja esta acción directamente con el <form> en detalle_rifa.html, 
// por lo que no necesita una función JS de apoyo, solo la validación del backend.

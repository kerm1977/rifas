// ver_rifas.js (Lógica JS de Modales de Ganador/Eliminar)
// JS para manejar el modal de anunciar ganador
function prepareWinnerModal(raffleId, raffleName, winnersAnnounced) {
    document.getElementById('winner-raffle-id').value = raffleId;
    document.getElementById('winner-raffle-name').textContent = raffleName;
    
    // CORRECCIÓN: Usamos la ruta hardcodeada '/rifas/anunciar_ganador/' para que funcione si el JS se carga como archivo estático.
    document.getElementById('winner-form').action = '/rifas/anunciar_ganador/' + raffleId;
    
    // Limpiar inputs al abrir
    document.getElementById('num_winners').value = '1';
    document.getElementById('winning_numbers_input').value = '';
    
    const removeBtn = document.getElementById('btn-remove-winners');
    const announceBtn = document.getElementById('btn-announce');
    const inputContainer = document.getElementById('winner-input-container');
    const instructions = document.getElementById('modal-instructions');
    
    if (winnersAnnounced) {
        // Mostrar botón de eliminar y ocultar entradas
        removeBtn.classList.remove('d-none'); // Mostrar botón de eliminar
        announceBtn.classList.add('d-none'); // Ocultar botón de anunciar
        inputContainer.classList.add('d-none'); // Ocultar campos de entrada
        
        instructions.innerHTML = `Ya hay ganadores anunciados para *${raffleName}*. Presione **Eliminar Ganadores** para resetear la rifa y anunciar nuevos.`;
    } else {
        // Ocultar botón de eliminar y mostrar entradas
        removeBtn.classList.add('d-none'); // Ocultar botón de eliminar
        announceBtn.classList.remove('d-none'); // Mostrar botón de anunciar
        inputContainer.classList.remove('d-none'); // Mostrar campos de entrada
        
        instructions.innerHTML = `Seleccione el número de ganadores para la rifa <span id="winner-raffle-name" class="font-extrabold text-red-800">${raffleName}</span>.`;
    }
    
    // Resetear la acción a 'announce' por defecto al abrir
    setWinnerAction('announce');
}

// Función para establecer la acción del formulario de ganador
function setWinnerAction(action) {
    document.getElementById('winner-action').value = action;
    
    // Si la acción es 'remove_winners', el input de números ya no es requerido para el submit
    const input = document.getElementById('winning_numbers_input');
    if (action === 'remove_winners') {
        input.removeAttribute('required');
    } else {
        input.setAttribute('required', 'required');
    }
}

// NUEVA FUNCIÓN: Prepara el modal de eliminación de rifa
function prepareDeleteModal(raffleId, raffleName) {
    // Establecer el ID de la rifa en el formulario oculto
    document.getElementById('raffle-to-delete-id').value = raffleId;
    
    // Mostrar el nombre de la rifa en el encabezado
    document.getElementById('raffle-to-delete-name').textContent = raffleName;
    
    // CORRECCIÓN: Usamos la ruta hardcodeada '/rifas/eliminar/'
    const deleteForm = document.getElementById('delete-raffle-form');
    if (deleteForm) {
        deleteForm.action = '/rifas/eliminar/' + raffleId;
    } else {
        console.error("Error: delete-raffle-form no encontrado.");
    }
    
    // Asegurar que el checkbox esté desmarcado al abrir
    document.getElementById('confirm-delete-checkbox').checked = false;
}

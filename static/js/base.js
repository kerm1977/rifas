// base.js (Lógica JS Global y Navbar)
function now_year() {
    return new Date().getFullYear();
}

// --- Lógica del Navbar (Puro JS) ---
document.getElementById('nav-toggler').addEventListener('click', function() {
    // CORRECCIÓN: Apuntar al contenedor del menú móvil correcto ('nav-menu-mobile')
    const menu = document.getElementById('nav-menu-mobile');
    // CORRECCIÓN: Usar la clase 'd-none' de Bootstrap para mostrar/ocultar el menú
    menu.classList.toggle('d-none'); 
});

// Ocultar menú si el tamaño de la pantalla es grande
window.addEventListener('resize', function() {
    // CORRECCIÓN: Apuntar también aquí al menú móvil
    const menu = document.getElementById('nav-menu-mobile');
    // 1024px es el breakpoint 'lg'
    if (window.innerWidth >= 1024) {
        // Aseguramos que el menú móvil siempre se oculte en vistas de escritorio
        menu.classList.add('d-none');
    }
});

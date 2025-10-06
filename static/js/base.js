// base.js (Lógica JS Global y Navbar)
function now_year() {
    return new Date().getFullYear();
}

// --- Lógica del Navbar (Puro JS) ---
document.getElementById('nav-toggler').addEventListener('click', function() {
    const menu = document.getElementById('nav-menu');
    // Usamos 'active' para cambiar entre display: none y display: flex/column,
    // que se define en base.css
    menu.classList.toggle('active'); 
});

// Ocultar menú si el tamaño de la pantalla es grande
window.addEventListener('resize', function() {
    const menu = document.getElementById('nav-menu');
    // 1024px es el breakpoint 'lg' de Tailwind
    if (window.innerWidth >= 1024) {
        // Aseguramos que el estado 'active' (que fuerza flex/column en móvil)
        // se remueva en escritorio, permitiendo que el media query de CSS tome control.
        menu.classList.remove('active');
    }
});

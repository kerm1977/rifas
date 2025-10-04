
function now_year() {
    return new Date().getFullYear();
}

// --- Lógica del Navbar (Puro JS) ---
document.getElementById('nav-toggler').addEventListener('click', function() {
    const menu = document.getElementById('nav-menu');
    menu.classList.toggle('active');
});

// Ocultar menú si el tamaño de la pantalla es grande
window.addEventListener('resize', function() {
    const menu = document.getElementById('nav-menu');
    if (window.innerWidth >= 1024) {
        menu.classList.remove('active');
    }
});
const appState = {
    sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true' || false
};

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-bs-theme');
    const next = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-bs-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon();
}

function updateThemeIcon() {
    const themeToggle = document.querySelector('.theme-toggle');
    const current = document.documentElement.getAttribute('data-bs-theme');
    themeToggle.textContent = current === 'dark' ? '☀️' : '🌙';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebarMenu');
    const brandText = document.getElementById('brandText');
    const toggleBtn = document.getElementById('sidebarToggle');
    sidebar.classList.toggle('collapsed');
    appState.sidebarCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebarCollapsed', appState.sidebarCollapsed);
    if (brandText) {
        brandText.style.display = appState.sidebarCollapsed ? 'none' : 'inline';
    }
    toggleBtn.setAttribute('aria-expanded', !appState.sidebarCollapsed);
    // Refresh tooltip
    const tooltip = bootstrap.Tooltip.getInstance(toggleBtn);
    if (tooltip) {
        tooltip.dispose();
    }
    new bootstrap.Tooltip(toggleBtn);
}

document.addEventListener('DOMContentLoaded', function() {
    updateThemeIcon();
    // Set current year in footer
    document.getElementById('currentYear').textContent = new Date().getFullYear();
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebarMenu');
    const brandText = document.getElementById('brandText');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleSidebar);
        const tooltip = new bootstrap.Tooltip(toggleBtn);
    }
    // Apply sidebar state
    if (appState.sidebarCollapsed) {
        sidebar.classList.add('collapsed');
        if (brandText) brandText.style.display = 'none';
        toggleBtn.setAttribute('aria-expanded', 'false');
    }
    // Restore transitions
    sidebar.style.transition = 'width 0.3s ease';
    // Keyboard accessibility for theme toggle
    const themeToggle = document.querySelector('.theme-toggle');
    themeToggle.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            toggleTheme();
        }
    });
});

// Select all alerts that do not have the 'no-auto-dismiss' class and dismiss them after 4 seconds
document.querySelectorAll('.alert:not(.no-auto-dismiss)').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500); // Remove after fade-out
    }, 4000); // Auto-dismiss after 3 seconds
  });
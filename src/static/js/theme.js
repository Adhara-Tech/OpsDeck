/**
 * OpsDeck Theme Manager
 * Handles dark/light mode switching with localStorage persistence
 * and system preference detection.
 */
const ThemeManager = (function() {
    'use strict';

    const STORAGE_KEY = 'opsdeck-theme';
    const THEME_DARK = 'dark';
    const THEME_LIGHT = 'light';

    /**
     * Get the user's system color scheme preference
     * @returns {string} 'dark' or 'light'
     */
    function getSystemPreference() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return THEME_DARK;
        }
        return THEME_LIGHT;
    }

    /**
     * Get the stored theme preference from localStorage
     * @returns {string|null} Stored theme or null
     */
    function getStoredTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            // localStorage not available (private browsing, etc.)
            return null;
        }
    }

    /**
     * Store the theme preference in localStorage
     * @param {string} theme - Theme to store
     */
    function setStoredTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            // localStorage not available
        }
    }

    /**
     * Get the current active theme (stored > system preference)
     * @returns {string} Current theme
     */
    function getCurrentTheme() {
        const stored = getStoredTheme();
        if (stored) {
            return stored;
        }
        return getSystemPreference();
    }

    /**
     * Apply theme to the document
     * @param {string} theme - Theme to apply
     */
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);

        // Update toggle button icon
        updateToggleIcon(theme);

        // Dispatch custom event for other components (e.g., charts)
        window.dispatchEvent(new CustomEvent('themechange', {
            detail: { theme: theme }
        }));
    }

    /**
     * Update the toggle button icon based on current theme
     * @param {string} theme - Current theme
     */
    function updateToggleIcon(theme) {
        const toggle = document.getElementById('themeToggle');
        if (!toggle) return;

        const icon = toggle.querySelector('i');
        if (!icon) return;

        if (theme === THEME_DARK) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            toggle.setAttribute('title', 'Switch to light mode');
            toggle.setAttribute('aria-label', 'Switch to light mode');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
            toggle.setAttribute('title', 'Switch to dark mode');
            toggle.setAttribute('aria-label', 'Switch to dark mode');
        }
    }

    /**
     * Toggle between light and dark themes
     */
    function toggle() {
        const current = getCurrentTheme();
        const next = current === THEME_DARK ? THEME_LIGHT : THEME_DARK;
        setStoredTheme(next);
        applyTheme(next);
    }

    /**
     * Initialize theme on page load
     */
    function init() {
        // Apply theme immediately (should already be set by inline FOUC script)
        const theme = getCurrentTheme();
        applyTheme(theme);

        // Listen for system preference changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)')
                .addEventListener('change', function(e) {
                    // Only auto-switch if user hasn't set a preference
                    if (!getStoredTheme()) {
                        applyTheme(e.matches ? THEME_DARK : THEME_LIGHT);
                    }
                });
        }

        // Set up toggle button click handler when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupToggleButton);
        } else {
            setupToggleButton();
        }
    }

    /**
     * Set up the toggle button click handler
     */
    function setupToggleButton() {
        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                ThemeManager.toggle();
            });
        }
    }

    // Initialize immediately
    init();

    // Public API
    return {
        toggle: toggle,
        getCurrentTheme: getCurrentTheme,
        applyTheme: applyTheme,
        DARK: THEME_DARK,
        LIGHT: THEME_LIGHT
    };
})();

/**
 * OpsDeck Toast Notification System
 *
 * Modern toast notifications to replace standard flash messages
 * with better UX and animations.
 */

const Toast = (function() {
    'use strict';

    const config = {
        duration: 4000,
        position: 'top-right', // top-right, top-left, bottom-right, bottom-left
        maxToasts: 5
    };

    const icons = {
        success: 'check-circle',
        error: 'times-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle',
        danger: 'times-circle'
    };

    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6',
        danger: '#ef4444'
    };

    /**
     * Initialize toast container if it doesn't exist
     */
    function getContainer() {
        let container = document.getElementById('toast-container');

        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        return container;
    }

    /**
     * Create a toast element
     */
    function createToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = 'custom-toast';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');

        const icon = icons[type] || icons.info;
        const color = colors[type] || colors.info;

        toast.innerHTML = `
            <div class="toast-icon" style="color: ${color};">
                <i class="fas fa-${icon}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Close notification">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Close button handler
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            dismissToast(toast);
        });

        return toast;
    }

    /**
     * Show a toast notification
     *
     * @param {string} message - The message to display
     * @param {string} type - Type of notification (success, error, warning, info, danger)
     * @param {number} duration - Duration in milliseconds (0 = persistent)
     */
    function show(message, type = 'info', duration = null) {
        if (!message) return;

        const container = getContainer();
        const toast = createToast(message, type);

        // Limit number of toasts
        const existingToasts = container.querySelectorAll('.custom-toast');
        if (existingToasts.length >= config.maxToasts) {
            dismissToast(existingToasts[0]);
        }

        container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Auto dismiss if duration is set
        const dismissDuration = duration !== null ? duration : config.duration;
        if (dismissDuration > 0) {
            setTimeout(() => {
                dismissToast(toast);
            }, dismissDuration);
        }
    }

    /**
     * Dismiss a toast with animation
     */
    function dismissToast(toast) {
        if (!toast || !toast.classList.contains('custom-toast')) return;

        toast.classList.remove('show');
        toast.classList.add('hide');

        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 300);
    }

    /**
     * Clear all toasts
     */
    function clearAll() {
        const container = document.getElementById('toast-container');
        if (container) {
            const toasts = container.querySelectorAll('.custom-toast');
            toasts.forEach(toast => dismissToast(toast));
        }
    }

    /**
     * Convenience methods
     */
    function success(message, duration) {
        show(message, 'success', duration);
    }

    function error(message, duration) {
        show(message, 'error', duration);
    }

    function warning(message, duration) {
        show(message, 'warning', duration);
    }

    function info(message, duration) {
        show(message, 'info', duration);
    }

    function danger(message, duration) {
        show(message, 'danger', duration);
    }

    // Public API
    return {
        show,
        success,
        error,
        warning,
        info,
        danger,
        clearAll
    };
})();

/**
 * Auto-convert flash messages to toasts on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.alert[role="alert"]');

    flashMessages.forEach(function(alert) {
        // Extract message text
        const message = alert.textContent.trim();

        // Determine type from Bootstrap classes
        let type = 'info';
        if (alert.classList.contains('alert-success')) type = 'success';
        else if (alert.classList.contains('alert-danger')) type = 'error';
        else if (alert.classList.contains('alert-warning')) type = 'warning';
        else if (alert.classList.contains('alert-info')) type = 'info';

        // Show toast
        Toast.show(message, type);

        // Hide original alert
        alert.style.display = 'none';
    });
});

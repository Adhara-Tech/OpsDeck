/**
 * OpsDeck Global Modal System
 * 
 * Promise-based modal utility to replace native alert(), confirm(), and prompt().
 * Uses Bootstrap 5 Modal API for consistent styling.
 */

const OpsDeck = (function () {
    'use strict';

    let modalEl = null;
    let bsModal = null;
    let currentResolve = null;
    let promptInput = null;

    /**
     * Initialize the modal reference (called on first use)
     */
    function init() {
        if (modalEl) return;

        modalEl = document.getElementById('globalModal');
        if (!modalEl) {
            console.error('OpsDeck Modal: #globalModal element not found in DOM');
            return;
        }

        bsModal = new bootstrap.Modal(modalEl, {
            backdrop: 'static',
            keyboard: true
        });

        // Handle modal hidden event
        modalEl.addEventListener('hidden.bs.modal', () => {
            if (currentResolve) {
                // If modal was dismissed without explicit action, resolve with null/false
                currentResolve(null);
                currentResolve = null;
            }
            // Clean up prompt input if present
            if (promptInput) {
                promptInput = null;
            }
        });

        // Handle Escape key for cancel
        modalEl.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && currentResolve) {
                currentResolve(null);
                currentResolve = null;
            }
        });
    }

    /**
     * Get variant class for buttons
     */
    function getButtonClass(variant) {
        const variants = {
            primary: 'btn-primary',
            secondary: 'btn-secondary',
            success: 'btn-success',
            danger: 'btn-danger',
            warning: 'btn-warning',
            info: 'btn-info'
        };
        return variants[variant] || 'btn-primary';
    }

    /**
     * Show an alert modal (single OK button)
     * 
     * @param {Object} options
     * @param {string} options.title - Modal title (default: 'Notice')
     * @param {string} options.body - Modal body text (required)
     * @param {string} options.okText - OK button text (default: 'OK')
     * @param {string} options.variant - Button variant (default: 'primary')
     * @returns {Promise<void>}
     */
    async function showAlert(options = {}) {
        init();
        if (!modalEl) {
            // Fallback to native alert if modal not available
            window.alert(options.body || options);
            return;
        }

        const title = options.title || 'Notice';
        const body = options.body || (typeof options === 'string' ? options : '');
        const okText = options.okText || 'OK';
        const variant = options.variant || 'primary';

        return new Promise((resolve) => {
            currentResolve = resolve;

            document.getElementById('globalModalTitle').textContent = title;
            document.getElementById('globalModalBody').innerHTML = `<p class="mb-0">${body}</p>`;
            document.getElementById('globalModalFooter').innerHTML = `
                <button type="button" class="btn ${getButtonClass(variant)}" id="globalModalOk">
                    ${okText}
                </button>
            `;

            document.getElementById('globalModalOk').addEventListener('click', () => {
                currentResolve = null;
                bsModal.hide();
                resolve();
            }, { once: true });

            bsModal.show();

            // Focus the OK button
            modalEl.addEventListener('shown.bs.modal', () => {
                document.getElementById('globalModalOk')?.focus();
            }, { once: true });
        });
    }

    /**
     * Show a confirmation modal (OK and Cancel buttons)
     * 
     * @param {Object} options
     * @param {string} options.title - Modal title (default: 'Confirm')
     * @param {string} options.body - Modal body text (required)
     * @param {string} options.okText - OK button text (default: 'OK')
     * @param {string} options.cancelText - Cancel button text (default: 'Cancel')
     * @param {string} options.variant - OK button variant (default: 'primary')
     * @returns {Promise<boolean>}
     */
    async function showConfirm(options = {}) {
        init();
        if (!modalEl) {
            // Fallback to native confirm if modal not available
            return window.confirm(options.body || options);
        }

        const title = options.title || 'Confirm';
        const body = options.body || (typeof options === 'string' ? options : 'Are you sure?');
        const okText = options.okText || 'OK';
        const cancelText = options.cancelText || 'Cancel';
        const variant = options.variant || 'primary';

        return new Promise((resolve) => {
            currentResolve = (val) => resolve(val === true ? true : false);

            document.getElementById('globalModalTitle').textContent = title;
            document.getElementById('globalModalBody').innerHTML = `<p class="mb-0">${body}</p>`;
            document.getElementById('globalModalFooter').innerHTML = `
                <button type="button" class="btn btn-secondary" id="globalModalCancel">
                    ${cancelText}
                </button>
                <button type="button" class="btn ${getButtonClass(variant)}" id="globalModalOk">
                    ${okText}
                </button>
            `;

            document.getElementById('globalModalCancel').addEventListener('click', () => {
                currentResolve = null;
                bsModal.hide();
                resolve(false);
            }, { once: true });

            document.getElementById('globalModalOk').addEventListener('click', () => {
                currentResolve = null;
                bsModal.hide();
                resolve(true);
            }, { once: true });

            bsModal.show();

            // Focus the Cancel button (safer default)
            modalEl.addEventListener('shown.bs.modal', () => {
                document.getElementById('globalModalCancel')?.focus();
            }, { once: true });
        });
    }

    /**
     * Show a prompt modal (with input field)
     * 
     * @param {Object} options
     * @param {string} options.title - Modal title (default: 'Input Required')
     * @param {string} options.body - Modal body text/label
     * @param {string} options.placeholder - Input placeholder
     * @param {string} options.defaultValue - Default input value
     * @param {string} options.okText - OK button text (default: 'OK')
     * @param {string} options.cancelText - Cancel button text (default: 'Cancel')
     * @returns {Promise<string|null>} - Returns input value or null if cancelled
     */
    async function showPrompt(options = {}) {
        init();
        if (!modalEl) {
            // Fallback to native prompt if modal not available
            return window.prompt(options.body || options, options.defaultValue || '');
        }

        const title = options.title || 'Input Required';
        const body = options.body || '';
        const placeholder = options.placeholder || '';
        const defaultValue = options.defaultValue || '';
        const okText = options.okText || 'OK';
        const cancelText = options.cancelText || 'Cancel';

        return new Promise((resolve) => {
            currentResolve = resolve;

            const inputId = 'globalModalPromptInput';
            document.getElementById('globalModalTitle').textContent = title;
            document.getElementById('globalModalBody').innerHTML = `
                ${body ? `<p>${body}</p>` : ''}
                <input type="text" class="form-control" id="${inputId}" 
                       placeholder="${placeholder}" value="${defaultValue}">
            `;
            document.getElementById('globalModalFooter').innerHTML = `
                <button type="button" class="btn btn-secondary" id="globalModalCancel">
                    ${cancelText}
                </button>
                <button type="button" class="btn btn-primary" id="globalModalOk">
                    ${okText}
                </button>
            `;

            promptInput = document.getElementById(inputId);

            // Handle Enter key in input
            promptInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    document.getElementById('globalModalOk').click();
                }
            });

            document.getElementById('globalModalCancel').addEventListener('click', () => {
                currentResolve = null;
                bsModal.hide();
                resolve(null);
            }, { once: true });

            document.getElementById('globalModalOk').addEventListener('click', () => {
                const value = promptInput.value;
                currentResolve = null;
                bsModal.hide();
                resolve(value);
            }, { once: true });

            bsModal.show();

            // Focus the input field
            modalEl.addEventListener('shown.bs.modal', () => {
                promptInput?.focus();
                promptInput?.select();
            }, { once: true });
        });
    }

    /**
     * Initialize form confirmation handlers
     * Forms with data-confirm attribute will show confirmation modal before submit
     */
    function initFormConfirmation() {
        document.body.addEventListener('submit', async (e) => {
            const form = e.target;
            const confirmMsg = form.dataset.confirm;

            if (confirmMsg && !form.dataset.confirmed) {
                e.preventDefault();
                e.stopPropagation();

                const confirmed = await showConfirm({
                    title: 'Confirm Action',
                    body: confirmMsg
                });

                if (confirmed) {
                    form.dataset.confirmed = 'true';
                    // Use requestSubmit to trigger native submit with validation
                    if (form.requestSubmit) {
                        form.requestSubmit();
                    } else {
                        form.submit();
                    }
                }
            }
        }, true); // Use capture phase to intercept early

        // Handle buttons/links with data-confirm (for non-form elements)
        document.body.addEventListener('click', async (e) => {
            const el = e.target.closest('[data-confirm]');

            // Skip if it's a form (handled above) or already confirmed
            if (!el || el.tagName === 'FORM' || el.dataset.confirmed) return;

            // Only handle links and buttons that aren't part of a form with data-confirm
            if (el.tagName === 'A' || (el.tagName === 'BUTTON' && !el.form?.dataset.confirm)) {
                e.preventDefault();
                e.stopPropagation();

                const confirmed = await showConfirm({
                    title: 'Confirm Action',
                    body: el.dataset.confirm
                });

                if (confirmed) {
                    el.dataset.confirmed = 'true';
                    el.click();
                    // Clear the confirmed flag after a short delay
                    setTimeout(() => { delete el.dataset.confirmed; }, 100);
                }
            }
        }, true);
    }

    // Initialize form confirmation when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFormConfirmation);
    } else {
        initFormConfirmation();
    }

    // Public API
    return {
        showAlert,
        showConfirm,
        showPrompt
    };
})();

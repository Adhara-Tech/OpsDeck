/**
 * OpsDeck Skeleton Loader Utilities
 *
 * Utilities for managing skeleton loaders during async operations.
 */

const Skeleton = (function() {
    'use strict';

    /**
     * Show a skeleton loader in a container
     *
     * @param {string|HTMLElement} container - Container element or selector
     * @param {string} type - Type of skeleton ('table', 'card', 'list', 'dashboard')
     * @param {Object} options - Configuration options
     */
    function show(container, type = 'table', options = {}) {
        const element = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        if (!element) {
            console.warn('Skeleton: Container not found', container);
            return;
        }

        // Hide existing content
        const existingContent = element.innerHTML;
        element.dataset.skeletonOriginalContent = existingContent;
        element.classList.add('skeleton-loading');

        // Create skeleton based on type
        let skeletonHTML = '';

        switch(type) {
            case 'table':
                skeletonHTML = createTableSkeleton(options);
                break;
            case 'card':
                skeletonHTML = createCardSkeleton(options);
                break;
            case 'list':
                skeletonHTML = createListSkeleton(options);
                break;
            case 'dashboard':
                skeletonHTML = createDashboardSkeleton(options);
                break;
            case 'custom':
                skeletonHTML = options.html || '';
                break;
            default:
                skeletonHTML = createDefaultSkeleton(options);
        }

        element.innerHTML = skeletonHTML;
    }

    /**
     * Hide skeleton loader and restore original content
     *
     * @param {string|HTMLElement} container - Container element or selector
     */
    function hide(container) {
        const element = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        if (!element) {
            console.warn('Skeleton: Container not found', container);
            return;
        }

        const originalContent = element.dataset.skeletonOriginalContent;
        if (originalContent !== undefined) {
            element.innerHTML = originalContent;
            delete element.dataset.skeletonOriginalContent;
        }

        element.classList.remove('skeleton-loading');
    }

    /**
     * Create a table skeleton
     */
    function createTableSkeleton(options = {}) {
        const rows = options.rows || 5;
        const columns = options.columns || 5;
        const showActions = options.showActions !== false;

        let html = '<div class="skeleton-table">';

        for (let i = 0; i < rows; i++) {
            html += '<div class="skeleton-table-row">';

            for (let j = 0; j < columns; j++) {
                html += '<div class="skeleton-table-cell"><div class="skeleton skeleton-text"></div></div>';
            }

            if (showActions) {
                html += '<div class="skeleton-table-cell" style="flex: 0 0 120px;">';
                html += '<div class="d-flex gap-2">';
                html += '<div class="skeleton skeleton-button-sm"></div>';
                html += '<div class="skeleton skeleton-button-sm"></div>';
                html += '</div></div>';
            }

            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    /**
     * Create a card grid skeleton
     */
    function createCardSkeleton(options = {}) {
        const count = options.count || 3;
        const hasImage = options.hasImage !== false;
        const hasActions = options.hasActions !== false;

        let html = '<div class="skeleton-grid">';

        for (let i = 0; i < count; i++) {
            html += '<div class="card">';

            if (hasImage) {
                html += '<div class="skeleton skeleton-card-header"></div>';
            }

            html += '<div class="skeleton-card-body">';
            html += '<div class="skeleton skeleton-title"></div>';
            html += '<div class="skeleton skeleton-text" style="width: 90%;"></div>';
            html += '<div class="skeleton skeleton-text" style="width: 80%;"></div>';
            html += '<div class="skeleton skeleton-text" style="width: 75%;"></div>';

            if (hasActions) {
                html += '<div class="d-flex gap-2 mt-3">';
                html += '<div class="skeleton skeleton-button"></div>';
                html += '<div class="skeleton skeleton-button"></div>';
                html += '</div>';
            }

            html += '</div></div>';
        }

        html += '</div>';
        return html;
    }

    /**
     * Create a list skeleton
     */
    function createListSkeleton(options = {}) {
        const items = options.items || 5;
        const hasAvatar = options.hasAvatar !== false;
        const hasBadge = options.hasBadge !== false;
        const hasActions = options.hasActions !== false;

        let html = '<div class="list-group">';

        for (let i = 0; i < items; i++) {
            html += '<div class="skeleton-list-item list-group-item">';

            if (hasAvatar) {
                html += '<div class="skeleton skeleton-avatar"></div>';
            }

            html += '<div class="flex-grow-1">';
            html += '<div class="d-flex align-items-center mb-2">';
            html += '<div class="skeleton skeleton-text" style="width: 200px; margin-bottom: 0;"></div>';

            if (hasBadge) {
                html += '<div class="skeleton skeleton-badge ms-2"></div>';
            }

            html += '</div>';
            html += '<div class="skeleton skeleton-text-sm" style="width: 60%;"></div>';
            html += '</div>';

            if (hasActions) {
                html += '<div class="d-flex gap-2">';
                html += '<div class="skeleton skeleton-button-sm"></div>';
                html += '</div>';
            }

            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    /**
     * Create a dashboard skeleton
     */
    function createDashboardSkeleton(options = {}) {
        const cards = options.cards || 4;

        let html = '<div class="row">';

        for (let i = 0; i < cards; i++) {
            html += '<div class="col-xl-3 col-md-6 mb-4">';
            html += '<div class="card"><div class="card-body">';
            html += '<div class="d-flex justify-content-between align-items-center mb-3">';
            html += '<div class="skeleton skeleton-text-sm" style="width: 100px;"></div>';
            html += '<div class="skeleton skeleton-avatar-sm"></div>';
            html += '</div>';
            html += '<div class="skeleton skeleton-title" style="width: 80px; height: 2.5rem; margin-bottom: 0.5rem;"></div>';
            html += '<div class="skeleton skeleton-text-sm" style="width: 120px;"></div>';
            html += '</div></div>';
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    /**
     * Create a default skeleton
     */
    function createDefaultSkeleton(options = {}) {
        const lines = options.lines || 5;

        let html = '<div>';
        for (let i = 0; i < lines; i++) {
            const width = 60 + Math.random() * 30; // Random width 60-90%
            html += `<div class="skeleton skeleton-text" style="width: ${width}%;"></div>`;
        }
        html += '</div>';

        return html;
    }

    /**
     * Wrap an async function with skeleton loading
     *
     * @param {string|HTMLElement} container - Container element or selector
     * @param {Function} asyncFn - Async function to execute
     * @param {string} type - Skeleton type
     * @param {Object} options - Skeleton options
     */
    async function wrap(container, asyncFn, type = 'table', options = {}) {
        show(container, type, options);

        try {
            const result = await asyncFn();
            return result;
        } finally {
            hide(container);
        }
    }

    /**
     * Create inline skeleton elements
     *
     * @param {string} type - Type of skeleton element
     * @param {Object} options - Style options
     * @returns {string} HTML string
     */
    function inline(type = 'text', options = {}) {
        const style = options.style || '';
        const className = options.className || '';

        return `<div class="skeleton skeleton-${type} ${className}" style="${style}"></div>`;
    }

    // Public API
    return {
        show,
        hide,
        wrap,
        inline
    };
})();

/**
 * Usage Examples:
 *
 * // Show skeleton while loading data
 * Skeleton.show('#data-container', 'table', { rows: 8, columns: 6 });
 * fetch('/api/data')
 *     .then(response => response.json())
 *     .then(data => {
 *         Skeleton.hide('#data-container');
 *         renderData(data);
 *     });
 *
 * // Or use the wrap helper
 * await Skeleton.wrap('#data-container', async () => {
 *     const response = await fetch('/api/data');
 *     const data = await response.json();
 *     renderData(data);
 * }, 'table', { rows: 8 });
 *
 * // Show card skeleton
 * Skeleton.show('#cards-container', 'card', { count: 4, hasImage: true });
 *
 * // Show list skeleton
 * Skeleton.show('#list-container', 'list', { items: 6, hasAvatar: true });
 *
 * // Show dashboard skeleton
 * Skeleton.show('#dashboard-container', 'dashboard', { cards: 4 });
 *
 * // Create inline skeleton
 * const skeletonHTML = Skeleton.inline('text', { style: 'width: 200px;' });
 */

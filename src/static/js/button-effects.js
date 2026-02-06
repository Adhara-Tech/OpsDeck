/**
 * OpsDeck Button Microinteractions
 *
 * Adds ripple effects and other microinteractions to buttons
 * for enhanced user experience.
 */

(function() {
    'use strict';

    /**
     * Create a ripple effect on button click
     */
    function createRipple(event) {
        const button = event.currentTarget;

        // Don't add ripple to disabled buttons
        if (button.disabled || button.classList.contains('disabled')) {
            return;
        }

        // Remove any existing ripples
        const existingRipple = button.querySelector('.btn-ripple');
        if (existingRipple) {
            existingRipple.remove();
        }

        // Create ripple element
        const ripple = document.createElement('span');
        ripple.classList.add('btn-ripple');

        // Calculate ripple size (largest dimension of button)
        const diameter = Math.max(button.clientWidth, button.clientHeight);
        const radius = diameter / 2;

        // Position ripple at click location
        const rect = button.getBoundingClientRect();
        const x = event.clientX - rect.left - radius;
        const y = event.clientY - rect.top - radius;

        ripple.style.width = ripple.style.height = `${diameter}px`;
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;

        // Add ripple to button
        button.appendChild(ripple);

        // Remove ripple after animation
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    /**
     * Initialize ripple effect on all buttons
     */
    function initRippleEffect() {
        // Select all buttons (except ones that opt-out with .no-ripple class)
        const buttons = document.querySelectorAll('.btn:not(.no-ripple)');

        buttons.forEach(button => {
            // Only add event listener once
            if (!button.dataset.rippleInitialized) {
                button.addEventListener('click', createRipple);
                button.dataset.rippleInitialized = 'true';
            }
        });
    }

    /**
     * Add shake animation to button (useful for form validation errors)
     */
    function shakeButton(button) {
        button.classList.add('btn-shake');

        setTimeout(() => {
            button.classList.remove('btn-shake');
        }, 500);
    }

    /**
     * Add pulse animation to button (useful for important CTAs)
     */
    function pulseButton(button, duration = 5000) {
        button.classList.add('btn-pulse');

        if (duration > 0) {
            setTimeout(() => {
                button.classList.remove('btn-pulse');
            }, duration);
        }
    }

    /**
     * Add loading state to button
     */
    function setButtonLoading(button, loading = true) {
        if (loading) {
            button.classList.add('loading');
            button.disabled = true;

            // Store original text if not already stored
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent.trim();
            }
        } else {
            button.classList.remove('loading');
            button.disabled = false;

            // Restore original text if it was stored
            if (button.dataset.originalText) {
                button.textContent = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    }

    /**
     * Initialize button effects on page load
     */
    document.addEventListener('DOMContentLoaded', function() {
        initRippleEffect();

        // Re-initialize for dynamically added buttons
        // (when new content is loaded via AJAX)
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    initRippleEffect();
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Auto-pulse buttons with data-pulse attribute
        document.querySelectorAll('[data-pulse]').forEach(button => {
            const duration = parseInt(button.dataset.pulse) || 5000;
            pulseButton(button, duration);
        });
    });

    // Expose utility functions globally
    window.ButtonEffects = {
        shake: shakeButton,
        pulse: pulseButton,
        setLoading: setButtonLoading,
        initRipple: initRippleEffect
    };
})();

/**
 * Usage examples:
 *
 * // Shake a button (e.g., on form validation error)
 * const submitBtn = document.getElementById('submit-btn');
 * ButtonEffects.shake(submitBtn);
 *
 * // Pulse a button (e.g., to draw attention to CTA)
 * const ctaBtn = document.getElementById('cta-btn');
 * ButtonEffects.pulse(ctaBtn, 5000); // Pulse for 5 seconds
 *
 * // Set loading state
 * ButtonEffects.setLoading(submitBtn, true);  // Show loading
 * // ... async operation ...
 * ButtonEffects.setLoading(submitBtn, false); // Hide loading
 *
 * // Disable ripple on specific button
 * <button class="btn btn-primary no-ripple">No Ripple</button>
 *
 * // Auto-pulse button on page load
 * <button class="btn btn-primary" data-pulse="5000">Important Action</button>
 */

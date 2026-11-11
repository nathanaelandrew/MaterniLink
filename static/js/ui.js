/* MaterniLink shared UI behaviour: reveal-on-scroll, count-up numbers,
   header shadow, flash toasts and password visibility toggles. */
   (function () {
    'use strict';

    var reduceMotion = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function ready(fn) {
        if (document.readyState !== 'loading') { fn(); }
        else { document.addEventListener('DOMContentLoaded', fn); }
    }

    /* Easing for count-up */
    function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

    /* Animate a number from 0 to its target. Target comes from data-count,
       decimals from data-decimals. The final text is always the exact value. */
    function countUp(el) {
        var raw = el.getAttribute('data-count');
        var target = parseFloat(raw);
        if (isNaN(target)) { return; }
        var decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
        var duration = parseInt(el.getAttribute('data-duration') || '1100', 10);

        if (reduceMotion) { el.textContent = target.toFixed(decimals); return; }

        var start = null;
        function frame(ts) {
            if (start === null) { start = ts; }
            var p = Math.min((ts - start) / duration, 1);
            el.textContent = (target * easeOutCubic(p)).toFixed(decimals);
            if (p < 1) { requestAnimationFrame(frame); }
            else { el.textContent = target.toFixed(decimals); }
        }
        requestAnimationFrame(frame);
    }

    function initReveal() {
        var items = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
        var counters = Array.prototype.slice.call(document.querySelectorAll('[data-count]'));

        /* Stagger children of [data-stagger] containers */
        document.querySelectorAll('[data-stagger]').forEach(function (group) {
            var step = parseInt(group.getAttribute('data-stagger') || '70', 10);
            group.querySelectorAll(':scope > [data-reveal]').forEach(function (child, i) {
                child.style.setProperty('--d', (i * step) + 'ms');
            });
        });

        if (!('IntersectionObserver' in window) || reduceMotion) {
            items.forEach(function (el) { el.classList.add('is-in'); });
            counters.forEach(countUp);
            return;
        }

        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) { return; }
                var el = entry.target;
                el.classList.add('is-in');
                el.querySelectorAll('[data-count]').forEach(countUp);
                if (el.hasAttribute('data-count')) { countUp(el); }
                io.unobserve(el);
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

        items.forEach(function (el) { io.observe(el); });

        /* Counters that are not inside a revealed block animate on their own */
        counters.forEach(function (el) {
            if (!el.closest('[data-reveal]')) { io.observe(el); }
        });
    }

    function initHeader() {
        var header = document.querySelector('.app-header');
        if (!header) { return; }
        function onScroll() { header.classList.toggle('is-scrolled', window.scrollY > 6); }
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
    }

    function initToasts() {
        document.querySelectorAll('.toast-msg').forEach(function (toast, i) {
            function dismiss() {
                if (toast.classList.contains('is-leaving')) { return; }
                toast.classList.add('is-leaving');
                setTimeout(function () { toast.remove(); }, 320);
            }
            var close = toast.querySelector('.toast-msg__close');
            if (close) { close.addEventListener('click', dismiss); }
            setTimeout(dismiss, 5200 + i * 600);
        });
    }

    function initPasswordToggles() {
        document.querySelectorAll('[data-toggle-password]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var input = btn.closest('.input-wrap').querySelector('input');
                if (!input) { return; }
                var show = input.type === 'password';
                input.type = show ? 'text' : 'password';
                btn.classList.toggle('is-visible', show);
                btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
            });
        });
    }

    ready(function () {
        initReveal();
        initHeader();
        initToasts();
        initPasswordToggles();
    });
}());
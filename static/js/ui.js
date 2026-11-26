/* MaterniLink shared UI behaviour.

   Core: reveal-on-scroll, count-up numbers, header shadow, flash toasts and
   password visibility toggles.

   Motion layer (CSS section 26), recreated in plain JS from popular
   21st.dev components (Magic UI, Aceternity UI, Motion Primitives):
     - Blur-in page titles, word by word ........ "Blur In" / "Text Effect"
     - Cursor spotlight on cards ................. "Magic Card" / "Spotlight Card"
     - Gliding hover pill in nav and tabs ........ "Animated Tabs"
     - Light sweep across solid buttons .......... "Shimmer Button"
     - Click ripple on buttons and actions ....... "Ripple Button"
     - Travelling light on the progress card ..... "Border Beam"
     - Gentle 3D tilt on landing features ........ "Parallax Tilt"
     - Pop on header badges when counts change ... "Animated Badge"
     - Reading progress bar on long pages ........ "Scroll Progress"

   Everything respects reduced motion: the system setting and the
   "Reduce animations" preference (body.reduce-motion). */
   (function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') { fn(); }
        else { document.addEventListener('DOMContentLoaded', fn); }
    }

    var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;

    /* Checked at use time, because the body class is only known once the DOM exists */
    function reduceMotion() {
        return (mq && mq.matches) ||
            (document.body && document.body.classList.contains('reduce-motion'));
    }

    /* Effects that draw inside an element need it to be positioned. Only
       touch elements that are static, so sticky or fixed ones keep theirs. */
    function anchor(el) {
        if (!el.classList.contains('ml-rel') && getComputedStyle(el).position === 'static') {
            el.classList.add('ml-rel');
        }
    }

    /* Hover effects only make sense with a real mouse or trackpad */
    var finePointer = window.matchMedia &&
        window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    /* ------------------------------------------------------------------ */
    /* Core                                                               */
    /* ------------------------------------------------------------------ */

    function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

    /* Animate a number from 0 to its target. Target comes from data-count,
       decimals from data-decimals. The final text is always the exact value. */
    function countUp(el) {
        if (el.dataset.counted) { return; }
        el.dataset.counted = '1';
        var target = parseFloat(el.getAttribute('data-count'));
        if (isNaN(target)) { return; }
        var decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
        var duration = parseInt(el.getAttribute('data-duration') || '1100', 10);

        if (reduceMotion()) { el.textContent = target.toFixed(decimals); return; }

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

        if (!('IntersectionObserver' in window) || reduceMotion()) {
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

    /* ------------------------------------------------------------------ */
    /* Motion layer                                                       */
    /* ------------------------------------------------------------------ */

    /* 1. Blur-in titles. Each word fades up out of a soft blur, one after
          another. Only plain text titles are split (an <em> or <strong>
          accent is fine); anything with counters or links is left alone. */
    var SPLIT_OK = { EM: 1, STRONG: 1, B: 1, I: 1, SPAN: 1, BR: 1 };

    function canSplit(el) {
        var all = el.getElementsByTagName('*');
        for (var i = 0; i < all.length; i++) {
            if (!SPLIT_OK[all[i].tagName] || all[i].hasAttribute('data-count')) { return false; }
        }
        return el.textContent.trim().length > 0;
    }

    function splitWords(el) {
        var index = 0;
        (function walk(node) {
            Array.prototype.slice.call(node.childNodes).forEach(function (child) {
                if (child.nodeType === 1) { walk(child); return; }
                if (child.nodeType !== 3 || !child.nodeValue.trim()) { return; }
                var frag = document.createDocumentFragment();
                child.nodeValue.split(/(\s+)/).forEach(function (part) {
                    if (!part) { return; }
                    if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
                    var span = document.createElement('span');
                    span.className = 'ml-word';
                    span.style.setProperty('--wi', index++);
                    span.textContent = part;
                    frag.appendChild(span);
                });
                node.replaceChild(frag, child);
            });
        }(el));
        el.classList.add('ml-words');
    }

    function initTitles() {
        document.querySelectorAll('.page-title, .hero-landing h1, .start-card__title, .error-page .page-title')
            .forEach(function (el) {
                if (el.classList.contains('ml-words') || !canSplit(el)) { return; }
                splitWords(el);
            });
    }

    /* 2. Cursor spotlight. One delegated listener moves a soft glow (and a
          brighter rim) to follow the pointer over cards. CSS draws the
          glow, JS only writes two custom properties once per frame. */
    var SPOT = '.panel, .action, .feature, .start-card, .auth-card, .signup__form, .appt';

    function initSpotlight() {
        if (!finePointer) { return; }
        var current = null, x = 0, y = 0, queued = false;

        function paint() {
            queued = false;
            if (!current) { return; }
            var r = current.getBoundingClientRect();
            current.style.setProperty('--mx', (x - r.left) + 'px');
            current.style.setProperty('--my', (y - r.top) + 'px');
        }

        document.addEventListener('pointermove', function (e) {
            if (reduceMotion()) { return; }
            var target = e.target.closest ? e.target.closest(SPOT) : null;
            if (target !== current) {
                if (current) { current.classList.remove('is-lit'); }
                current = target;
                if (current) { anchor(current); current.classList.add('ml-spot', 'is-lit'); }
            }
            x = e.clientX; y = e.clientY;
            if (current && !queued) { queued = true; requestAnimationFrame(paint); }
        }, { passive: true });

        document.addEventListener('pointerleave', function () {
            if (current) { current.classList.remove('is-lit'); current = null; }
        });
    }

    /* 3. Gliding hover pill. A single highlight slides between the links
          of a nav or tab group instead of each link lighting up alone. */
    function initGlide() {
        if (!finePointer) { return; }
        document.querySelectorAll('.nav-links, .seg').forEach(function (group) {
            var links = group.querySelectorAll(':scope > a');
            if (links.length < 2) { return; }
            var glide = document.createElement('span');
            glide.className = 'ml-glide';
            glide.setAttribute('aria-hidden', 'true');
            anchor(group);
            group.appendChild(glide);
            group.classList.add('has-glide');

            function moveTo(link) {
                if (reduceMotion()) { return; }
                glide.style.width = link.offsetWidth + 'px';
                glide.style.height = link.offsetHeight + 'px';
                glide.style.transform = 'translate(' + link.offsetLeft + 'px,' + link.offsetTop + 'px)';
                if (!glide.classList.contains('is-on')) {
                    /* First entry: appear in place, no slide in from the corner */
                    glide.style.transition = 'none';
                    void glide.offsetWidth;
                    glide.style.transition = '';
                    glide.classList.add('is-on');
                }
                glide.classList.toggle('is-over-active', link.classList.contains('is-active'));
            }

            links.forEach(function (link) {
                link.addEventListener('pointerenter', function () { moveTo(link); });
                link.addEventListener('focus', function () { moveTo(link); });
            });
            group.addEventListener('pointerleave', function () { glide.classList.remove('is-on'); });
            group.addEventListener('focusout', function (e) {
                if (!group.contains(e.relatedTarget)) { glide.classList.remove('is-on'); }
            });
        });
    }

    /* 4. Click ripple. A ring spreads from the exact point that was pressed. */
    var RIPPLE = '.button, .btn-sage, .action, .tabbar a';

    function initRipple() {
        document.addEventListener('pointerdown', function (e) {
            if (e.button !== 0 || reduceMotion()) { return; }
            var host = e.target.closest ? e.target.closest(RIPPLE) : null;
            if (!host || host.disabled) { return; }
            var r = host.getBoundingClientRect();
            var size = Math.max(r.width, r.height) * 2.2;
            var dot = document.createElement('span');
            dot.className = 'ml-ripple';
            dot.setAttribute('aria-hidden', 'true');
            dot.style.width = dot.style.height = size + 'px';
            dot.style.left = (e.clientX - r.left - size / 2) + 'px';
            dot.style.top = (e.clientY - r.top - size / 2) + 'px';
            anchor(host);
            host.classList.add('ml-ripple-host');
            host.appendChild(dot);
            dot.addEventListener('animationend', function () { dot.remove(); });
            setTimeout(function () { if (dot.parentNode) { dot.remove(); } }, 900);
        }, { passive: true });
    }

    /* 4b. Shimmer. Solid buttons get a band of light that sweeps across on
           hover (and on a slow loop for the landing page's main button). */
    function initShimmer() {
        document.querySelectorAll('.button, .btn-sage').forEach(function (btn) {
            anchor(btn);
            btn.classList.add('ml-btn');
        });
    }

    /* 5. Border beam. A short arc of light travels around the edge of the
          dashboard's progress card (and the Start tracking card). */
    function initBeam() {
        document.querySelectorAll('.hero, .start-card').forEach(function (card) {
            if (card.querySelector(':scope > .ml-beam')) { return; }
            anchor(card);
            var beam = document.createElement('span');
            beam.className = 'ml-beam';
            beam.setAttribute('aria-hidden', 'true');
            card.appendChild(beam);
        });
    }

    /* 6. Parallax tilt on the landing page feature cards. */
    function initTilt() {
        if (!finePointer) { return; }
        document.querySelectorAll('.features .feature').forEach(function (card) {
            var queued = false, px = 0, py = 0;
            function paint() {
                queued = false;
                card.style.setProperty('--rx', (py * -5).toFixed(2) + 'deg');
                card.style.setProperty('--ry', (px * 6).toFixed(2) + 'deg');
            }
            card.addEventListener('pointermove', function (e) {
                if (reduceMotion()) { return; }
                var r = card.getBoundingClientRect();
                px = (e.clientX - r.left) / r.width - 0.5;
                py = (e.clientY - r.top) / r.height - 0.5;
                card.classList.add('is-tilting');
                if (!queued) { queued = true; requestAnimationFrame(paint); }
            });
            card.addEventListener('pointerleave', function () {
                card.classList.remove('is-tilting');
                card.style.removeProperty('--rx');
                card.style.removeProperty('--ry');
            });
        });
    }

    /* 7. Badge pop. comm.js refreshes the header counts on its own; when a
          count appears or goes up, the badge gives a small bounce. */
    function initBadges() {
        if (!('MutationObserver' in window)) { return; }
        document.querySelectorAll('[data-badge]').forEach(function (badge) {
            var last = badge.hidden ? 0 : parseInt(badge.textContent, 10) || 0;
            new MutationObserver(function () {
                var now = badge.hidden ? 0 : parseInt(badge.textContent, 10) || 0;
                if (now > last && !reduceMotion()) {
                    badge.classList.remove('ml-pop');
                    void badge.offsetWidth;
                    badge.classList.add('ml-pop');
                    var btn = badge.closest('.tool-btn');
                    if (btn) {
                        btn.classList.remove('ml-ring');
                        void btn.offsetWidth;
                        btn.classList.add('ml-ring');
                    }
                }
                last = now;
            }).observe(badge, { attributes: true, attributeFilter: ['hidden'], childList: true, characterData: true, subtree: true });
            badge.addEventListener('animationend', function () { badge.classList.remove('ml-pop'); });
        });
    }

    /* 8. Reading progress. A thin sage line under the header on long pages
          such as the Privacy Notice, Records or a patient chart. */
    function initProgress() {
        var bar = document.createElement('div');
        bar.className = 'ml-progress';
        bar.setAttribute('aria-hidden', 'true');
        document.body.appendChild(bar);
        var queued = false;

        function paint() {
            queued = false;
            var doc = document.documentElement;
            var room = doc.scrollHeight - window.innerHeight;
            var long = room > window.innerHeight * 0.6;
            bar.classList.toggle('is-on', long && window.scrollY > 4);
            bar.style.transform = 'scaleX(' + (long ? Math.min(window.scrollY / room, 1) : 0).toFixed(4) + ')';
        }
        function queue() { if (!queued) { queued = true; requestAnimationFrame(paint); } }
        window.addEventListener('scroll', queue, { passive: true });
        window.addEventListener('resize', queue, { passive: true });
        paint();
    }

    ready(function () {
        initTitles();
        initReveal();
        initHeader();
        initToasts();
        initPasswordToggles();
        initSpotlight();
        initGlide();
        initRipple();
        initShimmer();
        initBeam();
        initTilt();
        initBadges();
        initProgress();
    });
}());
/* MaterniLink communication UI:
   - Messages and Notifications dropdowns in the header (loaded when opened)
   - Facebook-style chat boxes docked at the bottom of the screen
   - Header badge counts that refresh on their own

   Everything that comes from the server is inserted with textContent,
   never as HTML, so a message can't inject markup into the page. */
(function () {
    'use strict';

    var dock = document.getElementById('chatDock');
    if (!dock) { return; }

    var CSRF = dock.dataset.csrf;
    var THREAD_URL = dock.dataset.threadUrl;      // ends in /0/
    var POLL_URL = dock.dataset.pollUrl;          // ends in /0/poll/
    var BADGES_URL = dock.dataset.badgesUrl;
    var STORE_KEY = 'ml-chat-dock-' + dock.dataset.user;
    var DOCK_ON = !dock.dataset.disabled;

    var POLL_MS = 6000;
    var BADGE_MS = 30000;

    /* ---------- small helpers ---------- */
    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) { n.className = cls; }
        if (text !== undefined && text !== null) { n.textContent = text; }
        return n;
    }

    function icon(name) {
        var ns = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('class', 'icon');
        svg.setAttribute('aria-hidden', 'true');
        var use = document.createElementNS(ns, 'use');
        use.setAttribute('href', '#' + name);
        svg.appendChild(use);
        return svg;
    }

    function urlFor(template, id) {
        return template.replace('/0/', '/' + id + '/');
    }

    function getJSON(url) {
        return fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
            .then(function (r) {
                if (!r.ok) { var e = new Error('HTTP ' + r.status); e.status = r.status; throw e; }
                return r.json();
            });
    }

    function postForm(url, data) {
        return fetch(url, {
            method: 'POST', body: data, credentials: 'same-origin',
            headers: { 'X-CSRFToken': CSRF, 'X-Requested-With': 'fetch' }
        }).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (body) {
                if (!r.ok) { var e = new Error(body.error || 'HTTP ' + r.status); e.status = r.status; throw e; }
                return body;
            });
        });
    }

    function isDesktop() { return window.innerWidth >= 768; }

    /* ---------- header badges ---------- */
    function setBadge(kind, count) {
        var b = document.querySelector('[data-badge="' + kind + '"]');
        if (!b) { return; }
        b.textContent = count > 99 ? '99+' : String(count);
        b.hidden = !count;
        var btn = b.closest('button');
        if (btn) {
            var label = kind === 'messages' ? 'Messages' : 'Notifications';
            btn.setAttribute('aria-label', count ? label + ', ' + count + ' unread' : label);
        }
    }

    function refreshBadges() {
        if (document.hidden) { return; }
        getJSON(BADGES_URL).then(function (d) {
            setBadge('messages', d.messages);
            setBadge('notifications', d.notifications);
        }).catch(function () {});
    }

    /* ---------- dropdown lists ---------- */
    function emptyRow(text) { return el('div', 'comm-menu__empty', text); }

    function renderMessages(list, rows) {
        list.textContent = '';
        if (!rows.length) {
            list.appendChild(emptyRow('No conversations yet.'));
            return;
        }
        rows.forEach(function (c) {
            var a = el('a', 'comm-item' + (c.unread ? ' is-unread' : ''));
            a.href = c.url;
            a.dataset.chatOpen = c.user_id;
            a.appendChild(el('span', 'avatar avatar--sm', c.initial));
            var body = el('span', 'comm-item__body');
            body.appendChild(el('strong', null, c.name));
            body.appendChild(el('span', null, c.preview));
            a.appendChild(body);
            var meta = el('span', 'comm-item__meta');
            meta.appendChild(el('time', null, c.time));
            if (c.unread) { meta.appendChild(el('span', 'comm-item__dot')); }
            a.appendChild(meta);
            list.appendChild(a);
        });
    }

    function renderNotifications(list, rows) {
        list.textContent = '';
        if (!rows.length) {
            list.appendChild(emptyRow('No notifications yet.'));
            return;
        }
        rows.forEach(function (n) {
            var a = el('a', 'comm-item comm-item--notif' + (n.unread ? ' is-unread' : ''));
            a.href = n.url;
            var ic = el('span', 'comm-item__icon');
            ic.appendChild(icon('i-bell'));
            a.appendChild(ic);
            var body = el('span', 'comm-item__body');
            body.appendChild(el('strong', null, n.title));
            body.appendChild(el('span', null, n.content));
            a.appendChild(body);
            var meta = el('span', 'comm-item__meta');
            meta.appendChild(el('time', null, n.time));
            if (n.unread) { meta.appendChild(el('span', 'comm-item__dot')); }
            a.appendChild(meta);
            list.appendChild(a);
        });
    }

    function loadList(list) {
        getJSON(list.dataset.src).then(function (d) {
            if (list.dataset.list === 'messages') { renderMessages(list, d.conversations); }
            else { renderNotifications(list, d.notifications); }
        }).catch(function () {
            list.textContent = '';
            list.appendChild(emptyRow("Couldn't load. Try again."));
        });
    }

    document.querySelectorAll('.comm-menu').forEach(function (menu) {
        var toggle = menu.parentElement.querySelector('[data-bs-toggle="dropdown"]');
        var list = menu.querySelector('[data-list]');
        if (toggle && list) {
            toggle.addEventListener('show.bs.dropdown', function () { loadList(list); });
        }
    });

    var readAll = document.querySelector('[data-read-all]');
    if (readAll) {
        readAll.addEventListener('click', function () {
            postForm(readAll.dataset.readAll, new FormData()).then(function () {
                setBadge('notifications', 0);
                document.querySelectorAll('[data-list="notifications"] .is-unread').forEach(function (a) {
                    a.classList.remove('is-unread');
                    var dot = a.querySelector('.comm-item__dot');
                    if (dot) { dot.remove(); }
                });
            }).catch(function () {});
        });
    }

    /* Clicking a conversation opens a chat box on desktop.
       On phones, or on the Messages page itself, the link just navigates. */
    document.addEventListener('click', function (e) {
        var a = e.target.closest('[data-chat-open]');
        if (!a || !DOCK_ON || !isDesktop()) { return; }
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) { return; }  // let "open in new tab" work
        e.preventDefault();
        openChat(parseInt(a.dataset.chatOpen, 10), false);
        var dd = a.closest('.dropdown');
        var toggle = dd && dd.querySelector('[data-bs-toggle="dropdown"]');
        if (toggle && window.bootstrap) { window.bootstrap.Dropdown.getOrCreateInstance(toggle).hide(); }
    });

    /* ---------- docked chat boxes ---------- */
    var boxes = {};   // user_id -> state
    var order = [];   // user ids, oldest first

    function maxBoxes() { return window.innerWidth >= 1300 ? 3 : 2; }

    function save() {
        try {
            var list = order.map(function (id) {
                return { id: id, min: boxes[id].minimized };
            });
            localStorage.setItem(STORE_KEY, JSON.stringify(list));
        } catch (err) { /* storage can be unavailable; the boxes still work */ }
    }

    function load() {
        try {
            var raw = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
            return Array.isArray(raw) ? raw.filter(function (b) { return b && Number.isInteger(b.id) && b.id > 0; }) : [];
        } catch (err) { return []; }
    }

    function addBubble(state, m) {
        if (state.seen[m.id]) { return; }
        state.seen[m.id] = true;
        if (state.emptyNote) { state.emptyNote.remove(); state.emptyNote = null; }
        var b = el('div', 'bubble' + (m.mine ? ' bubble--mine' : ''));
        b.appendChild(el('p', null, m.body));
        b.appendChild(el('span', 'bubble__time', m.time));
        state.scroll.appendChild(b);
        state.last = Math.max(state.last, m.id);
    }

    function scrollDown(state) { state.scroll.scrollTop = state.scroll.scrollHeight; }

    function setUnread(state, n) {
        state.unread = n;
        state.badge.textContent = String(n);
        state.badge.hidden = !(n && state.minimized);
    }

    function setMinimized(state, min) {
        state.minimized = min;
        state.box.classList.toggle('is-min', min);
        state.minBtn.setAttribute('aria-label', min ? 'Expand chat' : 'Minimize chat');
        state.minBtn.replaceChildren(icon(min ? 'i-chevron-up' : 'i-minus'));
        state.title.setAttribute('aria-expanded', String(!min));
        if (!min) {
            setUnread(state, 0);
            poll(state, true);          // marks the conversation read
            setTimeout(function () { scrollDown(state); state.input.focus(); }, 30);
        } else {
            state.badge.hidden = !state.unread;
        }
        save();
    }

    function closeChat(id) {
        var state = boxes[id];
        if (!state) { return; }
        state.box.remove();
        delete boxes[id];
        order = order.filter(function (x) { return x !== id; });
        save();
    }

    function build(id) {
        var box = el('section', 'chatbox');
        box.setAttribute('role', 'dialog');
        box.setAttribute('aria-label', 'Chat');

        var head = el('div', 'chatbox__head');
        var title = el('button', 'chatbox__title');
        title.type = 'button';
        var avatar = el('span', 'avatar avatar--sm', '·');
        var name = el('span', 'chatbox__name', 'Loading…');
        var badge = el('span', 'count-badge chatbox__badge', '0');
        badge.hidden = true;
        title.appendChild(avatar);
        title.appendChild(name);
        title.appendChild(badge);
        head.appendChild(title);

        var full = el('a', 'chatbox__btn');
        full.href = urlFor(THREAD_URL, id);
        full.title = 'Open full conversation';
        full.setAttribute('aria-label', 'Open full conversation');
        full.appendChild(icon('i-expand'));
        var minBtn = el('button', 'chatbox__btn');
        minBtn.type = 'button';
        var closeBtn = el('button', 'chatbox__btn');
        closeBtn.type = 'button';
        closeBtn.setAttribute('aria-label', 'Close chat');
        closeBtn.appendChild(icon('i-x'));
        head.appendChild(full);
        head.appendChild(minBtn);
        head.appendChild(closeBtn);

        var body = el('div', 'chatbox__body');
        var scroll = el('div', 'chatbox__scroll');
        scroll.setAttribute('aria-live', 'polite');
        var emptyNote = el('div', 'chat-empty', 'No messages yet. Say hello.');
        scroll.appendChild(emptyNote);

        var form = el('form', 'chatbox__form');
        var input = el('textarea', 'form-control');
        input.rows = 1;
        input.maxLength = 2000;
        input.placeholder = 'Aa';
        input.setAttribute('aria-label', 'Message');
        var send = el('button', 'chatbox__send');
        send.type = 'submit';
        send.setAttribute('aria-label', 'Send');
        send.appendChild(icon('i-send'));
        form.appendChild(input);
        form.appendChild(send);
        body.appendChild(scroll);
        body.appendChild(form);

        box.appendChild(head);
        box.appendChild(body);

        var state = {
            id: id, box: box, title: title, avatar: avatar, name: name, badge: badge,
            minBtn: minBtn, scroll: scroll, input: input, emptyNote: emptyNote,
            last: 0, seen: {}, unread: 0, minimized: false, busy: false
        };

        title.addEventListener('click', function () { setMinimized(state, !state.minimized); });
        minBtn.addEventListener('click', function () { setMinimized(state, !state.minimized); });
        closeBtn.addEventListener('click', function () { closeChat(id); });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.requestSubmit();
            }
        });

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var text = input.value.trim();
            if (!text || state.busy) { return; }
            state.busy = true;
            var data = new FormData();
            data.append('body', text);
            postForm(urlFor(THREAD_URL, id), data).then(function (d) {
                input.value = '';
                addBubble(state, d.message);
                scrollDown(state);
            }).catch(function (err) {
                var note = el('div', 'chatbox__error', err.message && err.message.indexOf('HTTP') !== 0
                    ? err.message : "Couldn't send. Try again.");
                state.scroll.appendChild(note);
                scrollDown(state);
                setTimeout(function () { note.remove(); }, 4000);
            }).then(function () { state.busy = false; input.focus(); });
        });

        return state;
    }

    function poll(state, first) {
        var url = urlFor(POLL_URL, state.id) + '?after=' + (first ? 0 : state.last) +
                  (state.minimized ? '&read=0' : '');
        return getJSON(url).then(function (d) {
            if (!boxes[state.id]) { return; }
            state.avatar.textContent = d.contact.initial;
            state.name.textContent = d.contact.name;
            state.box.setAttribute('aria-label', 'Chat with ' + d.contact.name);
            var nearBottom = state.scroll.scrollHeight - state.scroll.scrollTop - state.scroll.clientHeight < 80;
            d.messages.forEach(function (m) { addBubble(state, m); });
            if (first || (d.messages.length && nearBottom)) { scrollDown(state); }
            if (state.minimized) { setUnread(state, d.unread); }
            else { refreshBadges(); }
        }).catch(function (err) {
            // 404: no longer allowed to message this person, so drop the box.
            if (err.status === 404) { closeChat(state.id); }
        });
    }

    function openChat(id, minimized) {
        if (!id || id < 1) { return; }
        if (boxes[id]) {
            if (boxes[id].minimized) { setMinimized(boxes[id], false); }
            else { boxes[id].input.focus(); }
            return;
        }
        // Too many open: close the oldest.
        while (order.length >= maxBoxes()) { closeChat(order[0]); }

        var state = build(id);
        boxes[id] = state;
        order.push(id);
        state.minimized = !!minimized;
        state.box.classList.toggle('is-min', state.minimized);
        state.minBtn.setAttribute('aria-label', state.minimized ? 'Expand chat' : 'Minimize chat');
        state.minBtn.appendChild(icon(state.minimized ? 'i-chevron-up' : 'i-minus'));
        state.title.setAttribute('aria-expanded', String(!state.minimized));
        dock.insertBefore(state.box, dock.firstChild);   // newest sits on the right
        save();
        poll(state, true).then(function () {
            if (!state.minimized) { state.input.focus(); }
        });
    }

    if (DOCK_ON) {
        // Make room for the floating Ask button when it is on the page.
        if (document.querySelector('.fab')) { dock.classList.add('chat-dock--beside-fab'); }

        // Reopen the chats that were open on the previous page.
        if (isDesktop()) {
            load().slice(-maxBoxes()).forEach(function (b) { openChat(b.id, b.min); });
        }

        setInterval(function () {
            if (document.hidden) { return; }
            order.forEach(function (id) { poll(boxes[id], false); });
        }, POLL_MS);
    }

    setInterval(refreshBadges, BADGE_MS);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) { refreshBadges(); } });
}());
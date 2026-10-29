
(function () {
  /* Appearance on the nations pages: Theme and Motion, saved under the landing's keys so a choice carries across
     the site. The popover itself is declarative (popovertarget). The OS reduced-motion setting is a floor. */
  var d = document.documentElement;
  var NAMES = { '': 'Sovereign Skeleton', maya: 'Maya Radiance', codex: 'Living Codex', skeleton: 'Obsidian Ember', calavera: 'Calavera Nocturne' };
  var DESCRIPTIONS = { '': 'Silver structure, a foundation for your own judgment.', maya: 'Deep Maya blue with moving gold light.', codex: 'Warm paper for memory that keeps growing.', skeleton: 'Dark obsidian with a deep crimson ember.', calavera: 'Midnight violet, jade and gold. Calaveras in living light.' };
  var BG = { '': '#000000', maya: '#02101E', codex: '#E8DBC0', skeleton: '#050507', calavera: '#090716' };
  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function radios(group, onPick) {
    if (!group) return function () {};
    var opts = group.querySelectorAll('[role="radio"]');
    function mark(b) {
      for (var i = 0; i < opts.length; i++) {
        opts[i].setAttribute('aria-checked', opts[i] === b ? 'true' : 'false');
        opts[i].tabIndex = opts[i] === b ? 0 : -1;
      }
    }
    group.addEventListener('click', function (e) {
      var b = e.target.closest('[role="radio"]');
      if (b && group.contains(b) && b.getAttribute('aria-disabled') !== 'true') { mark(b); onPick(b); }
    });
    group.addEventListener('keydown', function (e) {
      var k = e.key, i = Array.prototype.indexOf.call(opts, document.activeElement);
      if (i < 0) return;
      var j = (k === 'ArrowRight' || k === 'ArrowDown') ? i + 1 : (k === 'ArrowLeft' || k === 'ArrowUp') ? i - 1 : k === 'Home' ? 0 : k === 'End' ? opts.length - 1 : -2;
      if (j === -2) return;
      e.preventDefault();
      j = (j + opts.length) % opts.length;
      opts[j].focus(); mark(opts[j]); onPick(opts[j]);
    });
    return mark;
  }
  var themeMark = radios(document.querySelector('#appearancePop .theme-picker'), function (b) { theme(b.getAttribute('data-set') || '', true); });
  function theme(t, save) {
    if (t !== 'maya' && t !== 'codex' && t !== 'skeleton' && t !== 'calavera') t = '';
    if (t) d.setAttribute('data-theme', t); else d.removeAttribute('data-theme');
    var m = document.getElementById('themeColorMeta');
    if (m) m.setAttribute('content', BG[t]);
    var n = document.getElementById('apThemeName');
    if (n) n.textContent = NAMES[t];
    var description = document.getElementById('apThemeDescription');
    if (description) description.textContent = DESCRIPTIONS[t];
    themeMark(document.querySelector('#appearancePop .theme-swatch[data-set="' + t + '"]'));
    if (save) put('zotheos_landing_theme', t);
  }
  var chosen = 'living';
  var sm = get('zotheos_motion');
  if (sm === 'living' || sm === 'calm' || sm === 'still') chosen = sm;
  else if (get('zotheos_fx') === 'off') chosen = 'still';
  var group = document.getElementById('motionGroup');
  var motionMark = radios(group, function (b) { chosen = b.getAttribute('data-mode'); put('zotheos_motion', chosen); motion(); });
  function motion() {
    var floor = !!(mq && mq.matches);
    var m = floor ? 'still' : chosen;
    d.setAttribute('data-motion', m);
    var row = document.getElementById('apMotionRow'), note = document.getElementById('apMotionNote');
    if (row) row.classList.toggle('is-idle', floor);
    if (note) note.hidden = !floor;
    if (group) {
      var opts = group.querySelectorAll('[role="radio"]');
      for (var i = 0; i < opts.length; i++) {
        if (floor && opts[i].getAttribute('data-mode') !== 'still') opts[i].setAttribute('aria-disabled', 'true');
        else opts[i].removeAttribute('aria-disabled');
      }
      motionMark(group.querySelector('[data-mode="' + m + '"]'));
    }
  }
  theme(get('zotheos_landing_theme') || '', false);
  motion();
  if (mq) { if (mq.addEventListener) mq.addEventListener('change', motion); else if (mq.addListener) mq.addListener(motion); }
})();

(function () {
  var input = document.getElementById('directoryQuery'), list = document.getElementById('directoryNames');
  if (!input || !list) return;
  var rows = list.querySelectorAll('[data-directory-name]'), groups = list.querySelectorAll('.directory-group');
  var status = document.getElementById('directoryResult'), clear = document.getElementById('directoryClear');
  var tools = document.getElementById('directoryTools'), inventory = document.getElementById('directoryInventory');
  var more = document.getElementById('directoryMore'), limitNote = document.getElementById('directoryLimit');
  var profilesOnly = document.getElementById('directoryProfilesOnly'), profileHint = document.getElementById('directoryProfileHint');
  var resultsIntro = document.getElementById('directoryResultsIntro'), resultsSummary = document.getElementById('directoryResultsSummary');
  var resultsEmpty = document.getElementById('directoryResultsEmpty'), resultsActions = document.getElementById('directoryResultsActions');
  var readFirst = document.getElementById('directoryReadFirst'), resultsReadFirst = document.getElementById('directoryResultsReadFirst');
  var share = document.getElementById('directoryShareLink');
  if (!status || !clear) return;
  var batch = 40, limit = batch, names = [], scopes = [], visible = [], i, QMAX = 200, announceTurn = 0;
  // The generated static href supplies the page path, so a request URL can never redirect the link elsewhere.
  var sharePath = share ? (share.getAttribute('href') || '').split(/[?#]/)[0] : '';
  if (!/^\/[A-Za-z0-9\/-]*$/.test(sharePath) || sharePath.charAt(1) === '/') share = null;
  var enhanced = !!(tools && inventory && more && limitNote);
  function fold(s) { return (s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s).toLowerCase(); }
  for (i = 0; i < rows.length; i++) {
    names.push(fold(rows[i].getAttribute('data-directory-name')));
    var owner = rows[i].closest('[data-directory-inventory]');
    scopes.push(owner ? owner.getAttribute('data-directory-inventory') : '');
    if (!owner) enhanced = false;
  }
  if (enhanced) {
    for (i = 0; i < inventory.options.length; i++) {
      var value = inventory.options[i].value, section = document.getElementById(value);
      if (value !== 'all' && (!section || !list.contains(section) || section.getAttribute('data-directory-inventory') !== value)) enhanced = false;
    }
  }
  function directoryMatches(name, words) {
    for (var j = 0; j < words.length; j++) {
      var word = words[j], at = -1;
      do { at = name.indexOf(word, at + 1); if (at < 0) return false; }
      while (/^[a-z0-9]/.test(word) && at > 0 && /[a-z0-9]/.test(name.charAt(at - 1)));
    }
    return true;
  }
  function shareHref(selected, readyOnly) {
    var parts = [], q = input.value.trim().slice(0, QMAX), encoded;
    if (q) {
      try { encoded = encodeURIComponent(q); } catch (e) { encoded = encodeURIComponent(q.replace(/[\uD800-\uDFFF]/g, '\uFFFD')); }
      parts.push('q=' + encoded);
    }
    if (selected !== 'all') parts.push('inventory=' + encodeURIComponent(selected));
    if (readyOnly) parts.push('ready=1');
    return sharePath + (parts.length ? '?' + parts.join('&') : '') + '#directoryNames';
  }
  // Only q, inventory and ready are read. The first copy of each wins; other parameters are ignored.
  function sharedSearch() {
    var raw = window.location.search, found = {}, used = false, invalid = false;
    if (typeof raw !== 'string' || raw.length < 2) return null;
    if (raw.length > 2048) return {invalid: true};
    var pairs = raw.slice(1).split('&');
    for (var j = 0; j < pairs.length; j++) {
      var at = pairs[j].indexOf('='), key = at < 0 ? pairs[j] : pairs[j].slice(0, at);
      if ((key !== 'q' && key !== 'inventory' && key !== 'ready') || Object.prototype.hasOwnProperty.call(found, key)) continue;
      used = true;
      try { found[key] = decodeURIComponent((at < 0 ? '' : pairs[j].slice(at + 1)).replace(/\+/g, ' ')); }
      catch (e) { found[key] = null; invalid = true; }
    }
    if (!used) return null;
    var out = {invalid: invalid};
    if (typeof found.q === 'string') { if (found.q.length <= QMAX) out.q = found.q; else invalid = true; }
    if (typeof found.inventory === 'string') {
      for (j = 0; j < inventory.options.length; j++) if (inventory.options[j].value === found.inventory) out.inventory = found.inventory;
      if (!out.inventory) invalid = true;
    }
    if (typeof found.ready === 'string') { if (found.ready === '1' && profilesOnly) out.ready = true; else invalid = true; }
    out.invalid = invalid;
    return out;
  }
  function filter() {
    var words = fold(input.value).trim().split(/\s+/), count = 0, shown = 0;
    var selected = enhanced ? inventory.value : 'all';
    var readyOnly = !!(enhanced && profilesOnly && profilesOnly.checked);
    if (profileHint) profileHint.hidden = !readyOnly;
    announceTurn++;
    if (enhanced && share) share.setAttribute('href', shareHref(selected, readyOnly));
    visible = [];
    for (var j = 0; j < rows.length; j++) {
      var match = (selected === 'all' || scopes[j] === selected) && directoryMatches(names[j], words)
        && (!readyOnly || rows[j].getAttribute('data-directory-profile') === 'ready');
      if (match) count++;
      var show = match && (!enhanced || shown < limit);
      rows[j].hidden = !show;
      if (show) { shown++; visible.push(rows[j]); }
    }
    for (i = 0; i < groups.length; i++) groups[i].hidden = !groups[i].querySelector('[data-directory-name]:not([hidden])');
    if (enhanced) {
      var label = selected === 'all' ? 'all source inventories' : inventory.options[inventory.selectedIndex].textContent;
      status.textContent = shown + ' of ' + count + ' matching name records' + (readyOnly ? ' with reviewed profile links' : '') + ' shown in ' + label + '.' + (count ? '' : ' Try another spelling or search the researched profiles.');
      if (resultsIntro) resultsIntro.hidden = false;
      if (resultsSummary) resultsSummary.textContent = status.textContent;
      if (resultsEmpty) resultsEmpty.hidden = count !== 0;
      if (resultsActions) resultsActions.hidden = count === 0;
      if (readFirst) readFirst.hidden = visible.length === 0;
      if (resultsReadFirst) resultsReadFirst.hidden = visible.length === 0;
      var next = Math.min(batch, count - shown);
      more.hidden = next <= 0;
      more.textContent = 'Show ' + next + ' More';
      more.setAttribute('aria-label', 'Show the next ' + next + ' matching name records');
      limitNote.textContent = (next > 0 ? 'Show More reveals the next ' + next + ' matching records. ' : '') + 'Each source keeps its own category and date. These counts are not a total of Indigenous Nations.';
    } else {
      status.textContent = count + ' of ' + rows.length + ' name records shown.' + (count ? '' : ' Try another spelling or search the researched profiles.');
    }
  }
  input.addEventListener('input', function () { limit = batch; filter(); });
  clear.addEventListener('click', function () { input.value = ''; limit = batch; filter(); input.focus(); });
  if (!enhanced) return;
  // The URL owns the filters, so the browser must not restore stale control values after Back/Forward.
  inventory.setAttribute('autocomplete', 'off');
  if (profilesOnly) profilesOnly.setAttribute('autocomplete', 'off');
  function readFirstMatch() {
    if (!visible.length) return;
    var name = visible[0].querySelector('.directory-name') || visible[0];
    name.setAttribute('tabindex', '-1'); name.focus(); name.scrollIntoView();
  }
  if (readFirst) readFirst.addEventListener('click', readFirstMatch);
  if (resultsReadFirst) resultsReadFirst.addEventListener('click', readFirstMatch);
  inventory.addEventListener('change', function () { limit = batch; filter(); });
  if (profilesOnly) profilesOnly.addEventListener('change', function () { limit = batch; filter(); });
  more.addEventListener('click', function () {
    var previous = visible.length;
    limit += batch; filter();
    // Focus the first newly revealed name so keyboard and screen-reader users can continue reading there.
    if (visible.length > previous) {
      var name = visible[previous].querySelector('.directory-name') || visible[previous];
      name.setAttribute('tabindex', '-1'); name.focus();
    }
  });
  function hashTarget() {
    var id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (e) { return null; }
    var target = document.getElementById(id);
    return target && list.contains(target) ? target : null;
  }
  function reveal(target, initial, focusInventory) {
    var owner = target.closest('[data-directory-inventory]');
    if (!owner) return;
    inventory.value = owner.getAttribute('data-directory-inventory');
    if (profilesOnly) profilesOnly.checked = false;
    input.value = ''; limit = batch;
    var row = target.closest('[data-directory-name]'), ordinal = 0;
    if (row) {
      for (var j = 0; j < rows.length; j++) {
        if (scopes[j] !== inventory.value) continue;
        ordinal++;
        if (rows[j] === row) { limit = Math.ceil(ordinal / batch) * batch; break; }
      }
    }
    filter();
    if (focusInventory) inventory.focus();
    else if (initial) window.requestAnimationFrame(function () { target.scrollIntoView(); });
    else target.scrollIntoView();
  }
  function decodable(hash) { try { decodeURIComponent(hash || ''); return true; } catch (e) { return false; } }
  function legacyTarget(target) { return !!(target && target !== list && target.closest('[data-directory-inventory]')); }
  // The URL defines the search on load and on Back/Forward: q, inventory and ready, with omitted values meaning the
  // defaults. A record or inventory fragment keeps its older deep-link meaning and takes precedence over them.
  function applyUrl(initial) {
    var target = hashTarget();
    if (legacyTarget(target)) { reveal(target, initial, false); return; }
    var shared = sharedSearch() || {};
    input.value = typeof shared.q === 'string' ? shared.q : '';
    inventory.value = shared.inventory || 'all';
    if (profilesOnly) profilesOnly.checked = !!shared.ready;
    limit = batch; filter();
    var restored = initial && (typeof shared.q === 'string' || shared.inventory || shared.ready || shared.invalid);
    if (!restored && !shared.invalid) return;
    var turn = announceTurn, message = (restored ? 'Search restored from this link. ' : '') + (shared.invalid ? 'Some link settings were not recognized and were left out. ' : '') + status.textContent;
    // Change the live region after it becomes visible so assistive technology announces the restored result.
    var later = initial && window.setTimeout ? function (fn) { window.setTimeout(fn, 300); } : function (fn) { fn(); };
    later(function () {
      if (turn !== announceTurn) return;
      status.textContent = message;
      if (resultsSummary) resultsSummary.textContent = message;
    });
    if (initial && target === list) window.requestAnimationFrame(function () { list.scrollIntoView(); });
  }
  // In-page fragment links (Browse Matching Names, Adjust Filters, skip links) keep the current filters. A fragment
  // change without a matching recent link activation is history traversal or an address edit, so the URL applies.
  var navHash = '', linkHash = '', linkAt = 0;
  if (document.addEventListener) document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null, href = a ? a.getAttribute('href') : '';
    var target = a ? a.getAttribute('target') : '';
    if (!a || a.getAttribute('download') !== null || (target && target.toLowerCase() !== '_self')) return;
    if (href && href.charAt(0) === '#' && href !== window.location.hash) { linkHash = href; linkAt = Date.now(); }
  }, true);
  window.addEventListener('hashchange', function () {
    var target = hashTarget(), focusInventory = target && navHash === target.id;
    var inPage = linkHash !== '' && linkHash === window.location.hash && Date.now() - linkAt < 3000;
    navHash = ''; linkHash = '';
    if (legacyTarget(target)) reveal(target, false, focusInventory);
    else if (!inPage && decodable(window.location.hash)) applyUrl(false);
  });
  window.addEventListener('pageshow', function (e) { if (e && e.persisted) applyUrl(false); });
  var jumps = document.querySelectorAll('.directory-inventory-nav a');
  for (i = 0; i < jumps.length; i++) jumps[i].addEventListener('click', function (e) {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var href = this.getAttribute('href');
    if (!href || href.charAt(0) !== '#') return;
    var target;
    try { target = document.getElementById(decodeURIComponent(href.slice(1))); } catch (err) { return; }
    if (!target || !list.contains(target)) return;
    e.preventDefault(); navHash = target.id;
    if (window.location.hash === href) { navHash = ''; reveal(target, false, true); }
    else window.location.hash = href;
  });
  filter(); tools.hidden = false;
  applyUrl(true);
})();

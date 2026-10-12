
(function () {
  /* Appearance on the nations pages: Theme and Motion, saved under the landing's keys so a choice carries across
     the site. The popover itself is declarative (popovertarget). The OS reduced-motion setting is a floor. */
  var d = document.documentElement;
  var NAMES = { '': 'Sovereign Skeleton', maya: 'Maya Radiance', codex: 'Living Codex', skeleton: 'Obsidian Ember' };
  var DESCRIPTIONS = { '': 'Silver structure, a foundation for your own judgment.', maya: 'Deep Maya blue with moving gold light.', codex: 'Warm paper for memory that keeps growing.', skeleton: 'Dark obsidian with a deep crimson ember.' };
  var BG = { '': '#000000', maya: '#02101E', codex: '#E8DBC0', skeleton: '#050507' };
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
    if (t !== 'maya' && t !== 'codex' && t !== 'skeleton') t = '';
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
  function fold(s) { return (s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s).toLowerCase(); }
  var names = [], i;
  for (i = 0; i < rows.length; i++) names.push(fold(rows[i].getAttribute('data-directory-name')));
  function directoryMatches(name, words) {
    for (var j = 0; j < words.length; j++) {
      var word = words[j], at = -1;
      do { at = name.indexOf(word, at + 1); if (at < 0) return false; }
      while (/^[a-z0-9]/.test(word) && at > 0 && /[a-z0-9]/.test(name.charAt(at - 1)));
    }
    return true;
  }
  function filter() {
    var words = fold(input.value).trim().split(/\s+/), count = 0;
    for (var i = 0; i < rows.length; i++) {
      var match = directoryMatches(names[i], words);
      rows[i].hidden = !match;
      if (match) count++;
    }
    for (i = 0; i < groups.length; i++) groups[i].hidden = !groups[i].querySelector('[data-directory-name]:not([hidden])');
    status.textContent = count + ' of ' + rows.length + ' name records shown.' + (count ? '' : ' Try another spelling or search the researched profiles.');
  }
  input.addEventListener('input', filter);
  clear.addEventListener('click', function () { input.value = ''; filter(); input.focus(); });
})();

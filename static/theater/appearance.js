(function () {
  'use strict';
  var root = document.documentElement;
  var pop = document.getElementById('appearancePop');
  var triggers = Array.from(document.querySelectorAll('[popovertarget="appearancePop"]'));
  if (!pop || !triggers.length) return;
  var native = typeof pop.showPopover === 'function';
  var opener = triggers[0];
  var menu = document.getElementById('navMenuBtn');
  var hadFocus = false;
  function isOpen() { return native ? pop.matches(':popover-open') : pop.classList.contains('is-open'); }
  function visible(node) { return node && node.getBoundingClientRect().width > 0 && node.getBoundingClientRect().height > 0; }
  function anchor() { return visible(opener) ? opener : visible(triggers[0]) ? triggers[0] : menu; }
  function expanded(open) {
    triggers.forEach(function (button) { button.setAttribute('aria-expanded', String(open)); });
  }
  function focus(node) {
    if (!node) return;
    try { node.focus({preventScroll: true}); } catch (_) { node.focus(); }
  }
  function close(restore) {
    if (!isOpen()) return;
    if (native) pop.hidePopover();
    else { pop.classList.remove('is-open'); expanded(false); }
    if (restore) focus(anchor());
  }
  function place() {
    if (!isOpen()) return;
    var button = anchor();
    if (!button) return;
    var viewport = window.visualViewport;
    var x = viewport ? viewport.offsetLeft : 0, y = viewport ? viewport.offsetTop : 0;
    var width = viewport ? viewport.width : root.clientWidth;
    var height = viewport ? viewport.height : window.innerHeight;
    pop.style.maxWidth = Math.max(1, width - 32) + 'px';
    pop.style.maxHeight = Math.max(1, height - 32) + 'px';
    var rect = button.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    var left = Math.max(x + 16, Math.min(rect.left, x + width - w - 16));
    var top = rect.bottom + 8 + h <= y + height - 16 ? rect.bottom + 8 : rect.top - h - 8;
    top = Math.max(y + 16, Math.min(top, y + height - h - 16));
    pop.style.left = Math.round(left) + 'px';
    pop.style.top = Math.round(top) + 'px';
  }
  triggers.forEach(function (button) {
    button.setAttribute('aria-controls', pop.id);
    button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', function () {
      opener = button;
      if (native) {
        var parentSheet = document.getElementById('navSheet');
        // Native popovers keep a trigger's ancestor sheet open unless we close it explicitly.
        if (parentSheet && parentSheet.contains(button) && typeof parentSheet.hidePopover === 'function') {
          try { parentSheet.hidePopover(); } catch (_) {}
        }
        if (isOpen()) place();
        return;
      }
      if (isOpen()) close(false);
      else {
        var sheet = document.getElementById('navSheet');
        if (sheet && typeof sheet.hidePopover === 'function') {
          try { sheet.hidePopover(); } catch (_) {}
        }
        pop.classList.add('is-open'); expanded(true); place();
        focus(pop.querySelector('[role="radio"][tabindex="0"]'));
      }
    });
  });
  if (native) {
    pop.addEventListener('beforetoggle', function (event) {
      if (event.newState === 'closed') hadFocus = pop.contains(document.activeElement);
    });
    pop.addEventListener('toggle', function (event) {
      expanded(event.newState === 'open');
      if (event.newState === 'open') { place(); return; }
      if (hadFocus) {
        hadFocus = false;
        var active = document.activeElement;
        if (!active || active === document.body || pop.contains(active)) focus(anchor());
      }
    });
  } else {
    pop.classList.add('is-fallback');
  }
  function outside(event) {
    if (!pop.contains(event.target) && !triggers.some(function (button) { return button.contains(event.target); })) close(false);
  }
  // Use the same outside dismissal for native popovers and the fallback.
  document.addEventListener('pointerdown', outside);
  document.addEventListener('click', outside);
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && isOpen()) { event.preventDefault(); close(true); }
  });
  function tabAway(event) {
    if (event.relatedTarget && !pop.contains(event.relatedTarget) && triggers.indexOf(event.relatedTarget) < 0) close(false);
  }
  pop.addEventListener('focusout', tabAway);
  triggers.forEach(function (button) { button.addEventListener('focusout', tabAway); });
  window.addEventListener('resize', place);
  window.addEventListener('scroll', place, {passive: true});
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', place);
    window.visualViewport.addEventListener('scroll', place);
  }
  if (window.ResizeObserver) new ResizeObserver(place).observe(pop);

  // This preference is shared with the landing page. Here it changes only the decorative frame.
  var group = document.getElementById('fxAmount');
  var row = document.getElementById('fxAmountRow');
  var note = document.getElementById('apFxNote');
  var levels = ['light', 'medium', 'heavy'], level = 'medium';
  try { var saved = localStorage.getItem('zotheos_rain'); if (levels.indexOf(saved) >= 0) level = saved; } catch (_) {}
  var options = group ? Array.from(group.querySelectorAll('[role="radio"]')) : [];
  function intensity() {
    root.setAttribute('data-theater-intensity', level);
    var idle = root.getAttribute('data-motion') !== 'living' || root.getAttribute('data-theater-motion') === 'still';
    options.forEach(function (button) {
      var picked = Number(button.getAttribute('data-level')) === levels.indexOf(level);
      button.setAttribute('aria-checked', String(picked));
      button.tabIndex = picked ? 0 : -1;
      if (idle) button.setAttribute('aria-disabled', 'true'); else button.removeAttribute('aria-disabled');
    });
    if (row) row.classList.toggle('is-idle', idle);
    if (note) note.hidden = !idle;
    if (group) {
      if (idle) group.setAttribute('aria-describedby', 'apFxNote'); else group.removeAttribute('aria-describedby');
    }
    place();
  }
  function pick(button) {
    if (!button || button.getAttribute('aria-disabled') === 'true') return;
    var value = Number(button.getAttribute('data-level'));
    if (!Number.isInteger(value) || value < 0 || value > 2) return;
    level = levels[value];
    try { localStorage.setItem('zotheos_rain', level); } catch (_) {}
    intensity();
  }
  if (group) {
    group.addEventListener('click', function (event) {
      var button = event.target.closest('[role="radio"]');
      if (button && group.contains(button)) pick(button);
    });
    group.addEventListener('keydown', function (event) {
      var index = options.indexOf(document.activeElement), next;
      if (index < 0 || options[index].getAttribute('aria-disabled') === 'true') return;
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % options.length;
      else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index + options.length - 1) % options.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = options.length - 1;
      else return;
      event.preventDefault(); pick(options[next]); focus(options[next]);
    });
  }
  new MutationObserver(intensity).observe(root, {attributes: true, attributeFilter: ['data-motion', 'data-theater-motion']});
  window.addEventListener('storage', function (event) {
    if (event.key === 'zotheos_rain' || event.key === null) {
      level = levels.indexOf(event.newValue) >= 0 ? event.newValue : 'medium'; intensity();
    }
  });
  intensity();

  var translation = document.getElementById('site-translation');
  var select = document.getElementById('translateSection');
  var translate = document.getElementById('translateText');
  var texts = [];
  function prepareTranslation() {
    if (!translation || !select || !translate) return;
    var chosen = select.value;
    select.textContent = ''; texts = [];
    var heading = document.getElementById('theater-heading');
    var title = document.getElementById('theaterTitle');
    var sections = [
      ['story', 'Selected Story', title && title.closest('.th-now-watching')],
      ['introduction', 'Theater Introduction', heading && heading.parentElement],
      ['curation', 'Curation And Historical Context', document.getElementById('curation')]
    ];
    sections.forEach(function (section) {
      if (!section[2]) return;
      var copy = section[2].cloneNode(true);
      copy.querySelectorAll('script, style, iframe, form, input, textarea, select, button, summary, [contenteditable], [aria-hidden="true"], [hidden]').forEach(function (node) { node.remove(); });
      // Block headings and adjacent metadata spans need separators in exported reading text.
      copy.querySelectorAll('h1, h2, h3, h4, p, li, div, span, strong, a, time').forEach(function (node) {
        node.appendChild(document.createTextNode(' '));
      });
      var text = copy.textContent.replace(/\s+/g, ' ').trim(), parts = [];
      while (text.length > 4500) {
        var end = text.lastIndexOf(' ', 4500); if (end < 1) end = 4500;
        parts.push(text.slice(0, end)); text = text.slice(end).trim();
      }
      if (text) parts.push(text);
      parts.forEach(function (part, index) {
        var option = document.createElement('option');
        option.value = section[0] + '-' + index;
        option.textContent = section[1] + (parts.length > 1 ? ' (' + (index + 1) + ' Of ' + parts.length + ')' : '');
        texts.push({value: option.value, text: part}); select.appendChild(option);
      });
    });
    if (texts.some(function (part) { return part.value === chosen; })) select.value = chosen;
    updateTranslation();
  }
  function updateTranslation() {
    if (!select || !translate) return;
    var part = texts.find(function (item) { return item.value === select.value; });
    translate.href = 'https://translate.google.com/?sl=en&tl=es&op=translate&text=' + encodeURIComponent(part ? part.text : '');
  }
  if (select) select.addEventListener('change', updateTranslation);
  if (translate) translate.addEventListener('click', prepareTranslation);
  pop.querySelectorAll('a[href="#site-translation"]').forEach(function (link) {
    link.addEventListener('click', function () {
      if (!translation) return;
      prepareTranslation(); translation.open = true; close(false); focus(translation.querySelector('summary'));
    });
  });
  var story = document.getElementById('theaterTitle');
  if (story) new MutationObserver(prepareTranslation).observe(story, {childList: true, subtree: true, characterData: true});
  prepareTranslation();
  var back = document.getElementById('apReturnToFilm');
  if (back) back.addEventListener('click', function () {
    close(false); focus(story);
    if (story) story.scrollIntoView({block: 'start', behavior: 'instant'});
  });
})();

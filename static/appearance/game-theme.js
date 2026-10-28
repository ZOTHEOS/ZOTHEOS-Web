/* Cached game Appearance controls. The engine owns listener cleanup and redraws, never this module's timers. */
(function (global) {
  'use strict';
  var THEMES = [['', 'Sovereign Skeleton'], ['maya', 'Maya Radiance'], ['codex', 'Living Codex'], ['skeleton', 'Obsidian Ember'], ['calavera', 'Calavera Nocturne']];
  var PIGMENTS = { '#000': '#090716', '#fff': '#FFF3E8', '#e6e6e6': '#C9B4E5', '#b8b8b8': '#77E8BA', '#8c8c8c': '#E8BC72', '#ececec': '#77E8BA', '#bdbdbd': '#C9B4E5' };
  var KEY = 'zotheos_landing_theme';
  function valid(value) {
    for (var i = 0; i < THEMES.length; i++) if (THEMES[i][0] === value) return value;
    return '';
  }
  function savedTheme() {
    var value = document.documentElement.getAttribute('data-theme') || '';
    try { var saved = localStorage.getItem(KEY); if (saved !== null) value = saved; } catch (e) {}
    return valid(value);
  }
  function markup() {
    var selected = savedTheme(), h = '<fieldset class="zg-page-appearance"><legend>Appearance</legend><div class="zg-theme-options" role="radiogroup" aria-label="Appearance">';
    for (var i = 0; i < THEMES.length; i++) h += '<button type="button" role="radio" data-set="' + THEMES[i][0] + '" data-game-theme="' + THEMES[i][0] + '" aria-checked="' + (THEMES[i][0] === selected) + '" tabindex="' + (THEMES[i][0] === selected ? 0 : -1) + '">' + THEMES[i][1] + '</button>';
    return h + '</div></fieldset>';
  }
  // Every event goes through the engine's existing listener registry and is removed by its existing teardown.
  function bind(dialog, changed, listen) {
    function apply(value, save) {
      var selected = valid(value), doc = document.documentElement, buttons = dialog.querySelectorAll('[data-game-theme]'), i;
      if (selected) doc.setAttribute('data-theme', selected); else doc.removeAttribute('data-theme');
      var meta = document.getElementById('themeColorMeta');
      if (meta) meta.setAttribute('content', {maya:'#02101E',codex:'#E8DBC0',skeleton:'#050507',calavera:'#090716'}[selected] || '#000000');
      if (save) try { localStorage.setItem(KEY, selected); } catch (e) {}
      for (i = 0; i < buttons.length; i++) {
        var picked = buttons[i].getAttribute('data-game-theme') === selected;
        buttons[i].setAttribute('aria-checked', String(picked)); buttons[i].tabIndex = picked ? 0 : -1;
      }
      changed(selected);
    }
    function click(event) {
      var button = event.target;
      if (button && button.hasAttribute && button.hasAttribute('data-game-theme')) apply(button.getAttribute('data-game-theme'), true);
    }
    function key(event) {
      var buttons = this.querySelectorAll('[data-game-theme]'), at = -1, next, k = event.key || event.code, i;
      for (i = 0; i < buttons.length; i++) if (buttons[i] === document.activeElement) at = i;
      if (at < 0) return;
      if (k === 'ArrowRight' || k === 'ArrowDown') next = (at + 1) % buttons.length;
      else if (k === 'ArrowLeft' || k === 'ArrowUp') next = (at + buttons.length - 1) % buttons.length;
      else if (k === 'Home') next = 0;
      else if (k === 'End') next = buttons.length - 1;
      else return;
      event.preventDefault(); event.stopPropagation(); apply(buttons[next].getAttribute('data-game-theme'), true); buttons[next].focus();
    }
    var groups = dialog.querySelectorAll('.zg-theme-options');
    for (var i = 0; i < groups.length; i++) { listen(groups[i], 'click', click); listen(groups[i], 'keydown', key); }
    listen(global, 'storage', function (event) {
      if (event.key === KEY || event.key === null) apply(event.newValue || '', false);
    });
    apply(savedTheme(), false);
  }
  function pigment(value) { return typeof value === 'string' ? PIGMENTS[value] || value : value; }
  global.ZotheosGameTheme = {markup: markup, bind: bind, pigment: pigment};
})(window);

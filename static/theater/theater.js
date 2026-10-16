(function () {
  'use strict';
  var get = function (id) { return document.getElementById(id); };
  var cards = Array.from(document.querySelectorAll('[data-theater-film]'));
  var buttons = Array.from(document.querySelectorAll('[data-theater-select]'));
  var search = get('theaterSearch'), topic = get('theaterTopic');
  var slot = get('theaterPlayer'), load = get('theaterLoad'), close = get('theaterClose');
  if (!cards.length || !search || !topic || !slot || !load || !close) return;
  var selected = null;
  function playerURL(card) {
    var p = card.dataset.provider, id = card.dataset.videoId || '';
    if (p === 'youtube' && /^[A-Za-z0-9_-]{11}$/.test(id))
      return 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=0&playsinline=1&rel=0';
    if (p === 'pbs' && /^\d{10}$/.test(id)) {
      var route = card.dataset.pbsRoute || 'stationplayer';
      if (route !== 'stationplayer' && route !== 'viralplayer') return '';
      return 'https://player.pbs.org/' + route + '/' + id + '/?autoPlay=false&autoplay=0';
    }
    if (p === 'vimeo' && /^\d{6,12}$/.test(id))
      return 'https://player.vimeo.com/video/' + id + '?autoplay=0&dnt=1&title=0&byline=0&portrait=0';
    if (p === 'nfb' && /^[a-z0-9]+(?:_[a-z0-9]+)*$/.test(id) && id.length <= 100)
      return 'https://www.nfb.ca/film/' + id + '/embed/player/?autoplay=0';
    return '';
  }
  function stop(announce) {
    while (slot.firstChild) slot.removeChild(slot.firstChild);
    slot.hidden = true; close.hidden = true;
    var playable = selected && Boolean(playerURL(selected));
    load.disabled = !playable; load.hidden = !playable;
    if (announce) get('theaterPlayerStatus').textContent = 'Player closed. Use Load Player to prepare it again.';
  }
  function mount(focus) {
    if (!selected) return;
    var source = playerURL(selected);
    if (!source) return;
    var frame = slot.firstChild;
    if (frame && frame.src !== source) { stop(false); frame = null; }
    if (!frame) {
      frame = document.createElement('iframe'); frame.src = source;
      frame.title = selected.dataset.title + ' | ' + selected.dataset.provider + ' player';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
      frame.setAttribute('allowfullscreen', ''); slot.appendChild(frame);
    }
    slot.hidden = false; close.hidden = false; load.hidden = true;
    get('theaterPlayerStatus').textContent = 'Player loaded. Press Play in its controls. If unavailable, open the official source.';
    if (focus) { frame.focus(); frame.scrollIntoView({block:'center',behavior:'instant'}); }
  }
  function select(card, focus) {
    if (selected !== card) {
      // The initial publisher iframe, when present, is adopted without a second request.
      if (selected || !slot.firstChild || slot.firstChild.src !== playerURL(card)) stop(false);
      selected = card;
    }
    var fields = {theaterTitle:'title', theaterDescription:'summary', theaterAvailability:'availability',
      theaterKind:'kind', theaterContentNote:'contentNote', theaterCredits:'credits'};
    Object.keys(fields).forEach(function (id) { if (get(id)) get(id).textContent = card.dataset[fields[id]] || ''; });
    if (get('theaterRuntime')) get('theaterRuntime').textContent = card.dataset.runtime || '';
    var watch = get('theaterWatch');
    try {
      var u = new URL(card.dataset.watchUrl);
      if (u.protocol !== 'https:' || u.username || u.password) throw new Error('Invalid destination');
      watch.href = u.href;
    } catch (_) { watch.href = '/theater'; }
    var sources = get('theaterSources');
    if (sources) {
      while (sources.firstChild) sources.removeChild(sources.firstChild);
      card.querySelectorAll('.th-source-list li').forEach(function (item) { sources.appendChild(item.cloneNode(true)); });
    }
    buttons.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.theaterSelect === card.dataset.theaterFilm)); });
    var playable = Boolean(playerURL(card));
    load.hidden = !playable; load.disabled = !playable;
    if (playable) mount(focus);
    else {
      stop(false);
      get('theaterPlayerStatus').textContent = (card.dataset.availability || '') + ' Open the official source to continue.';
      if (focus) { get('theaterTitle').focus(); get('theaterTitle').scrollIntoView({block:'start',behavior:'instant'}); }
    }
  }
  function fold(value) { return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase(); }
  function filter() {
    var words = fold(search.value.trim()).split(/\s+/).filter(Boolean), count = 0;
    cards.forEach(function (card) {
      var hay = fold(card.dataset.search || '');
      var matches = words.every(function (word) { return hay.indexOf(word) !== -1; }) &&
        (topic.value === 'all' || (card.dataset.topic || '').split(/\s+/).indexOf(topic.value) !== -1);
      card.hidden = !matches; if (matches) count++;
    });
    get('theaterEmpty').hidden = count !== 0;
    get('theaterStatus').textContent = count + (count === 1 ? ' title' : ' titles') + ' in this selection.';
  }
  search.addEventListener('input', filter); topic.addEventListener('change', filter);
  get('theaterClear').addEventListener('click', function () { search.value = ''; topic.value = 'all'; filter(); search.focus(); });
  buttons.forEach(function (button) {
    button.hidden = false;
    button.setAttribute('role', 'button');
    button.addEventListener('keydown', function (event) {
      if (event.key === ' ' && button.tagName === 'A') { event.preventDefault(); button.click(); }
    });
    button.addEventListener('click', function (event) {
      if (button.tagName === 'A' && event && (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || (event.button != null && event.button !== 0))) return;
      if (event && event.preventDefault) event.preventDefault();
      var card = cards.find(function (candidate) { return candidate.dataset.theaterFilm === button.dataset.theaterSelect; });
      if (card) select(card, true);
    });
  });
  load.addEventListener('click', function () { mount(true); });
  close.addEventListener('click', function () { stop(true); if (!load.hidden) load.focus(); });
  var motion = get('theaterMotion'), paused = false;
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  function updateMotion() {
    var globalMode = document.documentElement.getAttribute('data-motion');
    var locked = reduced.matches || globalMode === 'still' || globalMode === 'calm';
    var still = locked || paused;
    document.documentElement.setAttribute('data-theater-motion', still ? 'still' : 'ambient');
    if (motion) {
      motion.setAttribute('aria-pressed', String(still));
      motion.setAttribute('aria-disabled', String(locked));
      motion.title = locked ? 'Your motion preference keeps the frame still.' : 'Pause or restore the subtle ambient frame.';
    }
  }
  if (motion) motion.addEventListener('click', function () {
    if (motion.getAttribute('aria-disabled') !== 'true') paused = !paused;
    updateMotion();
  });
  if (reduced.addEventListener) reduced.addEventListener('change', updateMotion);
  else if (reduced.addListener) reduced.addListener(updateMotion);
  new MutationObserver(updateMotion).observe(document.documentElement, {attributes:true,attributeFilter:['data-motion']});
  updateMotion();
  get('theaterTools').hidden = false;
  select(cards.find(function (card) { return card.dataset.featured === 'true'; }) || cards[0], false);
  filter();
}());

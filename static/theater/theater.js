(function () {
  'use strict';
  var get = function (id) { return document.getElementById(id); };
  var cards = Array.from(document.querySelectorAll('[data-theater-film]'));
  var buttons = Array.from(document.querySelectorAll('[data-theater-select]'));
  var search = get('theaterSearch'), topic = get('theaterTopic'), region = get('theaterRegion'), viewing = get('theaterViewing');
  var slot = get('theaterPlayer'), more = get('theaterMore'), next = get('theaterNext');
  if (!cards.length || !search || !topic || !slot) return;
  var selected = null, limit = more ? 24 : Infinity, matched = cards.slice();
  var segment = /^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$/;
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
    if (p === 'nfb' && segment.test(id) && id.length <= 100) {
      var preview = card.dataset.nfbPreview || '', previewType = card.dataset.nfbPreviewType || '';
      if (preview && (!segment.test(preview) || preview.length > 100 || (previewType !== 'trailer' && previewType !== 'promo_clip'))) return '';
      return 'https://www.nfb.ca/film/' + id + '/' + (preview ? previewType + '/' + preview + '/' : '') + 'embed/player/?auto_play=false&autoplay=0';
    }
    return '';
  }
  function stop() {
    while (slot.firstChild) slot.removeChild(slot.firstChild);
    slot.hidden = true;
  }
  function mount(focus) {
    var source = playerURL(selected);
    if (!source) return;
    var frame = slot.firstChild;
    if (frame && frame.src !== source) { stop(); frame = null; }
    if (!frame) {
      frame = document.createElement('iframe'); frame.src = source;
      frame.title = selected.dataset.title + ' | ' + selected.dataset.provider + ' player';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
      frame.setAttribute('allowfullscreen', ''); slot.appendChild(frame);
    }
    slot.hidden = false;
    get('theaterPlayerStatus').textContent = 'Ready to watch. Press Play in the video. If unavailable, open its official source.';
    if (focus) { frame.focus(); frame.scrollIntoView({block:'center',behavior:'instant'}); }
  }
  function select(card, focus) {
    if (selected !== card) {
      if (selected || !slot.firstChild || slot.firstChild.src !== playerURL(card)) stop();
      selected = card;
    }
    var fields = {theaterTitle:'title', theaterDescription:'summary', theaterAvailability:'availability',
      theaterKind:'kind', theaterContentNote:'contentNote', theaterCredits:'credits', theaterLocation:'location', theaterRuntime:'runtime'};
    Object.keys(fields).forEach(function (id) { if (get(id)) get(id).textContent = card.dataset[fields[id]] || ''; });
    var watch = get('theaterWatch');
    try {
      var raw = card.dataset.watchUrl || '', u = new URL(raw);
      if (u.protocol !== 'https:' || u.username || u.password || u.port === '0' || /^https:\/\/[^/?#]*:(?:[/?#]|$)/.test(raw) || /[\\\s]/.test(raw)) throw new Error('Invalid destination');
      watch.href = u.href;
    } catch (_) { watch.href = '/theater'; }
    var sources = get('theaterSources');
    if (sources) {
      while (sources.firstChild) sources.removeChild(sources.firstChild);
      card.querySelectorAll('.th-source-list li').forEach(function (item) { sources.appendChild(item.cloneNode(true)); });
    }
    buttons.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.theaterSelect === card.dataset.theaterFilm)); });
    if (playerURL(card)) mount(focus);
    else {
      stop();
      get('theaterPlayerStatus').textContent = (card.dataset.availability || '') + ' Open the official source to continue.';
      if (focus) { get('theaterTitle').focus(); get('theaterTitle').scrollIntoView({block:'start',behavior:'instant'}); }
    }
  }
  function fold(value) { return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase(); }
  function showMatches() {
    cards.forEach(function (card) { var i = matched.indexOf(card); card.hidden = i === -1 || i >= limit; });
    get('theaterEmpty').hidden = matched.length !== 0;
    var shown = Math.min(limit, matched.length);
    get('theaterStatus').textContent = shown < matched.length ? 'Showing ' + shown + ' of ' + matched.length + ' stories.' : matched.length + (matched.length === 1 ? ' title' : ' titles') + ' in this selection.';
    if (more) { more.hidden = shown >= matched.length; more.textContent = 'Show ' + Math.min(24, matched.length - shown) + ' More Stories'; }
    if (next) next.disabled = matched.length < 2;
  }
  function filter() {
    var words = fold(search.value.trim()).split(/\s+/).filter(Boolean);
    matched = cards.filter(function (card) {
      var hay = fold(card.dataset.search || '');
      return words.every(function (word) { return hay.indexOf(word) !== -1; }) &&
        (topic.value === 'all' || (card.dataset.topic || '').split(/\s+/).indexOf(topic.value) !== -1) &&
        (!region || region.value === 'all' || (card.dataset.region || 'unindexed') === region.value) &&
        (!viewing || viewing.value === 'all' || card.dataset.viewing === viewing.value);
    });
    limit = more ? 24 : Infinity;
    showMatches();
  }
  search.addEventListener('input', filter); topic.addEventListener('change', filter);
  if (region) region.addEventListener('change', filter);
  if (viewing) viewing.addEventListener('change', filter);
  if (more) more.addEventListener('click', function () {
    var firstNew = matched[limit]; limit += 24; showMatches();
    var poster = firstNew && buttons.find(function (b) { return b.dataset.theaterSelect === firstNew.dataset.theaterFilm; });
    if (poster) { poster.focus(); poster.scrollIntoView({block:'nearest',behavior:'instant'}); }
  });
  if (next) next.addEventListener('click', function () {
    if (!matched.length) return;
    var i = (matched.indexOf(selected) + 1) % matched.length;
    if (more && i >= limit) { limit = Math.ceil((i + 1) / 24) * 24; showMatches(); }
    select(matched[i], true);
  });
  get('theaterClear').addEventListener('click', function () {
    search.value = ''; topic.value = 'all'; if (region) region.value = 'all'; if (viewing) viewing.value = 'all'; filter(); search.focus();
  });
  buttons.forEach(function (button) {
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
  var motion = get('theaterMotion'), paused = false;
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  function updateMotion() {
    var mode = document.documentElement.getAttribute('data-motion');
    var locked = reduced.matches || mode === 'still' || mode === 'calm';
    var still = locked || paused;
    document.documentElement.setAttribute('data-theater-motion', still ? 'still' : 'ambient');
    if (motion) {
      motion.setAttribute('aria-pressed', String(still)); motion.setAttribute('aria-disabled', String(locked));
      motion.title = locked ? 'Your motion preference keeps the frame still.' : 'Pause or restore the subtle ambient frame.';
    }
  }
  if (motion) motion.addEventListener('click', function () { if (motion.getAttribute('aria-disabled') !== 'true') paused = !paused; updateMotion(); });
  if (reduced.addEventListener) reduced.addEventListener('change', updateMotion);
  else if (reduced.addListener) reduced.addListener(updateMotion);
  new MutationObserver(updateMotion).observe(document.documentElement, {attributes:true,attributeFilter:['data-motion']});
  updateMotion();
  get('theaterTools').hidden = false;
  if (next) next.hidden = false;
  if (motion) motion.hidden = false;
  select(cards.find(function (card) { return card.dataset.featured === 'true'; }) || cards[0], false);
  filter();
}());

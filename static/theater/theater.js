(function () {
  'use strict';
  var get = function (id) { return document.getElementById(id); };
  var cards = Array.from(document.querySelectorAll('[data-theater-film]'));
  var search = get('theaterSearch'), topic = get('theaterTopic');
  var slot = get('theaterPlayer'), load = get('theaterLoad'), close = get('theaterClose');
  if (!cards.length || !search || !topic || !slot || !load || !close) return;
  var selected = null;
  function valid(card) {
    var p = card.dataset.provider, id = card.dataset.videoId || '';
    return (p === 'youtube' && /^[A-Za-z0-9_-]{11}$/.test(id)) ||
      (p === 'pbs' && /^\d{10}$/.test(id));
  }
  function stop(announce) {
    while (slot.firstChild) slot.removeChild(slot.firstChild);
    slot.hidden = true;
    close.hidden = true;
    load.disabled = !selected || !valid(selected);
    load.hidden = !selected || !valid(selected);
    if (announce) get('theaterPlayerStatus').textContent = 'Player closed. Load it again only when you choose.';
  }
  function select(card, focus) {
    stop(false); selected = card;
    var fields = {theaterTitle:'title', theaterDescription:'summary', theaterAvailability:'availability',
      theaterKind:'kind', theaterContentNote:'contentNote', theaterCredits:'credits'};
    Object.keys(fields).forEach(function (id) { get(id).textContent = card.dataset[fields[id]] || ''; });
    var watch = get('theaterWatch');
    // Only HTTPS publisher destinations already validated by the static builder.
    try {
      var u = new URL(card.dataset.watchUrl);
      if (u.protocol !== 'https:' || u.username || u.password) throw new Error('Invalid destination');
      watch.href = u.href;
    } catch (_) { watch.href = '/theater'; }
    var playable = valid(card);
    load.hidden = !playable; load.disabled = !playable;
    load.textContent = 'Load ' + (card.dataset.provider === 'pbs' ? 'PBS' : 'YouTube') + ' Player';
    get('theaterConsent').hidden = !playable;
    get('theaterPlayerStatus').textContent = playable ? 'No player is loaded. Choosing this title does not contact a video provider.' :
      'Use the official source below. This title has no player on this page.';
    if (focus) { var target = playable ? load : get('theaterTitle'); target.focus(); target.scrollIntoView({block:playable ? 'center' : 'start',behavior:'instant'}); }
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
  document.querySelectorAll('[data-theater-select]').forEach(function (button) {
    button.hidden = false;
    button.addEventListener('click', function () {
      var card = cards.find(function (candidate) { return candidate.dataset.theaterFilm === button.dataset.theaterSelect; });
      if (card) select(card, true);
    });
  });
  load.addEventListener('click', function () {
    if (!selected || !valid(selected) || slot.firstChild) return;
    var provider = selected.dataset.provider, frame = document.createElement('iframe');
    frame.src = provider === 'pbs' ? 'https://player.pbs.org/stationplayer/' + selected.dataset.videoId + '/?autoplay=0' :
      'https://www.youtube-nocookie.com/embed/' + selected.dataset.videoId + '?autoplay=0&playsinline=1&rel=0';
    frame.title = selected.dataset.title + ' | ' + (provider === 'pbs' ? 'PBS' : 'YouTube') + ' player';
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
    frame.setAttribute('allowfullscreen', '');
    slot.hidden = false; slot.appendChild(frame);
    close.hidden = false; load.hidden = true;
    get('theaterPlayerStatus').textContent = 'Player loaded. Press play in its controls. If unavailable, open the official source below.';
    frame.focus(); frame.scrollIntoView({block:'center',behavior:'instant'});
  });
  close.addEventListener('click', function () { stop(true); if (!load.hidden) load.focus(); });
  get('theaterTools').hidden = false;
  select(cards.find(function (card) { return card.dataset.featured === 'true'; }) || cards[0], false);
  filter();
}());

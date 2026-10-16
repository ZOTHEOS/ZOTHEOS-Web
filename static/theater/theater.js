(function () {
  'use strict';
  /* One selected provider player; muted in-view previews with explicit visitor controls. */
  var d = document.documentElement;
  var get = function (id) { return document.getElementById(id); };
  var PREVIEW_AUTOPLAY = d.getAttribute('data-preview-autoplay') === 'on';
  var cards = Array.prototype.slice.call(document.querySelectorAll('[data-theater-film]'));
  var posters = Array.prototype.slice.call(document.querySelectorAll('[data-theater-select]'));
  var search = get('theaterSearch'), topic = get('theaterTopic'), region = get('theaterRegion'), viewing = get('theaterViewing');
  var access = get('theaterAccess'), permalink = get('theaterPermalink');
  var slot = get('theaterPlayer'), more = get('theaterMore'), next = get('theaterNext');
  var section = get('screening'), shell = get('theaterStage'), screenEl = get('theaterScreen');
  var composedSvg = get('theaterFrameComposed'), titleEl = get('theaterTitle');
  var curtain = get('theaterCurtain'), curtainImg = get('theaterCurtainImg'), curtainText = get('theaterCurtainText'), curtainSource = get('theaterCurtainSource'), curtainPlay = get('theaterCurtainPlay');
  var statusLine = get('theaterPlayerStatus'), announcer = get('theaterAnnounce'), playBtn = get('theaterPlay'), soundBtn = get('theaterSound'), ccBtn = get('theaterCC');
  var lightBtn = get('theaterMotion'), backLink = get('theaterBack'), nativeNote = get('theaterNativeNote'), progress = get('theaterProgress');
  var filtersToggle = get('theaterFiltersToggle'), filterPanel = get('theaterFilterPanel'), filterCount = get('theaterFilterCount');
  var railList = get('theaterUpNextList'), dock = get('theaterDock');
  if (!cards.length || !search || !topic || !slot) return;

  var NAMES = { youtube: 'YouTube', vimeo: 'Vimeo', pbs: 'PBS', nfb: 'National Film Board' };
  var YT = 'https://www.youtube-nocookie.com', VIMEO = 'https://player.vimeo.com';
  var STEP = 24, RAIL = 8;
  var every = typeof setInterval === 'function' ? setInterval : null, stopEvery = typeof clearInterval === 'function' ? clearInterval : function () {};
  var later = typeof setTimeout === 'function' ? setTimeout : function (fn) { fn(); return 0; };
  var cancel = typeof clearTimeout === 'function' ? clearTimeout : function () {};
  var now = function () { return Date.now(); };
  var media = function (q) { try { return window.matchMedia ? window.matchMedia(q) : null; } catch (e) { return null; } };
  var reducedQuery = media('(prefers-reduced-motion: reduce)'), wideQuery = media('(min-width: 720px)');
  var selected = null, originCard = null, limit = more ? STEP : Infinity, matched = cards.slice();

  /* ---------- record text lives once, in the card's own markup (also the no-script fallback) ---------- */
  function text(root, sel) { var n = root.querySelector(sel); return n ? String(n.textContent).replace(/\s+/g, ' ').trim() : ''; }
  function attr(card, name) { return card.getAttribute(name) || ''; }
  function record(card) {
    return {
      id: attr(card, 'data-theater-film'),
      title: text(card, '.th-film-title') || attr(card, 'data-title'),
      summary: text(card, '.th-description') || attr(card, 'data-summary'),
      credits: text(card, '.th-film-credits') || attr(card, 'data-credits'),
      availability: text(card, '.th-film-access') || attr(card, 'data-availability'),
      note: text(card, '.th-content-note > span') || attr(card, 'data-content-note'),
      perspective: text(card, '.th-film-perspective > span'),
      publisher: text(card, '.th-card-publisher') || attr(card, 'data-publisher'),
      place: text(card, '.th-card-place') || attr(card, 'data-location'),
      kind: attr(card, 'data-kind'), form: attr(card, 'data-form'), runtime: attr(card, 'data-runtime'), year: attr(card, 'data-year')
    };
  }
  function fold(value) { return String(value).normalize('NFD').replace(/[̀-ͯ]/g, '').toLocaleLowerCase(); }
  var topicNames = {};
  Array.prototype.forEach.call(topic.options || [], function (o) { topicNames[o.value] = o.textContent; });
  /* The searchable text of a card: title (with any original title), synopsis, credits, publisher, place, form and
     subjects, read from the card markup the first time a search needs it. */
  var hay = new Map();
  function hayOf(card) {
    var ds = card.getAttribute('data-search');
    if (ds) return fold(ds);
    if (!hay.has(card)) {
      var r = record(card);
      var topics = attr(card, 'data-topic').split(/\s+/).map(function (t) { return topicNames[t] || ''; }).join(' ');
      hay.set(card, fold([r.title, attr(card, 'data-title'), r.summary, r.credits, r.publisher, r.place, r.form, topics].join(' ')));
    }
    return hay.get(card);
  }
  function posterFor(card) { return card.querySelector('[data-theater-select]'); }
  function cardFor(id) { for (var i = 0; i < cards.length; i++) if (cards[i].getAttribute('data-theater-film') === id) return cards[i]; return null; }
  function seconds(runtime) {
    var m = /(\d+)\s*h/.exec(runtime || ''), n = /(\d+)\s*m/.exec(runtime || ''), s = /(\d+)\s*s\b/.exec(runtime || '');
    var t = (m ? +m[1] * 3600 : 0) + (n ? +n[1] * 60 : 0) + (s ? +s[1] : 0);
    return t || 0;
  }

  /* ---------- player addresses: the published allowlist and patterns, unchanged; with the switch on, the address
     names this page's origin for the provider's message API, and when the page may start this story's preview by
     itself the address also holds the sound off (mute=1 / muted=1), so a lost message can never let sound start.
     A story the page will not preview keeps a normal address: its own Play plays with sound. ---------- */
  var segment = /^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$/;
  var ccWanted = PREVIEW_AUTOPLAY, soundWanted = false, soundChosenOff = false;
  function langOf(card, trailer) { var l = attr(card, trailer ? 'data-trailer-cap-lang' : 'data-cap-lang'); return /^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$/.test(l) ? l : ''; }
  function origin() { try { return window.location.origin || ''; } catch (e) { return ''; } }
  function playerURL(card, trailer, quiet) {
    var p = card.getAttribute('data-provider'), id = card.getAttribute('data-video-id') || '';
    if (trailer && p === 'youtube') id = card.getAttribute('data-trailer-id') || '';
    if (p === 'youtube' && /^[A-Za-z0-9_-]{11}$/.test(id)) {
      var lang = langOf(card, trailer), o = origin();
      return YT + '/embed/' + id + '?autoplay=0&playsinline=1&rel=0' + (PREVIEW_AUTOPLAY ? '&enablejsapi=1' + (quiet ? '&mute=1' : '') + (o ? '&origin=' + encodeURIComponent(o) : '') +
        (ccWanted ? '&cc_load_policy=1' + (lang ? '&cc_lang_pref=' + lang : '') : '') : '');
    }
    if (p === 'pbs' && /^\d{10}$/.test(id)) {
      var route = card.getAttribute('data-pbs-route') || 'stationplayer';
      if (route !== 'stationplayer' && route !== 'viralplayer') return '';
      return 'https://player.pbs.org/' + route + '/' + id + '/?autoPlay=false&autoplay=0';
    }
    if (p === 'vimeo' && /^\d{6,12}$/.test(id))
      return VIMEO + '/video/' + id + '?autoplay=0&dnt=1&title=0&byline=0&portrait=0' + (PREVIEW_AUTOPLAY ? (quiet ? '&muted=1' : '') + '&playsinline=1' : '');
    if (p === 'nfb' && segment.test(id) && id.length <= 100) {
      var preview = card.getAttribute('data-nfb-preview') || '', previewType = card.getAttribute('data-nfb-preview-type') || '';
      if (preview && (!segment.test(preview) || preview.length > 100 || (previewType !== 'trailer' && previewType !== 'promo_clip'))) return '';
      return 'https://www.nfb.ca/film/' + id + '/' + (preview ? previewType + '/' + preview + '/' : '') + 'embed/player/?auto_play=false&autoplay=0';
    }
    return '';
  }
  /* The autoplay permission lets a muted preview start and lets Sound On keep playing in the cross-origin frame. */
  function allowList(kind) { return (hasAPI(kind) ? 'autoplay; ' : '') + 'encrypted-media; picture-in-picture; fullscreen'; }

  /* ---------- motion policy ---------- */
  function motion() { return d.getAttribute('data-motion') || 'living'; }
  function held() { return d.getAttribute('data-motion-ask') === 'pending'; }
  function floor() { return !!(reducedQuery && reducedQuery.matches); }
  function ambientLocked() { var m = motion(); return m === 'still' || m === 'calm' || held() || floor(); }
  /* The owner's direction: previews start without sound in Living and in Calm (Calm only rests the frame light);
     Still never starts anything on its own. */
  function previewMode() { var m = motion(); return !floor() && (m === 'living' || m === 'calm'); }
  function saveData() {
    try { var c = navigator.connection; return !!c && (c.saveData === true || /^(slow-2g|2g)$/.test(String(c.effectiveType || ''))); } catch (e) { return false; }
  }

  /* ---------- the one connected player ---------- */
  var player = null, inView = false, barSeen = false, onScreen = true, ratio = 1, userPaused = false, autoStarted = false, deliberate = false, pausedFor = '';
  var pending = { play: 0, pause: 0, unmute: 0, mute: 0 }, frozen = false, capped = false, gesture = false, playOnReady = false;
  var arrival = null, restUntil = 0, advisoryUntil = 0, startedOnce = {};
  function hasAPI(kind) { return PREVIEW_AUTOPLAY && (kind === 'youtube' || kind === 'vimeo'); }
  function post(msg) {
    if (!player || !player.frame || !player.frame.contentWindow) return;
    try { player.frame.contentWindow.postMessage(player.kind === 'youtube' ? JSON.stringify(msg) : msg, player.origin); } catch (e) {}
  }
  var adapters = {
    youtube: {
      hello: function () { post({ event: 'listening', id: 1, channel: 'widget' }); },
      cmd: function (f, a) { post({ event: 'command', func: f, args: a || [], id: 1, channel: 'widget' }); },
      subscribe: function () { var self = this; ['onStateChange', 'onError', 'onApiChange'].forEach(function (n) { self.cmd('addEventListener', [n]); }); },
      play: function () {
        if (player && player.state === 'ended') this.cmd('seekTo', [0, true]);
        else if (player && player.resumeAt) { this.cmd('seekTo', [player.resumeAt, true]); player.resumeAt = 0; }
        this.cmd('playVideo');
      },
      pause: function () { this.cmd('pauseVideo'); },
      /* a preview that reached its limit stops loading too (pauseVideo keeps buffering ahead); Play resumes at the spot */
      stop: function () { if (player) player.resumeAt = player.time || 0; this.cmd('stopVideo'); },
      mute: function () { this.cmd('mute'); }, unmute: function () { this.cmd('unMute'); },
      /* Ask the provider to select or clear its caption track. The state word changes only when the provider
         reports the new track; sending the request does not establish that captions changed. */
      captions: function (on) {
        if (on) { this.cmd('loadModule', ['captions']); this.cmd('setOption', ['captions', 'track', { languageCode: (player && player.capLang) || 'en' }]); }
        else this.cmd('setOption', ['captions', 'track', {}]);
      }
    },
    vimeo: {
      hello: function () { post({ method: 'ping' }); },
      cmd: function (m, v) { post(v === undefined ? { method: m } : { method: m, value: v }); },
      subscribe: function () { var self = this; ['play', 'playing', 'pause', 'ended', 'volumechange', 'error', 'texttrackchange'].forEach(function (n) { self.cmd('addEventListener', n); }); self.cmd('getTextTracks'); },
      play: function () { this.cmd('play'); }, pause: function () { this.cmd('pause'); }, stop: function () { this.cmd('pause'); },
      mute: function () { this.cmd('setMuted', true); }, unmute: function () { this.cmd('setMuted', false); },
      captions: function (on) {
        var t = player && player.tracks && (player.tracks.filter(function (x) { return player.capLang && x.language.indexOf(player.capLang) === 0; })[0] || player.tracks[0]);
        if (on && t) this.cmd('enableTextTrack', { language: t.language, kind: t.kind });
        else if (!on) this.cmd('disableTextTrack');
      }
    }
  };
  function adapter() { return player && player.api ? adapters[player.kind] : null; }
  function requestSound(muted) {
    var a = adapter();
    if (!a) return;
    pending[muted ? 'unmute' : 'mute'] = 0;
    pending[muted ? 'mute' : 'unmute'] = now();
    if (muted) a.mute(); else a.unmute();
  }

  /* Only messages from the current frame's window and its provider's exact origin are read. */
  window.addEventListener('message', function (e) {
    if (!player || !player.api || e.origin !== player.origin || !player.frame || e.source !== player.frame.contentWindow) return;
    var data = e.data;
    if (typeof data === 'string') { if (data.length > 100000) return; try { data = JSON.parse(data); } catch (_) { return; } }
    if (!data || typeof data !== 'object' || frozen) return;
    if (player.kind === 'youtube') readYouTube(data); else readVimeo(data);
  });
  function readYouTube(m) {
    var ev = m.event, inf = m.info;
    if (ev === 'onReady' || ev === 'initialDelivery') ready();
    if (inf && typeof inf === 'object') {
      if (typeof inf.currentTime === 'number' && isFinite(inf.currentTime)) player.time = inf.currentTime;
      if (typeof inf.muted === 'boolean') setMuted(inf.muted);
      if (typeof inf.playerState === 'number') providerState(inf.playerState);
      if (inf.captions && typeof inf.captions === 'object') readCaptions(inf.captions);
    }
    if (ev === 'onStateChange' && typeof inf === 'number') providerState(inf);
    if (ev === 'onError') failed();
  }
  /* Caption truth comes from the provider: On or Auto only for an active reported track; None for an empty list. */
  function readCaptions(c) {
    var cc = player.cc, list = c.tracklist, track = c.track;
    var active = !!(track && typeof track === 'object' && typeof track.languageCode === 'string' && track.languageCode);
    if (Array.isArray(list)) {
      cc.listed = list.length > 0 || active;
      /* the data is a snapshot of the watch page; an empty list once playback has begun is this player's own answer */
      if (!cc.listed && !cc.open && (moving() || pending.play)) cc.none = true;   /* words in the picture need no track */
      /* a preview the page started must offer captions: without them it stops and waits for the visitor */
      if (cc.none && autoStarted && !deliberate) { capped = true; pausedFor = 'captions'; adapter().pause(); pending.pause = now(); }
    }
    if (track !== undefined) {
      cc.reported = true; cc.active = active; cc.auto = active && track.kind === 'asr';
      if (active && !player.capLang) player.capLang = track.languageCode;
    }
    if (Array.isArray(list) && list.length && !player.capLang) {
      var first = list[0]; if (first && typeof first.languageCode === 'string') player.capLang = first.languageCode;
    }
    cc.loaded = true;
    if (!ccWanted && cc.active && !cc.offSent) { cc.offSent = true; adapters.youtube.captions(false); }
    if (ccWanted && !cc.active && cc.listed && !cc.onSent && moving()) { cc.onSent = true; adapters.youtube.captions(true); }
    render();
  }
  function readVimeo(m) {
    var ev = m.event, method = m.method;
    if (ev === 'ready' || (typeof method === 'string' && method)) ready();
    if (method === 'getTextTracks' && Array.isArray(m.value)) {
      player.tracks = m.value.filter(function (t) { return t && typeof t.language === 'string' && (t.kind === 'captions' || t.kind === 'subtitles'); }).slice(0, 40);
      player.cc.listed = player.tracks.length > 0; player.cc.none = !player.tracks.length; player.cc.loaded = true;
      if (player.tracks.length && ccWanted) adapters.vimeo.captions(true);
      maybePreview();
      render();
    }
    if (ev === 'play' || ev === 'playing') providerState(1);
    else if (ev === 'pause') providerState(2);
    else if (ev === 'ended') providerState(0);
    else if (ev === 'error') failed();
    else if (ev === 'volumechange' && m.data && typeof m.data === 'object') {
      if (typeof m.data.muted === 'boolean') setMuted(m.data.muted); else if (typeof m.data.volume === 'number') setMuted(m.data.volume === 0);
    } else if (ev === 'texttrackchange' && m.data && typeof m.data === 'object') {
      player.cc.reported = true; player.cc.active = !!m.data.language; player.cc.auto = false; render();
    }
  }
  function ready() {
    if (!player || player.ready) return;
    player.ready = true;
    stopEvery(player.helloTimer); cancel(player.slowTimer);
    adapter().subscribe();
    hideCurtain();
    stage('ready');
    if (playOnReady) { playOnReady = false; startDeliberate(); }
    else maybePreview();
  }
  function moving() { return !!(player && (player.state === 'playing' || player.state === 'buffering')); }
  /* Provider states: 1 playing, 3 buffering, 2 paused, 0 ended, -1 and 5 ready. A start or a pause that the page did
     not request a moment earlier came from the visitor's own use of the native controls. */
  function providerState(s) {
    if (!player || player.error) return;
    var t = now();
    var named = s === 1 ? 'playing' : s === 3 ? 'buffering' : s === 2 ? 'paused' : s === 0 ? 'ended' : 'ready';
    if (named === player.state) return;
    var wasMoving = moving();
    if (s === 1 || s === 3) {
      if (!wasMoving) {
        if (!(pending.play && t - pending.play < 9000)) { deliberate = true; userPaused = false; autoStarted = false; capped = false; }
        pending.play = 0; pausedFor = '';
        var id = player.card.getAttribute('data-theater-film'), note = record(player.card).note;
        /* A start the visitor's own Play did not ask for (the page's preview, or a story chosen from a poster or Next
           Story that then started by itself) shows the Before Watching note in the status slot for 12 seconds. */
        if (player.previewStart && !startedOnce[id]) {
          startedOnce[id] = true;
          if (note) { advisoryUntil = t + 12000; later(render, 12050); }
          announce(playingText() + (note ? ' Before watching: ' + note : ''), true);
        }
        if (ccWanted && player.kind === 'youtube' && !player.cc.onSent && player.cc.listed !== false) { player.cc.onSent = true; adapters.youtube.captions(true); }
      }
      hideCurtain(true);
      stage(named);
    } else if (s === 2) {
      if (pending.pause && t - pending.pause < 6000) pending.pause = 0;
      else if (wasMoving) { userPaused = true; deliberate = false; autoStarted = false; pausedFor = 'visitor'; }
      restUntil = t + 2000; later(lights, 2050);
      stage('paused');
    } else if (s === 0) { autoStarted = false; restUntil = t + 2000; later(lights, 2050); stage('ended'); announce(statusText('ended'), true); }
    else stage('ready');
  }
  function setMuted(m) {
    if (!player) return;
    var t = now();
    if (m === false && pending.mute && t - pending.mute < 2500) return;   /* a report sent before the mute request arrived */
    if (m === false && player.muted === true && !(pending.unmute && t - pending.unmute < 5000)) { deliberate = true; autoStarted = false; }
    if (m === false) pending.unmute = 0; else pending.mute = 0;
    player.muted = m;
    render();
  }
  function failed() {
    if (!player) return;
    player.error = true;
    stopEvery(player.helloTimer); cancel(player.slowTimer);
    showCurtain(player.card, 'unavailable');
    stage('unavailable');
    announce(statusText('unavailable'), true);
  }

  function stop() {
    if (player) { stopEvery(player.helloTimer); cancel(player.slowTimer); cancel(player.capTimer); }
    pending = { play: 0, pause: 0, unmute: 0, mute: 0 };
    player = null; autoStarted = false; deliberate = false; pausedFor = ''; arrival = null; playOnReady = false;
    while (slot.firstChild) slot.removeChild(slot.firstChild);
    slot.hidden = true;
  }
  function frameTitle(card, kind) { return record(card).title + ', ' + (NAMES[kind] || 'provider') + ' player'; }
  /* Exactly one player: choosing a story replaces the old frame. The no-script frame is never reused, so a story
     link never contacts the featured provider first. A full film's page-started preview plays its trailer in the same
     single frame; the visitor's own Play mounts the film itself in its place. */
  function mount(card, opts) {
    opts = opts || {};
    stop();
    var useTrailer = !!opts.trailer;
    var quiet = previewPossible(card);
    var frame = document.createElement('iframe');
    frame.src = playerURL(card, useTrailer, quiet);
    frame.title = frameTitle(card, card.getAttribute('data-provider')) + (useTrailer ? ' (trailer)' : '');
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.setAttribute('allow', allowList(card.getAttribute('data-provider')));
    frame.setAttribute('allowfullscreen', '');
    slot.appendChild(frame);
    slot.hidden = false;
    var kind = card.getAttribute('data-provider');
    var capKind = attr(card, useTrailer ? 'data-trailer-captions' : 'data-captions');
    player = { card: card, frame: frame, kind: kind, api: hasAPI(kind), origin: kind === 'youtube' ? YT : kind === 'vimeo' ? VIMEO : '',
               ready: false, state: 'loading', muted: quiet ? true : null, trailer: useTrailer, capLang: langOf(card, useTrailer),
               cc: { listed: null, none: false, open: capKind === 'open', auto: false, active: false, reported: false, loaded: false },
               tracks: null, error: false };
    var p = player;
    frame.addEventListener('load', function () {
      if (player !== p || frozen) return;
      hideCurtain();
      if (!p.api) { p.ready = true; cancel(p.slowTimer); stage('ready'); }
      else if (!p.ready) adapters[p.kind].hello();
    });
    stage('loading');
    if (p.api && every) {
      var tries = 0;
      p.helloTimer = every(function () { if (player !== p || p.ready || ++tries > 80) { stopEvery(p.helloTimer); return; } adapters[p.kind].hello(); }, 250);
    }
    p.slowTimer = later(function () { if (player === p && !p.ready && !p.error) { p.slow = true; if (curtain) curtain.setAttribute('data-connect', 'done'); render(); } }, 15000);
  }

  /* ---------- preview policy ---------- */
  function previewState(card) { return card ? attr(card, 'data-preview') : ''; }
  function eligible() {
    if (!player || !player.api) return false;
    var s = previewState(player.card);
    if (s !== 'ok') return false;
    if (player.kind === 'vimeo' && !player.cc.listed) return false;   /* Vimeo: a caption track must be listed first */
    return true;
  }
  /* Whether the page may start this story's preview by itself now (the provider, the gate, Living, no question open,
     no Save-Data). Decided at mount; the postMessage mute is sent before every page-started play as well. */
  function previewPossible(card) {
    return PREVIEW_AUTOPLAY && hasAPI(card.getAttribute('data-provider')) && previewState(card) === 'ok' && previewMode() && !held() && !saveData();
  }
  function holdCurtain(card) { return PREVIEW_AUTOPLAY && hasAPI(card.getAttribute('data-provider')) && previewState(card) === 'hold-note'; }
  function canPreview() {
    return PREVIEW_AUTOPLAY && !frozen && !!player && player.api && !player.error && previewMode() && !held() &&
      !userPaused && !capped && inView && !document.hidden && !saveData() && eligible() && !(curtain && !curtain.hidden && curtain.getAttribute('data-mode') === 'held');
  }
  function lightCanWalk() {
    return !!zf && !!player && !composed() && motion() === 'living' && !held() && !floor() && !lightPaused && onScreen && !document.hidden && !(forced && forced.matches);
  }
  /* In Living the light first finishes one fast descent (four segments, 0.25s each) and the preview starts as it
     lands on the innermost tread, or when the player is ready if that comes later. */
  function maybePreview() {
    if (!canPreview() || !barSeen || moving() || player.state === 'ended') { if (arrival && (!canPreview() || !barSeen)) { arrival = null; lights(); } return; }
    if (lightCanWalk() && !gesture && !player.landed) {
      if (!arrival) {
        var a = arrival = {}, p0 = player;
        /* the shared frame lights the last four segments 0.25 s apart and hands over at 1.0 s */
        zf.arrive(function () {
          if (arrival !== a) return;
          arrival = null; p0.landed = true;
          if (player === p0 && player.ready) startPreview();
          lights();
        });
      }
      return;
    }
    if (player.ready) startPreview();
  }
  function startPreview() {
    if (!canPreview() || !barSeen || moving()) return;
    var a = adapter();
    gesture = false;
    requestSound(true);
    a.play(); pending.play = now();
    autoStarted = true; deliberate = false; pausedFor = '';
    player.previewStart = true;
    armCap(player);
    render();
  }
  /* A page-started preview stops after 45 seconds on desktop or 15 seconds on phone widths. Choosing a poster or
     Next Story remains a muted, capped preview. Actual Play, Sound or native playback controls make playback
     the visitor's own. No bandwidth-saving amount is claimed here. */
  function capSeconds() { return wideQuery && !wideQuery.matches ? 15 : 45; }
  function armCap(p) {
    if (!p) return;
    cancel(p.capTimer);
    if (!(autoStarted && !deliberate)) return;
    var limit = capSeconds();
    p.capTimer = later(function () {
        if (player === p && autoStarted && !deliberate && moving()) {
          capped = true; pausedFor = 'cap'; adapter().stop(); pending.pause = now();
          showCurtain(p.card, 'rested'); render();
        }
      }, limit * 1000);
  }
  function holdPreview(reason) {
    if (!player || !player.api || !player.ready || frozen) return;
    if (moving() && autoStarted && !deliberate) { adapter().pause(); pending.pause = now(); pausedFor = reason; }
  }
  /* The visitor's own Play plays this story (or the full film in place of its trailer) with sound,
     unless the visitor deliberately turned Sound off. */
  function startDeliberate() {
    if (!player || !player.api) return;
    var a = adapter();
    userPaused = false; capped = false; deliberate = true; autoStarted = false; pausedFor = ''; gesture = false; arrival = null;
    if (curtain && !curtain.hidden && curtain.getAttribute('data-mode') !== 'loading') { curtain.hidden = true; if (section) section.removeAttribute('data-curtain'); }
    if (!player.ready) { playOnReady = true; render(); return; }
    /* the visitor's own Play plays with sound, unless they turned Sound off themselves */
    if (player.muted !== false && !soundChosenOff) { requestSound(false); }
    a.play(); pending.play = now();
    render();
  }
  function watchFullFilm() {
    var card = player && player.card;
    if (!card) return;
    userPaused = false; capped = false;
    showCurtain(card, 'loading');
    mount(card, { trailer: false });
    playOnReady = true;
    render();
  }

  function buzz() {}

  /* ---------- what is said: the visible line always shows the state; screen readers hear it after the visitor acts,
     when a story first starts by itself, and when it ends or fails. View and tab pauses are never spoken. ---------- */
  var speakUntil = 0, statusTimer = 0;
  function listen() { speakUntil = now() + 4000; }
  function announce(msg, force) {
    if (!announcer || !msg) return;
    if (!force && now() > speakUntil) return;
    speakUntil = 0;
    announcer.textContent = '';
    later(function () { announcer.textContent = msg; }, 30);
  }

  /* ---------- stage rendering ---------- */
  function setText(id, value) { var n = get(id); if (n) n.textContent = value; return n; }
  function showRow(id, on) { var n = get(id); if (n) n.hidden = !on; }
  function setLabel(btn, label, icon) {
    if (!btn) return;
    var l = btn.querySelector('.th-tlabel'); if (l && l.textContent !== label) l.textContent = label;
    if (icon) btn.setAttribute('data-icon', icon);
  }
  function setState(btn, word) { var n = btn && btn.querySelector('.th-tstate'); if (n && n.textContent !== word) n.textContent = word; }
  function stage(s) {
    if (player) player.state = s;
    if (section) section.setAttribute('data-stage-state', s);
    render();
  }
  function soundWord() {
    if (!player || pending.mute || pending.unmute || player.muted === null) return 'Checking';
    return player.muted ? 'Off' : 'On';
  }
  function ccWord() {
    if (!player) return '';
    var cc = player.cc;
    if (cc.open) return 'In Picture';
    if (cc.none) return 'None Offered';
    /* Off follows a fresh provider report; sending a command alone does not confirm the displayed state. */
    if (!ccWanted) return cc.reported && !cc.active ? 'Off' : 'Checking';
    if (cc.active) return cc.auto ? 'Auto' : 'On';
    return moving() ? 'Checking' : '';
  }
  function ccPhrase() {
    var w = ccWord();
    return w === 'On' ? ' Captions on.' : w === 'Auto' ? ' Automatic captions on.' : w === 'None Offered' ? ' This upload offers no captions.' :
      w === 'In Picture' ? ' Captions are in the picture.' : w === 'Off' ? ' Captions off.' : '';
  }
  function render() {
    var s = (section && section.getAttribute('data-stage-state')) || (player && player.state) || 'ready';
    var kind = player ? player.kind : (selected && selected.getAttribute('data-provider')) || '';
    if (selected && !playerURL(selected)) kind = '';
    var api = !!(player && player.api);
    if (section) section.setAttribute('data-provider', kind || 'none');
    if (lightBtn) { lightBtn.hidden = !kind; lightBtn.setAttribute('aria-disabled', String(!kind || ambientLocked())); }
    [playBtn, soundBtn, ccBtn].forEach(function (b) { if (b) b.hidden = !api; });
    if (nativeNote) {
      nativeNote.hidden = api || !PREVIEW_AUTOPLAY || !kind;   /* source-only: the screen itself says where it plays */
      nativeNote.textContent = !kind ? '' : 'This ' + (NAMES[kind] || 'provider') + ' player uses its own play, sound and caption controls.';
    }
    if (api && playBtn && soundBtn && ccBtn) {
      var playing = moving(), known = player.ready && !player.error, muted = player.muted !== false;
      /* the primary action: Play when the next action is Play; for a full film showing its trailer, Watch Full Film */
      var label = player.trailer ? 'Watch Full Film' : playing ? 'Pause' : 'Play';
      setLabel(playBtn, label, player.trailer ? 'film' : playing ? 'pause' : 'play');
      playBtn.setAttribute('data-next', player.trailer || !playing ? 'play' : 'pause');
      playBtn.setAttribute('aria-disabled', String(!!player.error));
      soundBtn.setAttribute('data-icon', muted ? 'muted' : 'sound');
      soundBtn.setAttribute('aria-pressed', String(!muted));
      setState(soundBtn, soundWord());
      soundBtn.setAttribute('aria-disabled', String(!known));
      var invite = playing && muted && !soundChosenOff;
      if (invite) { soundBtn.setAttribute('data-invite', ''); playBtn.setAttribute('data-next', player.trailer ? 'quiet' : 'pause'); }
      else soundBtn.removeAttribute('data-invite');
      var w = ccWord(), fixed = w === 'None Offered' || w === 'In Picture';
      var pressed = !fixed && player.cc.reported && player.cc.active;
      ccBtn.setAttribute('data-icon', pressed ? 'cc-on' : 'cc');
      ccBtn.setAttribute('aria-pressed', String(pressed));
      setState(ccBtn, w);
      ccBtn.title = w === 'None Offered' ? 'The provider lists no captions for this video.' : w === 'In Picture' ? 'Words are shown in the picture itself.' : '';
      ccBtn.setAttribute('aria-disabled', String(!known || fixed));
    }
    if (curtainPlay) curtainPlay.textContent = 'Play';
    scheduleStatus(s, kind);
    lights();
    updateDock();
  }
  function statusText(s, kind) {
    kind = kind === undefined ? (player ? player.kind : '') : kind;
    var name = NAMES[kind] || 'the provider', note = selected ? record(selected).note : '';
    if (!kind) return (selected ? record(selected).availability + ' ' : '') + 'Open the official source to continue.';   /* the contract: the record's own availability */
    if (s === 'loading') return player && player.slow ? 'Still connecting to ' + name + '. If the player does not load, open the official source.' : 'Connecting to ' + name + '.';
    if (s === 'unavailable') return 'This video cannot play in this player. Open its official source.';
    if (!player || !player.api) return 'Ready. Use Play in the player, or open the official source. Viewing restrictions can vary.';
    if (s === 'playing' || s === 'buffering') {
      /* on phones the Before Watching note already sits directly under the screen, so the status does not repeat it */
      if (note && now() < advisoryUntil && !(wideQuery && !wideQuery.matches)) return 'Before watching: ' + note;
      return playingText();
    }
    if (curtain && !curtain.hidden && curtain.getAttribute('data-mode') === 'held') return 'This story has a Before Watching note. Press Play when you are ready.';
    if (s === 'paused') return pausedFor === 'cap' ? 'Preview paused. Press Play to keep watching.' :
      pausedFor === 'captions' ? 'This upload offers no captions in the player, so the preview stopped. Press Play to watch.' : userPaused ? 'Paused. Previews stay paused until you press Play.' :
      pausedFor === 'tab' ? 'Paused while this tab is hidden.' : pausedFor === 'view' ? 'Paused while the screen is out of view.' : 'Paused. Press Play to continue.';
    if (s === 'ended') return 'Finished. Press Play to watch again, or choose another story.';
    if (pausedFor === 'cap') return 'Preview paused. Press Play to keep watching.';
    if (held()) return 'Ready. Choose a motion setting above; the preview waits for your answer.';
    if (motion() === 'still') return 'Still: nothing moves. Press Play to watch.';
    if (userPaused) return 'Ready. Previews stay paused until you press Play.';
    if (saveData()) return 'Ready. Previews are off to save data. Press Play to watch.';
    var why = previewState(player.card);
    if (why === 'hold-audio') return 'Ready. This program is audio-led; press Play to listen.';
    if (why === 'hold-captions') return 'Ready. Caption availability is not verified for this preview; press Play to watch.';
    if (why === 'hold-full') return 'Ready. Full films start when you press Play.';
    if (player.kind === 'vimeo' && !player.cc.listed) return player.cc.none ? 'Ready. Caption availability is not verified for this preview; press Play to watch.' : 'Ready. Press Play to watch.';
    return player.trailer ? 'Ready. The trailer preview starts without sound when the screen and its controls are in view.' : 'Ready. The preview starts without sound when the screen and its controls are in view.';
  }
  function playingText() {
    return (player && player.trailer ? 'Trailer preview, playing' : 'Playing') + (soundWord() === 'Checking' ? '. Sound state checking.' : player.muted ? ' without sound.' : ' with sound.') + ccPhrase();
  }
  /* The visible line settles for 300 ms before it changes, so an automatic pause and resume never flashes. Screen
     readers hear the new line only when the visitor has just acted (listen()); view and tab changes stay silent. */
  var statusPending = null;
  function scheduleStatus(s, kind) {
    if (!statusLine) return;
    var msg = statusText(s, kind);
    if (msg === statusPending) return;            /* already waiting to show this line: providers report many times a second */
    cancel(statusTimer); statusPending = null;
    if (msg === statusLine.textContent) return;
    var apply = function () {
      statusPending = null;
      if (statusLine.textContent !== msg) { statusLine.textContent = msg; announce(msg); }
      if (/^Before watching: /.test(msg)) statusLine.setAttribute('data-advisory', ''); else statusLine.removeAttribute('data-advisory');
    };
    if (!statusLine.textContent || s === 'loading' || s === 'source-only') apply(); else { statusPending = msg; statusTimer = later(apply, 300); }
  }

  function cloneList(from, to) {
    if (!to) return;
    while (to.firstChild) to.removeChild(to.firstChild);
    if (from) Array.prototype.forEach.call(from.children, function (n) { to.appendChild(n.cloneNode(true)); });
  }
  function safeHref(raw) {
    try {
      var u = new URL(raw);
      if (u.protocol !== 'https:' || u.username || u.password || u.port === '0' || /^https:\/\/[^/?#]*:(?:[/?#]|$)/.test(raw) || /[\\\s]/.test(raw)) throw new Error('Invalid destination');
      return u.href;
    } catch (_) { return '/theater'; }
  }
  function posterImage(card) {
    var img = card.querySelector('.th-poster-button img');
    return img ? { now: img.complete && img.currentSrc ? img.currentSrc : '', src: img.getAttribute('src') || '', srcset: img.getAttribute('srcset') || '' } : null;
  }
  /* The curtain: the story's own provider preview image while its player connects; with a plain note when the story
     plays on its official page or the provider reports an error; with the Before Watching note above a Play button
     for a held story; or after a preview has rested. It is the real thumbnail, never a frame. */
  var connectTimer = 0;
  function showCurtain(card, mode) {
    if (!curtain) return;
    var im = posterImage(card);
    var use = !!im && (!!im.now || mode !== 'loading');
    if (curtainImg) {
      curtainImg.removeAttribute('srcset');
      if (use && im.now) curtainImg.src = im.now;
      else if (use) { curtainImg.sizes = '(max-width: 719px) 100vw, 62vw'; if (im.srcset) curtainImg.srcset = im.srcset; curtainImg.src = im.src; }
      else curtainImg.removeAttribute('src');
      curtainImg.hidden = !use;
    }
    curtain.setAttribute('data-mode', mode);
    if (section) section.setAttribute('data-curtain', mode);
    if (curtainText) curtainText.textContent = mode === 'source-only' ? 'This story plays on its official page.' :
      mode === 'unavailable' ? 'This video cannot play in this player. The publisher may limit where or how it plays.' :
      mode === 'held' ? 'Before watching: ' + record(card).note : '';
    if (curtainSource) curtainSource.href = safeHref(card.getAttribute('data-watch-url') || '');
    cancel(connectTimer);
    if (mode === 'loading') { curtain.setAttribute('data-connect', 'run'); connectTimer = later(function () { if (curtain) curtain.setAttribute('data-connect', 'done'); }, 5000); }
    curtain.hidden = false;
  }
  function hideCurtain(always) {
    if (!curtain) return;
    var m = curtain.getAttribute('data-mode');
    if (m === 'loading' || (always && m === 'rested')) curtain.hidden = true;
    if (curtain.hidden && section) section.removeAttribute('data-curtain');
  }

  function setTitle(card, r) {
    if (!titleEl) return;
    var src = card.querySelector('.th-film-title');
    if (src && src.childNodes && titleEl.replaceChildren) {
      titleEl.replaceChildren.apply(titleEl, Array.prototype.map.call(src.childNodes, function (n) { return n.cloneNode(true); }));
      var lang = src.getAttribute('lang');
      if (lang) titleEl.setAttribute('lang', lang); else titleEl.removeAttribute('lang');
    } else titleEl.textContent = r.title;
  }
  function select(card, opts) {
    opts = opts || {};
    var r = record(card), changed = selected !== card;
    selected = card;
    setTitle(card, r);
    if (section) section.setAttribute('aria-label', 'Screening room: ' + r.title);
    setText('theaterKind', r.kind);
    setText('theaterForm', r.form); showRow('theaterForm', !!r.form);
    setText('theaterCredits', r.credits);
    setText('theaterPerspective', r.perspective); showRow('theaterPerspectiveRow', !!r.perspective);
    setText('theaterPublisher', r.publisher);
    setText('theaterYear', r.year); showRow('theaterYearRow', !!r.year);
    setText('theaterRuntime', r.runtime); showRow('theaterRuntimeRow', !!r.runtime);
    setText('theaterLocation', r.place); showRow('theaterPlaceRow', !!r.place);
    setText('theaterDescription', r.summary);
    setText('theaterAvailability', r.availability);
    setText('theaterContentNote', r.note);
    var watch = get('theaterWatch'); if (watch) watch.href = safeHref(card.getAttribute('data-watch-url') || '');
    if (permalink) permalink.href = '/theater#film-' + r.id;
    cloneList(card.querySelector('.th-source-list'), get('theaterSources'));
    var credit = card.querySelector('.th-thumbnail-credit'), creditBox = get('theaterThumbCredit');
    if (creditBox) { while (creditBox.firstChild) creditBox.removeChild(creditBox.firstChild); if (credit) creditBox.appendChild(credit.cloneNode(true)); }
    posters.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-theater-select') === r.id)); });
    cards.forEach(function (c) { if (c.classList) c.classList.toggle('is-selected', c === card); });
    var wayUp = document.querySelector('.th-linked-watch');   /* the story link's way up belongs to its own story only */
    if (wayUp && wayUp.parentNode && !card.contains(wayUp)) wayUp.parentNode.removeChild(wayUp);
    if (changed || opts.initial) {
      gesture = !!opts.gesture; capped = false; advisoryUntil = 0;
      if (playerURL(card)) {
        /* a full film's page-started preview is its trailer (Living only); a held story waits behind its note */
        var trailer = PREVIEW_AUTOPLAY && !!card.getAttribute('data-trailer-id') && previewState(card) === 'ok' && previewMode() && !held() && !saveData();
        if (holdCurtain(card)) { mount(card, { trailer: false }); showCurtain(card, 'held'); }
        else { showCurtain(card, 'loading'); mount(card, { trailer: trailer }); }
      }
      else { stop(); showCurtain(card, 'source-only'); stage('source-only'); }
    }
    updateRail();
    if (opts.focus) {
      var frame = player && player.frame;
      if (PREVIEW_AUTOPLAY && titleEl) {
        /* With previews on, a chosen story focuses its title; the screening controls follow it in reading order, before
           the provider's own frame. Next Story keeps focus on itself. */
        if (opts.keepFocus) return;
        titleEl.focus({ preventScroll: true }); titleEl.scrollIntoView({ block: 'start', behavior: 'instant' });
      } else if (frame) { frame.focus({ preventScroll: true }); frame.scrollIntoView({ block: 'center', behavior: 'instant' }); }
      else if (titleEl) { titleEl.focus({ preventScroll: true }); titleEl.scrollIntoView({ block: 'start', behavior: 'instant' }); }
    }
  }

  /* ---------- view transitions: Living morphs the poster into the screen; Calm cross-fades; Still is instant ---------- */
  function transition(from, toFn, update) {
    var m = motion();
    if (!document.startViewTransition || m === 'still' || held() || floor()) { update(); return; }
    var named = [];
    function name(n) { if (n && n.style && m === 'living') { n.style.viewTransitionName = 'th-hero'; named.push(n); } }
    name(from);
    d.setAttribute('data-vt', m);
    var vt;
    try {
      vt = document.startViewTransition(function () {
        named.forEach(function (n) { n.style.viewTransitionName = ''; });
        named = [];
        var waitFor = update();
        name(toFn && toFn());
        return waitFor && waitFor.then ? Promise.race([waitFor, new Promise(function (r) { setTimeout(r, 250); })]) : undefined;
      });
    } catch (e) { named.forEach(function (n) { n.style.viewTransitionName = ''; }); d.removeAttribute('data-vt'); update(); return; }
    var done = function () { named.forEach(function (n) { n.style.viewTransitionName = ''; }); d.removeAttribute('data-vt'); };
    vt.finished.then(done, done);
  }
  function choose(card, poster) {
    originCard = card;
    buzz(); listen();
    var img = poster && poster.querySelector('img');
    transition(img, function () { return curtain && !curtain.hidden ? curtainImg : screenEl; }, function () {
      select(card, { focus: true, gesture: true });
      announceNow();
      return curtainImg && curtain && !curtain.hidden && curtainImg.decode ? curtainImg.decode().catch(function () {}) : null;
    });
  }
  function announceNow() {
    if (!selected || !PREVIEW_AUTOPLAY) return;
    var r = record(selected);
    announce('Now on screen: ' + r.title + ', ' + r.kind + (r.runtime ? ', ' + r.runtime : '') + '.' +
      (holdCurtain(selected) ? ' This story has a Before Watching note.' : ''), true);
  }
  function shown(card) { return card && !card.hidden && matched.indexOf(card) !== -1; }
  function returnToCollection() {
    var card = shown(selected) ? selected : null;
    var poster = card && posterFor(card);
    transition(screenEl, function () { return poster && poster.querySelector('img'); }, function () {
      if (poster) { card.scrollIntoView({ block: 'center', behavior: 'instant' }); poster.focus({ preventScroll: true }); }
      else { var h = get('collection-heading'); if (h) { h.scrollIntoView({ block: 'start', behavior: 'instant' }); h.focus({ preventScroll: true }); } }
    });
  }

  /* ---------- next in this selection: the next eight matched stories as real posters ---------- */
  var railKey = '';
  function updateRail() {
    if (!railList || !document.createElement) return;
    var list = [], start = matched.indexOf(selected);
    for (var k = 1; k <= matched.length && list.length < RAIL; k++) {
      var c = matched[(start + k + matched.length) % matched.length];
      if (c && c !== selected && list.indexOf(c) === -1) list.push(c);
    }
    var key = list.map(function (c) { return c.getAttribute('data-theater-film'); }).join(' ');
    if (key === railKey) return;
    railKey = key;
    while (railList.firstChild) railList.removeChild(railList.firstChild);
    list.forEach(function (c) {
      var r = record(c), li = document.createElement('li'), b = document.createElement('button');
      b.type = 'button'; b.className = 'th-upnext-item'; b.setAttribute('data-upnext', r.id);
      var thumb = document.createElement('span'); thumb.className = 'th-upnext-thumb';
      var pb = posterFor(c), src = pb && pb.querySelector('img');
      if (pb) { var cr = pb.getAttribute('data-crop'); if (cr) { thumb.setAttribute('data-crop', cr); thumb.setAttribute('style', pb.getAttribute('style') || ''); } }
      if (src) {
        var im = document.createElement('img');
        im.alt = ''; im.loading = 'lazy'; im.decoding = 'async'; im.referrerPolicy = 'no-referrer'; im.width = 320; im.height = 180;
        if (src.getAttribute('srcset')) { im.setAttribute('srcset', src.getAttribute('srcset')); im.setAttribute('sizes', '(max-width: 719px) 168px, 200px'); }
        im.src = src.getAttribute('src');
        thumb.appendChild(im);
      }
      var t = document.createElement('span'); t.className = 'th-upnext-title';
      var h = c.querySelector('.th-film-title');
      if (h) { Array.prototype.forEach.call(h.childNodes, function (n) { t.appendChild(n.cloneNode(true)); }); if (h.getAttribute('lang')) t.setAttribute('lang', h.getAttribute('lang')); }
      else t.textContent = r.title;
      var meta = document.createElement('span'); meta.className = 'th-upnext-meta';
      meta.textContent = r.kind + (r.runtime ? ' · ' + r.runtime.replace(/\s*·.*$/, '') : '');
      b.appendChild(thumb); b.appendChild(t); b.appendChild(meta);
      b.addEventListener('click', function () { choose(c, posterFor(c)); });
      li.appendChild(b); railList.appendChild(li);
    });
  }

  /* ---------- collection: search, filters, paging ---------- */
  function showMatches(reveal) {
    cards.forEach(function (card) { var i = matched.indexOf(card); card.hidden = i === -1 || i >= limit; });
    get('theaterEmpty').hidden = matched.length !== 0;
    var shownCount = Math.min(limit, matched.length);
    get('theaterStatus').textContent = shownCount < matched.length ? 'Showing ' + shownCount + ' of ' + matched.length + ' stories.' : matched.length + (matched.length === 1 ? ' title' : ' titles') + ' in this selection.';
    if (more) { more.hidden = shownCount >= matched.length; more.textContent = 'Show ' + Math.min(STEP, matched.length - shownCount) + ' More Stories'; }
    if (progress) { progress.hidden = !matched.length; var bar = progress.firstElementChild; if (bar) bar.style.inlineSize = (matched.length ? Math.round(shownCount / matched.length * 1000) / 10 : 0) + '%'; }
    if (next) next.disabled = matched.length < 2;
    if (reveal) reveal.forEach(function (c) { if (!c.classList) return; c.classList.remove('th-revealed'); void c.offsetWidth; c.classList.add('th-revealed'); });
  }
  function filter() {
    var words = fold(search.value.trim()).split(/\s+/).filter(Boolean);
    matched = cards.filter(function (card) {
      var h = words.length ? hayOf(card) : '';
      return words.every(function (w) { return h.indexOf(w) !== -1; }) &&
        (topic.value === 'all' || attr(card, 'data-topic').split(/\s+/).indexOf(topic.value) !== -1) &&
        (!region || region.value === 'all' || (card.getAttribute('data-region') || 'unindexed') === region.value) &&
        (!viewing || viewing.value === 'all' || card.getAttribute('data-viewing') === viewing.value) &&
        (!access || access.value === 'all' || (access.value === 'watch-here' && Boolean(playerURL(card))) ||
          (access.value === 'official-site' && !playerURL(card)));
    });
    limit = more ? STEP : Infinity;
    showMatches();
    countFilters();
    updateRail();
  }
  /* Phones fold the four selects behind one Filters button; the count says how many are set. */
  function countFilters() {
    if (!filterCount) return;
    var n = [topic, region, viewing, access].filter(function (s) { return s && s.value !== 'all'; }).length;
    filterCount.textContent = n ? String(n) : '';
    filterCount.hidden = !n;
    if (filtersToggle) filtersToggle.setAttribute('aria-label', n ? 'Filters, ' + n + ' set' : 'Filters');
  }
  if (filtersToggle && filterPanel) filtersToggle.addEventListener('click', function () {
    var open = filtersToggle.getAttribute('aria-expanded') !== 'true';
    filtersToggle.setAttribute('aria-expanded', String(open));
    if (filterPanel.classList) filterPanel.classList.toggle('is-open', open);
  });
  search.addEventListener('input', filter); topic.addEventListener('change', filter);
  if (region) region.addEventListener('change', filter);
  if (viewing) viewing.addEventListener('change', filter);
  if (access) access.addEventListener('change', filter);
  if (more) more.addEventListener('click', function () {
    var firstNew = matched[limit], start = limit;
    limit += STEP; showMatches(matched.slice(start, limit));
    var poster = firstNew && posterFor(firstNew);
    if (poster) { poster.focus({ preventScroll: true }); poster.scrollIntoView({ block: 'nearest', behavior: 'instant' }); }
  });
  if (next) next.addEventListener('click', function () {
    if (!matched.length) return;
    var i = (matched.indexOf(selected) + 1) % matched.length;
    if (more && i >= limit) { limit = Math.ceil((i + 1) / STEP) * STEP; showMatches(); }
    buzz(); listen();
    originCard = matched[i];
    transition(null, null, function () { select(matched[i], { focus: true, keepFocus: true, gesture: true }); announceNow(); });
  });
  get('theaterClear').addEventListener('click', function () {
    search.value = ''; topic.value = 'all'; if (region) region.value = 'all'; if (viewing) viewing.value = 'all'; if (access) access.value = 'all';
    filter(); search.focus();
  });
  posters.forEach(function (button) {
    button.setAttribute('role', 'button');
    button.addEventListener('keydown', function (event) { if (event.key === ' ' && button.tagName === 'A') { event.preventDefault(); button.click(); } });
    button.addEventListener('click', function (event) {
      if (button.tagName === 'A' && event && (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || (event.button != null && event.button !== 0))) return;
      if (event && event.preventDefault) event.preventDefault();
      var card = cardFor(button.getAttribute('data-theater-select'));
      if (card) choose(card, button);
    });
  });
  if (backLink) backLink.addEventListener('click', function (e) {
    if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || (e.button != null && e.button !== 0)) return;
    e.preventDefault(); returnToCollection();
  });

  /* ---------- story links: #film-<id> lands on its card. The fragment resolves
     before any player mounts; the browser's own fragment scroll does the landing, never the script. ---------- */
  function linkedCard() {
    var match = /^#film-([a-z][a-z0-9-]{0,99})$/.exec((window.location && window.location.hash) || '');
    return match ? cardFor(match[1]) : null;
  }
  function revealLinked(card) {
    var i = matched.indexOf(card);
    if (more && i >= limit) { limit = Math.ceil((i + 1) / STEP) * STEP; showMatches(); }
  }
  /* A card story link lands on its card. The card then offers one plain way up to the screen where the story is
     already selected. */
  function markLinked(card) {
    if (!card || !card.insertBefore || !card.querySelector) return;
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'th-btn th-btn-solid th-linked-watch';
    b.textContent = playerURL(card) ? 'Watch In The Screening Room' : 'Show In The Screening Room';
    b.addEventListener('click', function () { if (b.parentNode) b.parentNode.removeChild(b); choose(card, posterFor(card)); });
    card.insertBefore(b, card.querySelector('.th-film-title'));
  }
  window.addEventListener('hashchange', function () {
    var card = linkedCard();
    if (!card) return;
    revealLinked(card);
    originCard = card;
    if (card === selected) select(card, { focus: true });
    else transition(null, null, function () { select(card, { focus: true }); });
  });

  /* ---------- transport ---------- */
  function disabled(b) { return !b || b.getAttribute('aria-disabled') === 'true'; }
  function togglePlay() {
    if (!player || !player.api) return;
    buzz(); listen();
    if (player.trailer) { watchFullFilm(); return; }
    var a = adapter();
    if (moving()) { userPaused = true; deliberate = false; autoStarted = false; pausedFor = 'visitor'; a.pause(); pending.pause = now(); render(); }
    else startDeliberate();
  }
  function toggleSound() {
    if (!player || !player.api) return;
    var a = adapter();
    buzz(); listen();
    if (player.muted !== false) { deliberate = true; autoStarted = false; soundWanted = true; soundChosenOff = false; requestSound(false); }
    else { requestSound(true); soundWanted = false; soundChosenOff = true; }
    render();
  }
  if (playBtn) playBtn.addEventListener('click', function () { if (!disabled(playBtn)) togglePlay(); });
  if (curtainPlay) curtainPlay.addEventListener('click', function () { buzz(); listen(); if (curtain) curtain.hidden = true; if (section) section.removeAttribute('data-curtain'); startDeliberate(); });
  if (soundBtn) soundBtn.addEventListener('click', function () { if (!disabled(soundBtn)) toggleSound(); });
  if (ccBtn) ccBtn.addEventListener('click', function () {
    if (disabled(ccBtn) || !player || !player.api) return;
    buzz(); listen();
    ccWanted = !ccWanted;
    armCap(player);
    if (!ccWanted) { player.cc.offAt = now(); later(render, 2600); }
    player.cc.onSent = ccWanted; player.cc.offSent = !ccWanted;
    adapter().captions(ccWanted);
    render();
  });

  /* ---------- now playing: docked controls when the visitor's own playback scrolls out of view ---------- */
  var dockShown = false, dockSaid = false, dockPausedAt = 0;
  function updateDock() {
    if (!dock || !PREVIEW_AUTOPLAY) return;
    var playingOwn = !!player && player.api && (deliberate || player.muted === false);
    var t = now();
    if (player && player.state === 'paused' && dockShown) { if (!dockPausedAt) { dockPausedAt = t; later(updateDock, 10050); } }
    else dockPausedAt = 0;
    var want = dockShown ? (ratio < 0.6 && !!player && player.api && (moving() || (player.state === 'paused' && t - dockPausedAt < 10000)))
                         : (ratio < 0.15 && moving() && playingOwn);
    if (want !== dockShown) {
      dockShown = want;
      dock.hidden = !want;
      if (want) {
        var r = record(player.card), img = get('theaterDockImg'), pb = posterFor(player.card), src = pb && pb.querySelector('img'), th = get('theaterDockThumb');
        setText('theaterDockTitle', r.title);
        if (th && pb) { var cr = pb.getAttribute('data-crop'); if (cr) { th.setAttribute('data-crop', cr); th.setAttribute('style', pb.getAttribute('style') || ''); } else { th.removeAttribute('data-crop'); th.removeAttribute('style'); } }
        /* a small provider thumbnail for the dock */
        if (img && src) { var small = (src.getAttribute('srcset') || '').split(',')[0].trim().split(/\s+/)[0]; img.removeAttribute('srcset'); img.src = small || src.currentSrc || src.getAttribute('src'); }
        if (!dockSaid) { dockSaid = true; announce('Now playing: ' + r.title + '. Its controls are docked at the bottom of the window.', true); }
      }
    }
    if (dockShown && player) {
      var dp = get('theaterDockPlay'), ds = get('theaterDockSound'), m = player.muted !== false;
      setLabel(dp, moving() ? 'Pause' : 'Play', moving() ? 'pause' : 'play');
      if (ds) { ds.setAttribute('data-icon', m ? 'muted' : 'sound'); ds.setAttribute('aria-pressed', String(!m)); setState(ds, soundWord()); }
    }
  }
  if (dock) {
    var dp = get('theaterDockPlay'), ds = get('theaterDockSound'), db = get('theaterDockBack');
    if (dp) dp.addEventListener('click', togglePlay);
    if (ds) ds.addEventListener('click', toggleSound);
    if (db) db.addEventListener('click', function () {
      if (shell) shell.scrollIntoView({ block: 'center', behavior: 'instant' });
      var f = player && player.frame; if (f) f.focus({ preventScroll: true });
    });
  }

  /* ---------- the stepped light frame ----------
     The reusable ZOTHEOS frame component (ZtFrame, zt-frame.js): three nested brackets
     after the mark, 18px apart on every side (12px on phones), the outer bracket on the stage edge; their top arms stop
     short of the centre in terraces (risers 18px, treads 44px; 12 and 26 on phones), so a stepped aisle opens above
     the screen, and the bottom stays closed. It draws whole device pixels at any display scale. This page decides its
     state: walk (Living, nothing playing), arrive (a preview is about to start), playing (house lights), paused (the
     visitor's Pause Light) or rest (Calm, Still, a pending motion question, out of view, a hidden tab, and for two
     seconds after a pause or an ending). */
  var lightPaused = false, forced = media('(forced-colors: active)');
  var GEOMETRY = { wide: { ox: [10, 28, 46], oy: [10, 28, 46], a: [36, 80, 124] }, phone: { ox: [0, 0, 0], oy: [11, 23, 35], a: [18, 44, 70] } };

  function composed() { return false; }
  /* Made in the first animation frame, so its first measurement shares the layout the first paint needs anyway
     instead of forcing one while the page is still being set up. */
  var zf = null;
  function makeFrame() {
    try {
      if (window.ZtFrame && shell && screenEl && document.createElementNS)
        zf = new window.ZtFrame(shell, screenEl, { geometry: wideQuery && !wideQuery.matches ? GEOMETRY.phone : GEOMETRY.wide, state: 'rest', phoneQuery: '(max-width: 719px)', ticker: true });
    } catch (e) { zf = null; }
    lights(); maybePreview();
  }
  function lightMode() {
    if (!zf) return 'rest';
    if (arrival) return 'arrive';
    if (moving()) return 'playing';   /* provider-reported playback only */
    if (now() < restUntil) return 'rest';
    if (lightPaused && !ambientLocked()) return 'paused';
    return lightCanWalk() ? 'walk' : 'rest';
  }
  function filmMoving() { return moving(); }
  function lights() {
    var locked = ambientLocked(), mode = lightMode();
    d.setAttribute('data-theater-motion', locked || lightPaused ? 'still' : 'ambient');
    if (lightBtn) {
      lightBtn.setAttribute('aria-disabled', String(!player || locked));
      lightBtn.setAttribute('aria-pressed', String(locked || lightPaused));
      setState(lightBtn, locked ? 'At Rest' : lightPaused ? 'Paused' : mode === 'walk' || mode === 'arrive' ? 'Moving' : 'Resting');
      lightBtn.setAttribute('data-icon', locked || lightPaused ? 'light-off' : 'light');
      lightBtn.title = locked ? 'Calm, Still or a pending motion choice keeps the ambient light at rest.' : 'Pause or play the ambient light around the screen.';
    }
    if (zf) {
      zf.motionOk(false);
      if (mode !== 'arrive' && zf.state !== mode) zf.set(mode);   /* the arrival runs on its own timer until it lands */
    }
  }
  if (lightBtn) lightBtn.addEventListener('click', function () {
    if (disabled(lightBtn)) return;
    listen();
    lightPaused = !lightPaused;
    if (lightPaused && arrival) { arrival = null; if (zf) zf.set('paused'); }
    lights(); maybePreview();
  });

  /* ---------- motion and theme changes (the Appearance script owns the saved choices) ---------- */
  function onMotion() {
    if (!previewMode() || held() || floor()) { holdPreview('motion'); arrival = null; } else maybePreview();
    render();
  }
  new MutationObserver(onMotion).observe(d, { attributes: true, attributeFilter: ['data-motion', 'data-motion-ask'] });
  new MutationObserver(function () { lights(); }).observe(d, { attributes: true, attributeFilter: ['data-theme'] });
  if (reducedQuery) { if (reducedQuery.addEventListener) reducedQuery.addEventListener('change', onMotion); else if (reducedQuery.addListener) reducedQuery.addListener(onMotion); }
  if (forced && forced.addEventListener) forced.addEventListener('change', function () { lights(); });

  /* ---------- in-view and visibility: 60% of the picture the visitor can actually see, below the sticky header ---------- */
  /* the row that matters is the first one: Play, Sound and Captions (one row at every width); Next Story and Pause
     Light may sit on a second row on phones */
  var io = null, barIo = null, transportEl = get('theaterTransport');
  function headerHeight() { return wideQuery && !wideQuery.matches ? 64 : 72; }
  function observe() {
    if (!('IntersectionObserver' in window) || !screenEl) { inView = false; barSeen = false; return; }
    if (io) io.disconnect();
    if (barIo) barIo.disconnect();
    /* the Play, Sound and Captions row counts as seen only when all of it is clear of the sticky header and the
       window's foot */
    if (transportEl) {
      barIo = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { barSeen = en.isIntersecting && en.intersectionRatio >= 0.999; });
        if (barSeen && inView) maybePreview(); else holdPreview('controls');
      }, { threshold: [0, 0.999, 1], rootMargin: '-' + headerHeight() + 'px 0px 0px 0px' });
      barIo.observe(transportEl);
    } else barSeen = false;
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { ratio = en.isIntersecting ? en.intersectionRatio : 0; inView = ratio >= 0.6; onScreen = en.isIntersecting; });
      if (inView) maybePreview(); else holdPreview('view');
      lights(); updateDock();
    }, { threshold: [0, 0.15, 0.6, 1], rootMargin: '-' + headerHeight() + 'px 0px 0px 0px' });
    io.observe(screenEl);
  }
  observe();
  if (wideQuery && wideQuery.addEventListener) wideQuery.addEventListener('change', function () {
    observe();
    if (zf) { zf.geometry = wideQuery.matches ? GEOMETRY.wide : GEOMETRY.phone; zf.key = ''; zf.draw(); }
    lights();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) holdPreview('tab'); else maybePreview();
    lights();
  });
  /* ---------- start: resolve an incoming story link first, then mount exactly one player ---------- */
  filter();
  var linked = linkedCard();
  select(linked || cards.filter(function (c) { return c.getAttribute('data-featured') === 'true'; })[0] || cards[0], { initial: true });
  if (linked) { revealLinked(linked); markLinked(linked); }
  if (get('theaterTools')) get('theaterTools').hidden = false;
  if (next) next.hidden = false;
  if (lightBtn) lightBtn.hidden = !player;
  d.setAttribute('data-theater-ready', '');
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(makeFrame); else makeFrame();
  render();
}());

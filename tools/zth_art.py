"""ZOTHEOS original art for the website (Living Gallery, Batch 1). Markup only; every shape is drawn by flat CSS borders
in theme tokens: the Nations stylesheet (tools/nations/partials/nations.css) for the guide and the brief sheets, and the
doors block in index.html (written by tools/landing_doors.py) for the homepage.

Rules this module keeps, and the tests check:
- Text stays in HTML. No image, no script, no text inside any svg, and no svg at all on Paths To Action (its injection
  guard forbids svg and img). The one svg here is the homepage data bar: a filled rectangle with whole numbers.
- Every art element carries data-origin="zotheos-original" and one variant class, zth-plain or zth-steps.
- Nothing can take focus, nothing is a form control or looks like one, and nothing depicts a person, place, object,
  design or ceremony of any culture. Art is a diagram beside the text it explains, never decoration.
- Every number an art element shows is computed by the build from the site's own loaders, never typed.

ART_STEPS is the Roots switch. False, the plain variant, is what ships. True, the stepped variant (ZOTHEOS's own
one-sided stair geometry, not the traditional xicalcoliuhqui step-fret), waits for the owner's Roots decision about the
footer that names the stepped fret; until then no stepped CSS ships either, and a test fails if the switch is flipped
without it. A page that draws stepped geometry carries CREDIT once.
"""
from html import escape

ART_STEPS = False

ORIGIN = 'zotheos-original'
CREDIT = 'Original project geometry by ZOTHEOS. It has no traditional or ceremonial meaning.'
# The label over a plate's privacy rule (pathway 06). 'Kept Out' repeated the phrase it introduced.
PRIVACY_LABEL = 'Privacy Rule'
CLIMB_STEPS = 4


def stepped(steps=None):
    """The variant in force: the module switch, unless a caller (a test or a preview) passes one explicitly."""
    return ART_STEPS if steps is None else bool(steps)


def variant(steps=None):
    """The class every art element carries."""
    return 'zth-steps' if stepped(steps) else 'zth-plain'


def _open(tag, cls, steps=None, extra=''):
    return '<' + tag + ' class="' + cls + ' ' + variant(steps) + '" data-origin="' + ORIGIN + '"' + extra + '>'


def credit(steps=None, cls='zth-credit'):
    """The once-per-page credit line. Empty in the plain variant, which draws no stepped geometry."""
    if not stepped(steps):
        return ''
    return '<p class="' + escape(cls, quote=True) + '">' + escape(CREDIT) + '</p>'


def _method(method):
    method = list(method)
    if len(method) != CLIMB_STEPS or len(set(method)) != CLIMB_STEPS or not all(isinstance(m, str) and m.strip() for m in method):
        raise ValueError('zth_art: the Climb draws exactly four distinct steps')
    return method


# ---------------------------------------------------------------------------------------------------- piece 1: guide
def climb(method, label, caption, steps=None):
    """The guide's own four-step method, drawn as four columns over its labels (the ordered list's own text).

    Plain: a 2 px rule over steps 01 to 03; over 04 only a short tick at each end of its column, a slot marked and left
    open (a missing line would read as a progress bar three quarters full). The rules and ticks are empty
    pseudo-elements, so nothing is read twice. In the stepped variant the caption carries the credit line.
    """
    items = ''.join('<li>' + escape(step) + '</li>' for step in _method(method))
    note = ' <span class="zth-credit">' + escape(CREDIT) + '</span>' if stepped(steps) else ''
    return (_open('figure', 'pw-climb', steps) + '<ol class="pw-route" aria-label="' + escape(label, quote=True) + '">'
            + items + '</ol><figcaption>' + escape(caption) + note + '</figcaption></figure>')


def lane_mark(scope, steps=None):
    """A 12 by 12 px mark whose shape names a step's lane; the lane class around it picks the shape. Website Now: a
    filled square. Work You Control: a 2 px L, a sheet's edge and its writing line. Proposed App Workflow: four corner
    ticks with open sides, a frame not yet built (the one empty inner element carries two of the ticks). None is a
    closed outline, so no mark can read as a checkbox state. The mark is empty (no text, no role), so assistive
    technology passes over it without an aria-hidden attribute; every step says its lane in words."""
    return _open('span', 'pw-lane', steps) + ('<i></i>' if scope == 'future-app' else '') + '</span>'


def here(position, total, steps=None):
    """One equal square per public chapter, the current one filled. Equal on purpose: no pathway ranks above another.
    Empty like the lane marks; the eyebrow says 'Pathway 03 of 10' in words."""
    if type(position) is not int or type(total) is not int or not 1 <= position <= total:
        raise ValueError('zth_art: chapter position out of range')
    marks = ''.join('<i class="on"></i>' if i == position else '<i></i>' for i in range(1, total + 1))
    return _open('span', 'pw-here', steps) + marks + '</span>'


# ----------------------------------------------------------------------------------------- piece 2: the shared plate
def whole(words):
    """Plate words with each hyphenated compound kept on one line ('land-and-water', 'decision-maker'), so a narrow
    screen breaks between words, never inside a compound (nations_pathways caps a compound at 28 letters)."""
    return ' '.join('<span class="pw-plate-nw">' + escape(w) + '</span>' if '-' in w else escape(w) for w in words.split(' '))


def plate(value, steps=None):
    """Something You Can Prepare, drawn as a sheet a person could picture holding: its name and its parts, in the
    deliverable's own words (nations_pathways.load() has already checked every word against the sentence). It is
    aria-hidden because the exact deliverable sentence follows it as plain text: screen readers hear the words once.
    A plate with a privacy rule shows its name and that rule only, never part rows. One implementation for the guide
    and the printable sheets."""
    private = ' pw-plate-private' if value.get('kept_out') else ''
    out = [_open('div', 'pw-plate' + private, steps, ' aria-hidden="true"'), '<p class="pw-plate-name">' + whole(value['name']) + '</p>']
    if value['parts']:
        out.append('<ul class="pw-plate-parts">' + ''.join('<li>' + whole(part) + '</li>' for part in value['parts']) + '</ul>')
    if value.get('kept_out'):
        out.append('<p class="pw-plate-kept"><span>' + escape(PRIVACY_LABEL) + '</span><span>' + escape(value['kept_out']) + '</span></p>')
    out.append('</div>')
    return ''.join(out)

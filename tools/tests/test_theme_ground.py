"""The homepage's colour themes stand on one flat ground (owner decision, Living Gallery Batch 1).

The owner's display lifts near-black, so the broad page gradient, its glow layers and the grain overlay of Maya Radiance,
Living Codex and Obsidian Ember read as a wide glow and speckle. Sovereign Skeleton was already flat. The rules that
draw those layers stay in the file as the themes' record; one later block sets each colour theme on its flat ground and
hides the layers. Static checks here; the evidence pack checks the computed styles in Chrome.
"""
import os
from pathlib import Path
import re

R = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
PAGE = (R / 'index.html').read_text(encoding='utf-8')
CSS = re.sub(r'/\*.*?\*/', '', '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', PAGE, re.S)), flags=re.S)
LAYERS = ('grain', 'vignette', 'aurora', 'hero-mist')


def test_each_colour_theme_has_one_flat_ground_after_its_gradient():
    flat = CSS.index('[data-theme] body { background: var(--bg-floor); }')
    codex = CSS.index('html[data-theme="codex"], [data-theme="codex"] body { background: var(--bg-deep); }')
    for theme in ('codex', 'skeleton'):
        assert CSS.index(f'[data-theme="{theme}"] body {{') < flat < codex, 'the flat ground must follow the gradient rules'
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS[flat:]):
        for part in sel.split(','):
            if re.fullmatch(r'\s*(html)?(\[data-theme[^\]]*\])?\s*body\s*', part):
                assert 'gradient' not in body, 'no later gradient on the page body: ' + part.strip()


def test_the_glow_and_grain_layers_are_hidden_in_the_colour_themes():
    rule = '[data-theme] :is(.grain, .vignette, .aurora, .hero-mist) { display: none; }'
    at = CSS.index(rule)
    # No later rule shows a layer again.
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS[at + len(rule):]):
        if any(re.search(r'\.' + layer + r'(?![\w-])', sel) for layer in LAYERS):
            assert not re.search(r'display\s*:(?!\s*none)', body), sel.strip()
    # The layers are still in the page (Sovereign hides them the same way), so nothing else depends on their removal.
    for layer in LAYERS:
        assert f'class="{layer}"' in PAGE


# Task B: the floor is one tone across the whole homepage, the theme's own colour.
GROUND = {'maya': '#02101E', 'codex': '#E8DBC0', 'skeleton': '#050507'}


def _token(selector, name):
    """The value `name` takes in the last rule whose selector is exactly `selector` and declares it (later wins)."""
    vals = []
    for m in re.finditer(r'(?:^|[{}])\s*' + re.escape(selector) + r'\s*\{([^{}]*)\}', CSS):
        vals += re.findall(re.escape(name) + r'\s*:\s*([^;]+);', m.group(1))
    assert vals, (selector, name)
    return vals[-1].strip()


def test_each_ground_is_the_colour_its_browser_bar_already_uses():
    bar = re.search(r"\{ maya: '(#\w+)', codex: '(#\w+)', skeleton: '(#\w+)' \}\[theme\]", PAGE)
    assert bar and dict(zip(('maya', 'codex', 'skeleton'), bar.groups())) == GROUND
    assert _token(':root', '--bg-floor') == GROUND['maya']            # Maya Radiance is the landing's :root
    assert _token('[data-theme="codex"]', '--bg-deep') == GROUND['codex']
    assert _token('[data-theme="skeleton"]', '--bg-floor') == GROUND['skeleton']
    # The shared Theater frame palette stands on the same grounds.
    for theme, ground in GROUND.items():
        assert _token(f'[data-theme="{theme}"]', '--zt-frame-ground') == ground, theme


def test_no_full_width_band_holds_a_second_tone():
    # The council band: accent rules stay, the tint and the inset shading go, in every colour theme.
    sec = CSS.index('[data-theme] .council-section { background: none; box-shadow: none; }')
    strip = CSS.index('[data-theme] .council-strip { background: none; }')
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS):
        if '[data-theme' in sel and re.search(r'\.council-(section|strip)(?![\w-])', sel) and 'not([data-theme])' not in sel:
            assert re.search(r'background\s*:\s*none', body) or 'background' not in body, sel.strip()
    assert sec and strip
    # The opaque bands (scrolled header, menu sheet, popovers, phone dock) are each theme's ground.
    assert re.findall(r'--hdr-band\s*:\s*([^;]+);', CSS) == ['var(--bg-floor)', GROUND['codex'], GROUND['skeleton']]
    assert _token('[data-theme="codex"]', '--hdr-band') == GROUND['codex']
    assert '[data-theme="skeleton"] { --hdr-band: #050507; }' in CSS
    # The Theater chapter's floor is the page ground: Maya and Ember the floor, Codex the paper. No other floor.
    assert re.findall(r'--tsc-floor\s*:\s*([^;]+);', CSS) == ['var(--bg-floor)', 'var(--bg-deep)']
    assert '[data-theme="codex"] .tsc { --tsc-floor: var(--bg-deep);' in CSS
    assert '[data-theme="skeleton"] .tsc { --tsc-edge: #8A7F6E; }' in CSS

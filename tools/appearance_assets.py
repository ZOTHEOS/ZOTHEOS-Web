"""Same-origin appearance assets with byte-pinned script authorization."""
import base64
import hashlib
from pathlib import Path

CONTROLS = 'static/appearance/controls.js'
EFFECTS = 'static/appearance/calavera.js'
STYLE = 'static/appearance/calavera.css'

def digest(root, rel):
    return hashlib.sha256((Path(root) / rel).read_bytes()).digest()

def script(root, rel, defer=True):
    value = digest(root, rel)
    integrity = 'sha256-' + base64.b64encode(value).decode('ascii')
    return '<script' + (' defer' if defer else '') + ' src="/' + rel + '?v=' + value.hex()[:12] + '" integrity="' + integrity + '" crossorigin="anonymous"></script>'

def stylesheet(root, rel=STYLE):
    return '<link rel="stylesheet" href="/' + rel + '?v=' + digest(root, rel).hex()[:12] + '">'

def scripts(root, controls=True, defer_controls=False):
    return (script(root, CONTROLS, defer=defer_controls) if controls else '') + script(root, EFFECTS)

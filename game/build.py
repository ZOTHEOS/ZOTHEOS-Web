# Build: index.src.html (readable) -> index.html (minified, test hooks removed). Needs node + uglify-js + acorn.
# Usage: py -3.10 build.py [path-to-uglify-js/bin/uglifyjs]   (add --dev to keep test hooks)
# Gates: the output must parse as ES5 (acorn ecmaVersion 5), contain no em or en dash, keep Echo logic free of
# trigonometry and Math.random, and stay under a 100 000 byte ceiling (92 000 is the Revision 2.1 budget, warned).
# It also prints the sha256 of the injected overlay CSS, for hosts with a strict style-src CSP that pass no opts.nonce.
import re, subprocess, sys, os, gzip, json, hashlib, base64
here = os.path.dirname(os.path.abspath(__file__))
nm = os.path.expanduser('~/AppData/Roaming/npm/node_modules/n8n/node_modules')
ug = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.join(nm, 'uglify-js/bin/uglifyjs'))
acorn = os.path.join(os.path.dirname(os.path.dirname(ug)), '..', 'acorn')
dev = '--dev' in sys.argv
s = open(os.path.join(here, 'index.src.html'), encoding='utf-8').read()
a, b = s.index('<script>') + 8, s.index('</script>')
js = s[a:b]
# The overlay CSS is the JS string `CSS` (injected as <style id="zgS"> on open); its hash is what a style-src CSP needs.
cb = re.search(r"var CSS = ((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+);", js, flags=re.S)
css_rt = ''.join(re.findall(r"'((?:[^'\\]|\\.)*)'", cb.group(1))).replace("\\'", "'").replace('\\\\', '\\') if cb else ''
csp = base64.b64encode(hashlib.sha256(css_rt.encode('utf-8')).digest()).decode()
# Gate: Echo's game logic (between the /*L*/ marks) uses no trigonometry, no pow/exp/log and no Math.random.
for blk in re.findall(r'/\*L\*/(.*?)/\*L\*/', js, flags=re.S):
    bad = re.findall(r'Math\.(sin|cos|tan|atan2?|pow|exp|log|random)', blk)
    if bad: sys.exit('trig or random in Echo logic: ' + ', '.join(sorted(set(bad))))
if not dev: js = re.sub(r'/\*T\*/.*?/\*T\*/', '', js, flags=re.S)
# arrows=false keeps uglify from emitting ES2015 arrow functions; the game must stay ES5.
out = subprocess.run(['node', ug, '-c', 'arrows=false,passes=2', '-m'], input=js.encode('utf-8'), capture_output=True)
if out.returncode: sys.exit(out.stderr.decode())
mjs = out.stdout.decode('utf-8').strip()
chk = subprocess.run(['node', '-e', 'var a=require(%s);a.parse(require("fs").readFileSync(0,"utf8"),{ecmaVersion:5});' % json.dumps(os.path.abspath(acorn))], input=mjs.encode('utf-8'), capture_output=True)
if chk.returncode: sys.exit('not ES5: ' + chk.stderr.decode()[-400:])
c0, c1 = s.index('<style>') + 7, s.index('</style>')
css = re.sub(r'\s*\n\s*', '', s[c0:c1])
html = s[:c0] + css + s[c1:a] + mjs + s[b:]
assert '—' not in html and '–' not in html, 'em or en dash in output'
# Size (Revision 2.1): the budget is 92 000 bytes of minified JS, about 40 KB gzipped (a warning); 100 000 is the hard ceiling.
# The game loads only when a visitor opens it, so the budget was re-baselined from 72 000 / 90 000.
if not dev and len(mjs.encode()) > 100000: sys.exit('minified js is %d bytes, over the 100 000 byte ceiling' % len(mjs.encode()))
if not dev and len(mjs.encode()) > 92000: print('WARNING: minified js is %d bytes, over the 92 000 byte budget' % len(mjs.encode()))
open(os.path.join(here, 'index.dev.html' if dev else 'index.html'), 'w', encoding='utf-8').write(html)
print('js %d bytes (gz %d), page css %d, file %d, ES5 ok' % (len(mjs.encode()), len(gzip.compress(mjs.encode())), len(css), len(html.encode())))
print("overlay css %d bytes; for a strict CSP without opts.nonce allow: style-src 'sha256-%s'" % (len(css_rt.encode('utf-8')), csp))

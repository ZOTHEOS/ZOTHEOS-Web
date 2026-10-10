# Build: index.src.html (readable) -> index.html (minified, test hooks removed). Needs node + uglify-js + acorn.
# Usage: py -3.10 build.py [path-to-uglify-js/bin/uglifyjs]   (add --dev to keep test hooks)
# Gates: the output must parse as ES5 (acorn ecmaVersion 5), contain no em or en dash, keep Echo logic free of
# trigonometry and Math.random, and stay under a 90 000 byte ceiling (72 000 is the design budget, warned).
import re, subprocess, sys, os, gzip, json
here = os.path.dirname(os.path.abspath(__file__))
nm = os.path.expanduser('~/AppData/Roaming/npm/node_modules/n8n/node_modules')
ug = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.join(nm, 'uglify-js/bin/uglifyjs'))
acorn = os.path.join(os.path.dirname(os.path.dirname(ug)), '..', 'acorn')
dev = '--dev' in sys.argv
s = open(os.path.join(here, 'index.src.html'), encoding='utf-8').read()
a, b = s.index('<script>') + 8, s.index('</script>')
js = s[a:b]
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
# Size: the design budget is 72 000 bytes of minified JS (a warning); 90 000 is a hard ceiling against further growth.
if not dev and len(mjs.encode()) > 90000: sys.exit('minified js is %d bytes, over the 90 000 byte ceiling' % len(mjs.encode()))
if not dev and len(mjs.encode()) > 72000: print('WARNING: minified js is %d bytes, over the 72 000 byte design budget' % len(mjs.encode()))
open(os.path.join(here, 'index.dev.html' if dev else 'index.html'), 'w', encoding='utf-8').write(html)
print('js %d bytes (gz %d), page css %d, file %d, ES5 ok' % (len(mjs.encode()), len(gzip.compress(mjs.encode())), len(css), len(html.encode())))

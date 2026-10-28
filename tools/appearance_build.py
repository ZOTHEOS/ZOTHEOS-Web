#!/usr/bin/env python3
"""Synchronize cached appearance controls and the hand-authored page adapters. No network reads."""
from pathlib import Path
import argparse
import re
import sys
from appearance_assets import scripts, stylesheet, script

def update(root, check=False):
    root=Path(root); changes={}
    def offer(rel, text):
        p=root/rel
        if not p.exists() or p.read_text(encoding='utf-8')!=text: changes[rel]=text
    controls=(root/'tools/nations/partials/appearance.js').read_text(encoding='utf-8')
    offer('static/appearance/controls.js',controls)
    offer('static/appearance/palette.css',(root/'tools/nations/partials/tokens.css').read_text(encoding='utf-8'))
    if check and changes: return changes
    for rel,text in changes.items():
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')
    for rel in ['index.html','download.html','game/index.src.html']:
        p=root/rel;s=p.read_text(encoding='utf-8')
        adapter=rel!='index.html'
        # First-paint preference is early; palette styles must follow the page's own styles.
        s=re.sub(r'<!-- site-appearance:start -->.*?<!-- site-appearance:end -->\n?', '', s, flags=re.S)
        s=re.sub(r'<!-- site-appearance-prepaint:start -->.*?<!-- site-appearance-prepaint:end -->\n?', '', s, flags=re.S)
        head=stylesheet(root)
        if adapter:
            boot=(root/'tools/nations/partials/bootstrap.js').read_text(encoding='utf-8')
            early='<!-- site-appearance-prepaint:start -->\n<script id="site-theme-prepaint">'+boot+'</script>\n<!-- site-appearance-prepaint:end -->'
            s=s.replace('<style',early+'\n<style',1)
            head=stylesheet(root,'static/appearance/palette.css')+head
            if rel=='game/index.src.html':
                head='<style id="site-appearance-styles">'+(root/'static/appearance/palette.css').read_text(encoding='utf-8')+'\n'+(root/'static/appearance/calavera.css').read_text(encoding='utf-8')+'</style>'
                head+='\n'+script(root,'static/appearance/game-theme.js',defer=False)
        head+='\n'+scripts(root,controls=rel=='download.html',defer_controls=True)
        if rel=='download.html':head+='\n<noscript><style>.site-appearance-launch,.site-appearance-pop{display:none!important}</style></noscript>'
        block='<!-- site-appearance:start -->\n'+head+'\n<!-- site-appearance:end -->'
        s=s.replace('</head>',block+'\n</head>',1)
        offer(rel,s)
    # Existing generated pages must not carry stale integrity during a source rebuild. Only these
    # explicit local appearance assets may be repinned; canonical builders still verify full output.
    pages=[root/'index.html',root/'download.html',root/'game/index.src.html',root/'game/index.html',root/'theater.html',root/'nations.html']+sorted((root/'nations').rglob('*.html'))
    for p in pages:
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix();s=changes.get(rel,p.read_text(encoding='utf-8'))
        s=re.sub(r'<script\b[^>]*\bsrc="/(static/appearance/(?:controls|calavera|game-theme)\.js)(?:\?[^"]*)?"[^>]*></script>',lambda m:script(root,m.group(1),defer=m.group(1).endswith('/calavera.js') or m.group(1).endswith('/controls.js') and rel=='download.html'),s)
        s=re.sub(r'<link rel="stylesheet" href="/(static/appearance/(?:calavera|palette)\.css)(?:\?[^"]*)?">',lambda m:stylesheet(root,m.group(1)),s)
        offer(rel,s)
    if not check:
        for rel,text in changes.items():(root/rel).write_text(text,encoding='utf-8',newline='\n')
    return changes

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--check',action='store_true');a=ap.parse_args()
    changes=update(a.root,a.check)
    print('appearance assets: '+(str(len(changes))+' files synchronized' if len(changes)>8 else ', '.join(changes) if changes else 'in sync'))
    return int(a.check and bool(changes))
if __name__=='__main__':sys.exit(main())

"""Flash check for the Council Route review captures (OpenCV + NumPy), after the WCAG 2.3.1 general and red flash rules.

A screening approximation, not a certified photosensitive-epilepsy analysis:
  * frames are decoded losslessly from the FFV1 master and reduced with OpenCV INTER_AREA (default 1/4 scale);
  * relative luminance per pixel from linearised sRGB (WCAG definition);
  * fields: windows the size of a 10 degree field (default 1/3 of width x 1/3 of height on desktop, 3/4 x 1/3 on a
    phone held at reading distance), stepped by half a field;
  * per field, the frame-to-frame mean decides the direction of a run; when the direction turns, the finished run is a
    transition if at least 25% of the field's pixels changed by 0.1 or more in that direction with the darker state
    below 0.8 (general), or changed in red value by more than 20 with a saturated red (R/(R+G+B) >= 0.8, red value
    (R - G - B) x 320) at either end (red);
  * a flash is a pair of opposing transitions; the limit is 3 flashes in any one second, per field.
  py -3.10 flash_check.py out/desktop_master.mkv [--field 0.333 0.333] [--json out/flash_desktop.json]
  py -3.10 flash_check.py --selftest       synthetic sequences that must pass or fail
"""
import argparse
import json
import subprocess
import sys

import cv2
import numpy as np

_s = np.arange(256) / 255.0
LIN = np.where(_s <= 0.04045, _s / 12.92, ((_s + 0.055) / 1.055) ** 2.4).astype(np.float32)


def planes(rgb):
    lin = LIN[rgb]
    r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    tot = r + g + b
    sat = (tot > 0) & (r >= 0.8 * np.maximum(tot, 1e-9))
    red = np.where(sat, np.maximum(r - g - b, 0) * 320.0, 0.0).astype(np.float32)
    return lum.astype(np.float32), red, sat


class Analyzer:
    def __init__(self, w, h, fps, field=(1 / 3, 1 / 3)):
        self.w, self.h, self.fps = w, h, fps
        fw, fh = max(2, int(round(w * field[0]))), max(2, int(round(h * field[1])))
        xs = list(range(0, max(1, w - fw + 1), max(1, fw // 2)))
        ys = list(range(0, max(1, h - fh + 1), max(1, fh // 2)))
        if xs[-1] != w - fw:
            xs.append(max(0, w - fw))
        if ys[-1] != h - fh:
            ys.append(max(0, h - fh))
        self.fields = [(x, y, fw, fh) for y in ys for x in xs]
        self.area = fw * fh
        n = len(self.fields)
        self.kinds = {}
        for kind in ('general', 'red'):
            self.kinds[kind] = {'dir': np.zeros(n, np.int8), 'start': np.zeros(n, np.int64), 'prev': None,
                                'events': [[] for _ in range(n)]}
        self.store = {}
        self.i = -1
        self.max_step = 0.0

    def means(self, plane):
        ii = cv2.integral(plane.astype(np.float64))
        return np.array([(ii[y + fh, x + fw] - ii[y, x + fw] - ii[y + fh, x] + ii[y, x]) / self.area
                         for x, y, fw, fh in self.fields])

    def push(self, rgb):
        self.i += 1
        lum, red, sat = planes(rgb)
        self.store[self.i] = (lum, red, sat)
        for kind, plane in (('general', lum), ('red', red)):
            k = self.kinds[kind]
            m = self.means(plane)
            if k['prev'] is not None:
                dm = m - k['prev']
                if kind == 'general':
                    self.max_step = max(self.max_step, float(np.abs(dm).max()))
                eps = 1e-4 if kind == 'general' else 1e-3
                sg = np.where(dm > eps, 1, np.where(dm < -eps, -1, 0)).astype(np.int8)
                for f in np.nonzero((sg != 0) & (sg != k['dir']))[0]:
                    if k['dir'][f] != 0:
                        self.close(kind, f, self.i - 1)
                    k['dir'][f] = sg[f]
                    k['start'][f] = self.i - 1
            k['prev'] = m
        keep = {int(s) for k in self.kinds.values() for s in k['start']} | {self.i}
        for j in list(self.store):
            if j not in keep:
                del self.store[j]

    def close(self, kind, f, end):
        k = self.kinds[kind]
        s, sgn = int(k['start'][f]), int(k['dir'][f])
        if s == end or s not in self.store:
            return
        x, y, fw, fh = self.fields[f]
        a, b = self.store[s], self.store[end]
        if kind == 'general':
            la, lb = a[0][y:y + fh, x:x + fw], b[0][y:y + fh, x:x + fw]
            d = (lb - la) * sgn
            hit = (d >= 0.1) & (np.minimum(la, lb) < 0.8)
        else:
            ra, rb = a[1][y:y + fh, x:x + fw], b[1][y:y + fh, x:x + fw]
            d = (rb - ra) * sgn
            hit = (d > 20) & (a[2][y:y + fh, x:x + fw] | b[2][y:y + fh, x:x + fw])
        if hit.mean() >= 0.25:
            k['events'][f].append((end, sgn))

    def finish(self):
        for kind, k in self.kinds.items():
            for f in range(len(self.fields)):
                if k['dir'][f] != 0:
                    self.close(kind, f, self.i)
        out = {'frames': self.i + 1, 'fps': self.fps, 'size': [self.w, self.h], 'fields': len(self.fields),
               'max_field_mean_luminance_step': round(self.max_step, 5)}
        for kind, k in self.kinds.items():
            worst, worst_field, transitions = 0, None, 0
            for f, ev in enumerate(k['events']):
                transitions += len(ev)
                flashes, last = [], None
                for fr, sg in ev:
                    if last is not None and sg == -last:
                        flashes.append(fr)
                        last = None
                    else:
                        last = sg
                j = 0
                for i2, fr in enumerate(flashes):
                    while flashes[j] <= fr - self.fps:
                        j += 1
                    if i2 - j + 1 > worst:
                        worst, worst_field = i2 - j + 1, self.fields[f]
            out[kind] = {'transitions': transitions, 'max_flashes_in_any_second': worst, 'worst_field': worst_field,
                         'pass': worst <= 3}
        out['pass'] = out['general']['pass'] and out['red']['pass']
        return out


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                        '-of', 'json', path], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)['streams'][0]
    num, den = s['r_frame_rate'].split('/')
    return s['width'], s['height'], float(num) / float(den)


def analyze_video(path, field, scale):
    w, h, fps = probe(path)
    sw, sh = max(2, w // scale), max(2, h // scale)
    an = Analyzer(sw, sh, fps, field)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        an.push(cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_AREA))
    p.wait()
    out = an.finish()
    out.update(source=path, source_size=[w, h], scale=scale, field_fraction=list(field))
    return out


def selftest():
    W, H, FPS = 160, 90, 60
    black = np.zeros((H, W, 3), np.uint8)
    white = np.full((H, W, 3), 255, np.uint8)
    red = black.copy(); red[..., 0] = 200

    def run(frames):
        an = Analyzer(W, H, FPS)
        for f in frames:
            an.push(f)
        return an.finish()

    def toggle(a, b, hz, seconds=2):
        half = int(FPS / hz / 2)
        return [(a if (i // half) % 2 == 0 else b) for i in range(FPS * seconds)]

    small = black.copy(); small[0:9, 0:16] = 255
    fade = [np.full((H, W, 3), int(255 * min(1, i / 60)) if i < 60 else int(255 * max(0, (120 - i) / 60)), np.uint8) for i in range(120)]
    cases = {
        'full-field black/white at 5 Hz fails': (toggle(black, white, 5), False, 'general'),
        'full-field black/white at 1.5 Hz passes': (toggle(black, white, 1.5), True, 'general'),
        'small area (10% of a field) at 10 Hz passes': (toggle(black, small, 10), True, 'general'),
        'saturated red at 5 Hz fails the red rule': (toggle(black, red, 5), False, 'red'),
        'one slow fade up and down passes': (fade, True, 'general'),
    }
    ok = True
    for name, (frames, expect, kind) in cases.items():
        r = run(frames)
        good = r[kind]['pass'] == expect
        ok &= good
        print(('ok   ' if good else 'FAIL ') + name, r[kind]['max_flashes_in_any_second'])
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('videos', nargs='*')
    ap.add_argument('--field', nargs=2, type=float, default=None, help='field width and height as fractions of the frame')
    ap.add_argument('--scale', type=int, default=4)
    ap.add_argument('--json')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    results = []
    for v in a.videos:
        field = tuple(a.field) if a.field else ((0.75, 1 / 3) if 'phone' in v else (1 / 3, 1 / 3))
        r = analyze_video(v, field, a.scale)
        results.append(r)
        print(json.dumps(r))
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=1)
    sys.exit(0 if all(r['pass'] for r in results) else 1)


if __name__ == '__main__':
    main()

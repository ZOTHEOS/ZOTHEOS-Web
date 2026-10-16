"""Mutation check for the Council Route controller tests: every deliberate bug below must make at least one test in
tools/tests/test_council_route.cjs fail. Each mutant is written to a temporary file; the fragment is never changed.

  py -3.10 tools/route/mutation_check.py          prints CAUGHT or MISSED per mutant, exit 1 if any is missed
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
FRAG = os.path.join(HERE, 'council_route.fragment.html')
TEST = os.path.join(ROOT, 'tools', 'tests', 'test_council_route.cjs')

MUT = {
    # Playback rules: autoplay on view in Living and Calm only, explicit Pause respected, pause and resume by view.
    'starts on load wherever the stage is': ("  if (mq.addEventListener) mq.addEventListener('change', motion);\n",
                                             "  if (mq.addEventListener) mq.addEventListener('change', motion);\n  play();\n"),
    'autoplays in Still': ("!ended && !still() && !d.hidden", "!ended && !d.hidden"),
    'autoplays under 60% in view': ("seen >= .6 && gone()", "seen >= .25 && gone()"),
    'autoplay ignores an explicit Pause': ("if (!playing && !held && !ended", "if (!playing && !ended"),
    'Pause does not hold': ("if (playing) { held = true; pause(); }", "if (playing) { pause(); }"),
    'Play does not release the hold': ("else { held = false; play(1); }", "else { play(1); }"),
    'stepping does not hold': ("  if (k < 0 || k > 7) return;\n  held = true;\n", "  if (k < 0 || k > 7) return;\n"),
    'restarts on its own after the end': ("if (!playing && !held && !ended && ", "if (!playing && !held && "),
    'autoplays in a hidden tab': ("!still() && !d.hidden && seen", "!still() && seen"),
    'autoplays under the intro': ("seen >= .6 && gone()) play();", "seen >= .6) play();"),
    'a replayed intro does not pause': ("gone() ? auto() : pause()", "gone() ? auto() : 0"),
    'autoplay scrolls the page': ("if (s) $('crRun').scrollIntoView", "if (1) $('crRun').scrollIntoView"),
    'no pause when hidden': ("d.hidden ? pause() : auto()", "d.hidden ? 0 : auto()"),
    'no resume when the tab returns': ("d.hidden ? pause() : auto()", "d.hidden ? pause() : 0"),
    'no pause out of view': ("else if (vis) pause();", "else if (0) pause();"),
    'pauses under 60% instead of 25%': ("if (seen >= .25) vis = true;", "if (seen >= .6) vis = true;"),
    'no resume back in view': ("  else if (vis) pause();\n  auto();\n};", "  else if (vis) pause();\n};"),
    'Still keeps animations': ("if (!canPlay() && A) paint(beat);", "if (0) paint(beat);"),
    'loops at the end': ("if (k > 7) { ended = true; return paint(0); }", "if (k > 7) { paint(0); return play(); }"),
    'Play allowed in Still': ("const PLAY_IN_STILL = false;", "const PLAY_IN_STILL = true;"),
    # Steps, captions, timing, keys, scroll, transcript.
    'Next goes back': ("bN.addEventListener('click', () => step(1));", "bN.addEventListener('click', () => step(-1));"),
    'rest caption announced': ("cap.setAttribute('aria-live', k ? 'polite' : 'off');", "cap.setAttribute('aria-live', 'polite');"),
    'wrong timing rule': (".26 * c.split(' ').length", ".25 * c.split(' ').length"),
    'arrow keys anywhere': ("$('crCtl').addEventListener('keydown'", "d.addEventListener('keydown'"),
    'modified arrows step': ("if (k && !(e.altKey || e.ctrlKey || e.metaKey || e.shiftKey))", "if (k)"),
    'Play does not scroll': ("  if (s) $('crRun').scrollIntoView({block: 'nearest'});\n", ""),
    'Play scrolls the stage only': ("$('crRun').scrollIntoView({block: 'nearest'});", "S.scrollIntoView({block: 'nearest'});"),
    'transcript opens on a live Still switch': ("function motion() {\n  if (!canPlay() && A) paint(beat);\n",
                                                "function motion() {\n  if (!canPlay() && A) paint(beat);\n  if (still()) $('crText').open = true;\n"),
    'transcript not open at load in Still': ("  if (still()) $('crText').open = true;\n", ""),
    # CC and the Audio slot.
    'CC never turns off': ("R.dataset.cc = on ? 'on' : 'off';", "R.dataset.cc = 'on';"),
    'CC state not announced': ("  bC.setAttribute('aria-pressed', on);\n", ""),
    'CC pauses the run': ("  bC.setAttribute('aria-pressed', on);\n", "  bC.setAttribute('aria-pressed', on);\n  pause();\n"),
    'Audio shown without a sound file': ("bS.hidden = !SOUND_FILE || !canPlay();", "bS.hidden = !canPlay();"),
    'Audio shown in Still': ("bS.hidden = !SOUND_FILE || !canPlay();", "bS.hidden = !SOUND_FILE;"),
    'sound loaded before a press': ("  R.hidden = false;\n", "  R.hidden = false;\n  au = d.createElement('audio');\n"),
    'sound keeps playing on Pause': ("  } else au.pause();\n", "  }\n"),
    # Haptics.
    'pulses before any interaction': (" && nv.userActivation.hasBeenActive", ""),
    'pulses in Still': ("p !== 'off' && !still() && nv.vibrate", "p !== 'off' && nv.vibrate"),
    'ignores the haptics preference': ("if (p !== 'off' && !still()", "if (!still()"),
    'pulse too long': ("nv.vibrate(10)", "nv.vibrate(40)"),
    'double pulse on Play': ("  if (beat === b) buzz();\n", "  buzz();\n"),
    'no pulse on Play or Pause': ("  if (beat === b) buzz();\n", ""),
    'no pulse on a beat change': ("  if (k !== beat) buzz();\n", ""),
    'storage errors escape': ("try { p = w.localStorage.getItem('zotheos_haptics'); } catch (e) {}",
                              "p = w.localStorage.getItem('zotheos_haptics');"),
}


def main():
    node = shutil.which('node')
    if not node:
        print('node is not installed')
        return 2
    src = open(FRAG, encoding='utf-8', newline='').read()
    clean = subprocess.run([node, TEST, FRAG], capture_output=True, text=True, encoding='utf-8')
    if clean.returncode:
        print('the unmutated fragment fails its tests; fix that first')
        return 1
    missed = 0
    with tempfile.TemporaryDirectory() as t:
        for name, (a, b) in MUT.items():
            assert src.count(a) == 1, 'mutant anchor not found exactly once: ' + name
            p = os.path.join(t, 'frag.html')
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(src.replace(a, b))
            r = subprocess.run([node, TEST, p], capture_output=True, text=True, encoding='utf-8')
            bad = [ln for ln in r.stdout.splitlines() if ln.startswith('not ok')]
            caught = r.returncode != 0
            print(('CAUGHT ' if caught else 'MISSED ') + name + (' -> ' + bad[0] if bad else ''))
            missed += not caught
    print('%d of %d mutants caught' % (len(MUT) - missed, len(MUT)))
    return 1 if missed else 0


if __name__ == '__main__':
    sys.exit(main())

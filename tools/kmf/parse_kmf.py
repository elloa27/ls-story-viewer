"""Parse KnightmareStory timeline bundles -> compact viewer json.
usage: parse_kmf.py <rows.json> <cache_dir> <out_dir>"""
import sys, os, json, re
from concurrent.futures import ProcessPoolExecutor
import UnityPy

def parse(args):
    path, f, out = args
    try:
        env = UnityPy.load(f)
    except Exception as e:
        return path, f'load {e}'
    objs = {o.path_id: o for o in env.objects}
    sc = {}
    def scr(o):
        if o.path_id in sc: return sc[o.path_id]
        try: s = o.read().m_Script.read().m_Name
        except Exception: s = None
        sc[o.path_id] = s; return s
    mbs = [o for o in env.objects if o.type.name == 'MonoBehaviour']
    tl = [o for o in mbs if scr(o) == 'TimelineAsset']
    if not tl: return path, 'notl'
    T = tl[0].read_typetree()
    R = {'id': path, 'kmf': [], 'cap': [], 'se': [], 'l2d': [], 'shot': [], 'act': {}, 'pp': [], 'fx': [], 'cut': [], 'mov': [], 'slow': []}
    for o in mbs:
        if scr(o) == 'KnightmareStoryResourceProvider':
            t = o.read_typetree(); R['kmf'] = t.get('knightmareFrameIds', []); R['field'] = t.get('fieldId')
    end = 0.0
    def walk(pid, group=''):
        nonlocal end
        o = objs.get(pid)
        if not o: return
        s = scr(o); t = o.read_typetree(); name = t.get('m_Name') or ''
        muted = t.get('m_Muted')
        if muted: return
        g = name if s == 'GroupTrack' else group
        for c in t.get('m_Clips', []):
            st, du = round(c['m_Start'], 3), round(c['m_Duration'], 3)
            end = max(end, st + du)
            ao = objs.get(c['m_Asset']['m_PathID']); ak = scr(ao) if ao else None
            at = ao.read_typetree() if ao else {}
            tp = at.get('template', {})
            if ak == 'CaptionClip':
                R['cap'].append([st, du, tp.get('speaker', ''), tp.get('captionText', '')])
            elif ak == 'PlaySeClip':
                R['se'].append([st, (tp.get('cueName') or '').lower(), round(tp.get('volume', 1), 2)])
            elif ak == 'Live2dClip':
                R['l2d'].append([st, du, tp.get('live2dId'), tp.get('heroFlag', 0), g])
            elif ak == 'AnimationPlayableAsset':
                m = re.match(r'KmfMotion(\d+)', name)
                if m: R['act'].setdefault(int(m.group(1)), []).append([st, du])
                elif name.startswith('Cameraman') or name.startswith('Camera'):
                    R['shot'].append(st)
            elif ak == 'ActivationPlayableAsset':
                m = re.match(r'KmfActivation(\d+)', name)
                if m: R['act'].setdefault(int(m.group(1)), []).append([st, du])
            elif ak == 'PostProcessClip':
                R['pp'].append([st, du])
            elif ak == 'TimelineEffectClip':
                R['fx'].append([st, du, g, name])
            elif ak == 'PlayMovieClip':
                R['mov'].append([st, du, at.get('moviePath')])
            elif ak == 'TimeDilationClip':
                R['slow'].append([st, du, round(tp.get('timeScale', 1), 2)])
        for m in t.get('m_Markers', {}).get('m_Objects', []):
            mo = objs.get(m['m_PathID'])
            if mo and scr(mo) and 'CutIn' in scr(mo):
                mt = mo.read_typetree(); R['cut'].append(round(mt.get('m_Time', 0), 3))
        for ch in t.get('m_Children', []):
            walk(ch['m_PathID'], g)
    for tr in T['m_Tracks']:
        walk(tr['m_PathID'])
    # markers on the timeline itself
    for m in T.get('m_MarkerTrack', {}) and [T['m_MarkerTrack']] or []:
        walk(m['m_PathID'])
    tx = []
    for o in mbs:
        if scr(o) == 'TextMeshProUGUI':
            s = o.read_typetree().get('m_text', '').strip()
            if s: tx.append(s)
    R['tmp'] = tx
    fd = T.get('m_FixedDuration', 0)
    R['d'] = round(end if T.get('m_DurationMode', 0) == 0 or not fd else fd, 3)
    for k in ('cap', 'se', 'l2d', 'pp', 'fx', 'mov', 'slow'):
        R[k].sort()
    R['shot'] = sorted(set(R['shot']))
    R['cut'] = sorted(set(R['cut']))
    R['act'] = {k: sorted(v) for k, v in sorted(R['act'].items())}
    json.dump(R, open(f'{out}/{path}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    return path, 'ok'

if __name__ == '__main__':
    rows = json.load(open(sys.argv[1])); cd = sys.argv[2]; out = sys.argv[3]
    os.makedirs(out, exist_ok=True)
    jobs = [(p, f'{cd}/{c}', out) for p, c in rows]
    st = {}
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        for p, r in ex.map(parse, jobs, chunksize=2):
            st[r[:4]] = st.get(r[:4], 0) + 1
            if r != 'ok': print(p, r)
    print(st)

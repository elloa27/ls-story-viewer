"""Extract Cubism-for-Unity model into a compact runtime pack for the viewer.
usage: extract_live.py <main_bundle> <tex_bundle> <outdir>
Output: model.moc3, tex0.webp.., m.json (model3 settings + inline exp/pose/motions refs), mot/<m>.motion3.json, exp/<e>.exp3.json
"""
import sys, os, json, math
import UnityPy

BL = {0: 'Overwrite', 1: 'Add', 2: 'Multiply'}

def curve_to_segments(ks):
    """Unity keyframes -> motion3 flat segment list. Returns (segments, n_segments, n_points)."""
    ks = sorted(ks, key=lambda k: k['time'])
    seg = [ks[0]['time'], ks[0]['value']]
    nseg = 0; npts = 1
    for a, b in zip(ks, ks[1:]):
        t0, v0, t1, v1 = a['time'], a['value'], b['time'], b['value']
        dt = t1 - t0
        if dt <= 0:
            continue
        so, si = a.get('outSlope', 0), b.get('inSlope', 0)
        if not math.isfinite(so) or not math.isfinite(si):
            seg += [2, t1, v1]; npts += 1  # stepped
        elif abs(so) < 1e-9 and abs(si) < 1e-9 and v0 == v1:
            seg += [0, t1, v1]; npts += 1  # linear (flat)
        else:
            seg += [1, t0 + dt / 3, v0 + so * dt / 3, t1 - dt / 3, v1 - si * dt / 3, t1, v1]; npts += 3
        nseg += 1
    if nseg == 0:  # single key: hold
        seg += [0, ks[0]['time'] + 0.01, ks[0]['value']]; nseg = 1; npts += 1
    return seg, nseg, npts

def extract(main, tex, out, part_ids=None):
    os.makedirs(out + '/mot', exist_ok=True); os.makedirs(out + '/exp', exist_ok=True)
    env = UnityPy.load(main, tex)
    go_names = {o.path_id: o.read().m_Name for o in env.objects if o.type.name == 'GameObject'}
    exps, motions, pose, texs = {}, {}, {}, []
    params = set(); parts = set()
    for o in env.objects:
        t = o.type.name
        if t == 'Texture2D':
            d = o.read()
            texs.append(d.m_Name)
            d.image.save(f'{out}/{d.m_Name}.webp', 'WEBP', quality=88, method=4)
        elif t == 'MonoBehaviour':
            try:
                d = o.read(); s = d.m_Script.read().m_Name
            except Exception:
                continue
            if s == 'CubismMoc':
                open(f'{out}/model.moc3', 'wb').write(bytes(o.read_typetree()['_bytes']))
            elif s == 'CubismPart':
                parts.add(go_names.get(o.read_typetree()['m_GameObject']['m_PathID']))
            elif s == 'CubismExpressionData':
                tt = o.read_typetree(); name = tt['m_Name'].replace('.exp3', '')
                exps[name] = {'Type': 'Live2D Expression', 'FadeInTime': tt.get('FadeInTime', 0.3), 'FadeOutTime': tt.get('FadeOutTime', 0.3),
                              'Parameters': [{'Id': p['Id'], 'Value': p['Value'], 'Blend': BL.get(p['Blend'], 'Add')} for p in tt['Parameters']]}
            elif s == 'CubismFadeMotionData':
                tt = o.read_typetree(); name = tt['m_Name'].replace('.fade', '')
                motions[name] = tt
            elif s == 'CubismPosePart':
                tt = o.read_typetree()
                pid = go_names.get(tt['m_GameObject']['m_PathID'])
                pose.setdefault(tt['GroupIndex'], []).append((tt['PartIndex'], pid, tt.get('Link') or []))
    texs.sort()
    # motions -> motion3.json
    mot_files = {}
    for name, tt in motions.items():
        curves = []; tseg = tpts = 0
        for i, (pid, c) in enumerate(zip(tt['ParameterIds'], tt['ParameterCurves'])):
            ks = c['m_Curve']
            if not ks: continue
            seg, ns, npnt = curve_to_segments(ks)
            tgt = 'PartOpacity' if pid in parts else 'Parameter'
            cv = {'Target': tgt, 'Id': pid, 'Segments': seg}
            fi = tt['ParameterFadeInTimes'][i] if i < len(tt.get('ParameterFadeInTimes', [])) else -1
            fo = tt['ParameterFadeOutTimes'][i] if i < len(tt.get('ParameterFadeOutTimes', [])) else -1
            if fi >= 0: cv['FadeInTime'] = fi
            if fo >= 0: cv['FadeOutTime'] = fo
            curves.append(cv); tseg += ns; tpts += npnt
        dur = float(tt.get('MotionLength', 1.0)) or 1.0
        m3 = {'Version': 3, 'Meta': {'Duration': dur, 'Fps': 30.0, 'Loop': name == 'm_000', 'AreBeziersRestricted': False,
              'FadeInTime': tt.get('FadeInTime', 0.5), 'FadeOutTime': tt.get('FadeOutTime', 0.5),
              'CurveCount': len(curves), 'TotalSegmentCount': tseg, 'TotalPointCount': tpts,
              'UserDataCount': 0, 'TotalUserDataSize': 0}, 'Curves': curves}
        json.dump(m3, open(f'{out}/mot/{name}.motion3.json', 'w'), separators=(',', ':'))
        mot_files[name] = f'mot/{name}.motion3.json'
    for n, e in exps.items():
        json.dump(e, open(f'{out}/exp/{n}.exp3.json', 'w'), separators=(',', ':'))
    fr = {'Moc': 'model.moc3', 'Textures': [f'{n}.webp' for n in texs],
          'Expressions': [{'Name': n, 'File': f'exp/{n}.exp3.json'} for n in sorted(exps)],
          'Motions': {n: [{'File': f}] for n, f in sorted(mot_files.items())}}
    if pose:
        groups = [[{'Id': pid, 'Link': list(link)} for _, pid, link in sorted(pose[g])] for g in sorted(pose)]
        json.dump({'Type': 'Live2D Pose', 'FadeInTime': 0.3, 'Groups': groups}, open(f'{out}/pose3.json', 'w'))
        fr['Pose'] = 'pose3.json'
    model = {'Version': 3, 'FileReferences': fr, 'Groups': [
        {'Target': 'Parameter', 'Name': 'EyeBlink', 'Ids': ['ParamEyeLOpen', 'ParamEyeROpen']},
        {'Target': 'Parameter', 'Name': 'LipSync', 'Ids': ['ParamMouthOpenY']}]}
    json.dump(model, open(f'{out}/model.model3.json', 'w'), separators=(',', ':'))
    return len(texs), len(exps), len(mot_files)

if __name__ == '__main__':
    print(extract(*sys.argv[1:4]))

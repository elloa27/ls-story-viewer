"""Build viewer data for knightmare cutscenes.
Inputs: out/*.json (parse_kmf.py), caps_ja.json (unique caption lines), kmfimg/ (conv_kmf.py)
Output: pack_kmf/ -> copy to data/kmf/ (and kmfimg -> data/kmf/img)
"""
import json, glob, os, re
_u = {}
for _f in sorted(glob.glob('out/*.json')):
    for _c in json.load(open(_f))['cap']: _u.setdefault(_c[3], _c[2])
L = list(_u.items())
# Korean captions, in the order caps_ja.json lists the unique Japanese lines (first appearance, sorted cutscene ids)
T = json.load(open('/home/claude/ls-story-viewer/translation/ko/kmf_captions_ko.json'))
assert len(T) == len(L), (len(T), len(L))
# sanity: gender markers count parity
for (ja, s), ko in zip(L, T):
    if ja.count('%') != ko.count('%'): print('PCT', ja, '|', ko)
    if ('[HERO_NAME]' in ja) != ('[HERO_NAME]' in ko): print('HERO', ja, ko)
names = json.load(open('/home/claude/ls-story-viewer/translation/ko/names.json'))
FW = str.maketrans('ABCDEFGHIJ', 'ＡＢＣＤＥＦＧＨＩＪ')
extra = {'スザク、カレン': '스자쿠, 카렌', '黒の騎士団輸送員B': '흑의 기사단 수송원 B', '日本革命軍兵士Ｃ': '일본 혁명군 병사 C',
         '基地パイロットC': '기지 파일럿 C', '基地パイロットD': '기지 파일럿 D', '基地パイロットE': '기지 파일럿 E',
         '得意げな傭兵': '의기양양한 용병', 'ブラックナイツA': '블랙 나이츠 A', 'ブラックナイツB': '블랙 나이츠 B',
         '日本解放戦線戦闘員': '일본 해방전선 전투원', 'ブルーバロンズ兵Ｄ': '블루 바론즈 병사 D', '受験生': '수험생',
         'バーストチルドレンB': '버스트 칠드런 B', 'リューネベルクパイロットB': '뤼네베르크 파일럿 B',
         'シュヴァルツナイト隊員Ｉ': '슈바르츠 나이트 대원 I', 'キルアニアパイロットB': '킬라니아 파일럿 B',
         'ネオ・ブリタニアパイロットB': '네오 브리타니아 파일럿 B', 'ネオ・ブリタニアパイロットD': '네오 브리타니아 파일럿 D'}
ko = {ja: k for (ja, s), k in zip(L, T)}
spk = {}
imgs = {int(os.path.basename(f)[:-5]) for f in glob.glob('kmfimg/*.webp')}
def img_for(k):
    if k in imgs: return k
    fam = [i for i in sorted(imgs) if i // 100 == k // 100]
    return fam[0] if fam else None
OUT = 'pack_kmf'; os.makedirs(OUT, exist_ok=True)
used = set(); miss_spk = set()
for f in sorted(glob.glob('out/*.json')):
    r = json.load(open(f))
    caps = []
    for t, du, s, ja in r['cap']:
        if s and s != '[HERO_NAME]':
            kn = names.get(s) or names.get(s.translate(FW)) or extra.get(s)
            if kn: spk[s] = kn
            else: miss_spk.add(s)
        caps.append([t, du, s, ja.replace('\\n', '\n')])
    im = [img_for(k) for k in r['kmf']]
    used |= {i for i in im if i}
    # flashes: effect tracks/clips named with white flash
    fl = sorted({round(x[0], 2) for x in r['fx'] if re.search('白フラ|フラッシュ|flash', x[2] + x[3], re.I)})
    D = {'d': r['d'], 'img': im, 'act': r['act'], 'shot': r['shot'], 'se': r['se'], 'cap': caps,
         'l2d': [[a, b, c, h] for a, b, c, h, g in r['l2d']], 'pp': [round(p[0], 2) for p in r['pp'] if p[1] < 4],
         'fl': fl, 'cut': r['cut'], 'slow': r['slow']}
    json.dump(D, open(f"{OUT}/{r['id']}.json", 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump({'text': {k.replace('\\n', '\n'): v.replace('\\n', '\n') for k, v in ko.items()}, 'spk': spk}, open(f'{OUT}/_ko.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('missing spk', miss_spk, 'imgs used', len(used), 'files', len(glob.glob(OUT + '/*.json')))
noimg = [os.path.basename(f) for f in glob.glob(OUT + '/KmfStory_*.json') if not any(json.load(open(f))['img'])]
print('no image cutscenes', len(noimg))

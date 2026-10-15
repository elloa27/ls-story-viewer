import sys, os, zipfile, io, re
import UnityPy
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

OUT = '/tmp/claude-0/-home-claude/9fb202a6-a8f5-5195-ba97-f2d8ea26cb60/scratchpad/apk/app/www/data/img'
W = 1280

def conv(args):
    name, data = args
    m = re.search(r'(bg|still)[\\/](\d+)\.bundle$', name)
    if not m:
        return name, 'skip'
    kind, id_ = m.group(1), m.group(2)
    if kind == 'still':
        id_ = str(int(id_))
    dst = f'{OUT}/{kind}/{id_}.webp'
    if os.path.exists(dst):
        return name, 'exists'
    try:
        env = UnityPy.load(data)
        best = None
        for obj in env.objects:
            if obj.type.name == 'Texture2D':
                t = obj.read()
                if best is None or t.m_Width * t.m_Height > best.m_Width * best.m_Height:
                    best = t
        if best is None:
            return name, 'notex'
        im = best.image.convert('RGB')
        if im.width > W:
            im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
        im.save(dst, 'WEBP', quality=72 if kind == 'bg' else 68, method=4)
        return name, 'ok'
    except Exception as e:
        return name, f'err {e}'

def gen(z):
    for n in z.namelist():
        if n.endswith('.bundle'):
            yield n, z.read(n)

if __name__ == '__main__':
    os.makedirs(OUT + '/bg', exist_ok=True)
    os.makedirs(OUT + '/still', exist_ok=True)
    stats = {}
    with zipfile.ZipFile(sys.argv[1]) as z, ProcessPoolExecutor(os.cpu_count()) as ex:
        for name, r in ex.map(conv, gen(z), chunksize=4):
            k = r.split()[0]
            stats[k] = stats.get(k, 0) + 1
            if k in ('err', 'notex'):
                print(name, r)
    print(sys.argv[1], stats)

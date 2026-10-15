import sys, json, io, os
import UnityPy
from PIL import Image
want = json.load(open(sys.argv[1])); cd = sys.argv[2]; out = sys.argv[3]
os.makedirs(out, exist_ok=True)
ok = 0
for kid, cf, _ in want:
    try:
        env = UnityPy.load(f'{cd}/{cf}')
        for o in env.objects:
            if o.type.name == 'TextAsset':
                d = o.read(); b = d.m_Script
                if isinstance(b, str): b = b.encode('utf-8', 'surrogateescape')
                im = Image.open(io.BytesIO(bytes(b))).convert('RGBA')
                bb = im.getchannel('A').getbbox()
                if bb: im = im.crop(bb)
                im.save(f'{out}/{kid}.webp', 'WEBP', quality=80, method=4)
                ok += 1; break
            elif o.type.name == 'Texture2D':
                im = o.read().image.convert('RGBA'); bb = im.getchannel('A').getbbox()
                if bb: im = im.crop(bb)
                im.save(f'{out}/{kid}.webp', 'WEBP', quality=80, method=4); ok += 1; break
    except Exception as e:
        print(kid, e)
print(ok, len(want))

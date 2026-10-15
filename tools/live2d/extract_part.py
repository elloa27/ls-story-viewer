"""extract_part.py <unzipped dir> <ids out file> : extract all l2d models in dir/l2d"""
import sys,os,re,json
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from extract_live import extract
PK='/tmp/claude-0/-home-claude/9fb202a6-a8f5-5195-ba97-f2d8ea26cb60/scratchpad/pack/l2d'
D=sys.argv[1]+'/l2d'
def one(c):
    try:
        if os.path.exists(f'{PK}/{c}/model.model3.json'): return c,'exists'
        extract(f'{D}/{c}.bundle',f'{D}/{c}_tex.bundle',f'{PK}/{c}'); return c,'ok'
    except Exception as e: return c,f'err {e}'
if __name__=='__main__':
    ids=sorted({m.group(1) for f in (os.listdir(D) if os.path.isdir(D) else []) for m in [re.match(r'(\d+)\.bundle$',f)] if m and os.path.exists(f'{D}/{m.group(1)}_tex.bundle')})
    ok=[]
    with ProcessPoolExecutor(2) as ex:
        for c,r in ex.map(one,ids):
            if r in('ok','exists'): ok.append(c)
            else: print(c,r)
    open(sys.argv[2],'w').write('\n'.join(ok))
    print('extracted',len(ok),'of',len(ids))

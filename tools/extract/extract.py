import UnityPy,json,os,glob,collections,sys
src='story/json_assets_json/adv'; dst='json'
os.makedirs(dst,exist_ok=True); bad=0; n=0
for f in glob.glob(src+'/**/*.bundle',recursive=True):
  try:
    env=UnityPy.load(f)
    for o in env.objects:
      if o.type.name=='TextAsset':
        d=o.read(); s=d.m_Script; s=s if isinstance(s,str) else s.decode('utf-8')
        rel=os.path.relpath(f,src)[:-7]+'.json'
        os.makedirs(os.path.dirname(os.path.join(dst,rel)),exist_ok=True)
        open(os.path.join(dst,rel),'w',encoding='utf-8').write(s); n+=1
  except Exception as e: bad+=1; print('ERR',f,e)
print('ok',n,'bad',bad)

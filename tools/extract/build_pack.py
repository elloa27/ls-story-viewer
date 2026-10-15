import json,glob,os,re,collections,shutil
SRC='json'; OUT='../apk/app/www/data'
shutil.rmtree(OUT+'/ep',ignore_errors=True); os.makedirs(OUT+'/ep')
TAG=re.compile(r'</?(color|size|b|i)[^>]*>')
def clean(t): return TAG.sub('',t or '')

def bg_of(v):
  if 'add' in v:
    return [a.get('bgId') for a in v['add']]
  return None

M3=re.compile(r'^m_\d{3}$');E3=re.compile(r'^e_\d{3}$')
def cid(x):
  d=re.sub(r'\D','',str(x)); return int(d) if d else None
def compile_file(path):
  j=json.load(open(path,encoding='utf-8'))
  k=0; groups={}; first=None; ssbg=set()
  for g,cmds in j.items():
    if first is None: first=g
    out=[]
    for c in cmds:
      if not c: continue
      name,v=next(iter(c.items()))
      if not isinstance(v,dict): v={}
      if name=='serif':
        if 'text' in v:
          spk=(v.get('speaker') or {}).get('text','')
          item=['S',spk,clean(v['text']),k]
          if v.get('voiceId'): item.append(v['voiceId'])
          out.append(item); k+=1
      elif name in('narration','telop'):
        if v.get('text'): out.append(['N',clean(v['text']),k]); k+=1
      elif name=='text':
        if v.get('text'): out.append(['N',clean(v['text']),k]); k+=1
      elif name in('chapterTitle','lostPlusOneChapterTitle'):
        if v.get('text'): out.append(['T',v.get('chapterNum'),v['text'],k]); k+=1
      elif name=='advBgOperator':
        b=bg_of(v)
        if b: out.append(['B',b[-1]])
      elif name=='advBg':
        if v.get('renderSecondScreen'):
          if v.get('bgId'): out.append(['B2',v['bgId']]); ssbg.add(v.get('id'))
        elif v.get('delete') and v.get('id') in ssbg: out.append(['B2',None])
        elif v.get('bgId'): out.append(['B',v['bgId']])
      elif name=='monitorSecondScreen':
        if v.get('delete') or v.get('close'): out.append(['MS',None])
        elif v.get('open'):
          pp=v.get('pos') or {}
          out.append(['MS',v.get('type') or 'small',pp.get('x',0),pp.get('y',0)])
      elif name=='halfSecondScreen':
        if v.get('delete'): out.append(['HS',0])
        elif 'isRight' in v or v.get('pos'): out.append(['HS',1 if v.get('isRight',True) else -1])
      elif name=='still':
        if v.get('delete'): out.append(['P',None])
        elif v.get('stillId'): out.append(['P',v['stillId']])
      elif name=='goTo':
        if 'goTo' in v: out.append(['G',v['goTo']])
        elif 'heroFlag' in v: out.append(['H',v['heroFlag']['goToMale'],v['heroFlag']['goToFemale']])
      elif name=='run':
        q=v.get('queueId')
        if q in j: out.append(['R',q])
      elif name=='reminiscence':
        p=v.get('play',{})
        if p.get('storyId'): out.append(['M',p['storyId'].lower(),p.get('queueId')])
      elif name=='live2d':
        i=v.get('id')
        if v.get('lipSync') is True: out.append(['L',i])
        if v.get('delete') or (v.get('fadeOut') and not v.get('charId')): out.append(['X',i])
        else:
          c=cid(v['charId']) if v.get('charId') else None
          pos=(v.get('pos') or {}).get('positionId')
          mv=((v.get('animation') or {}).get('moveTo') or {}).get('pos',{}).get('positionId')
          pos=pos or mv
          m=e=None
          for a in (v.get('live2dAnimation') or {}).get('animation',[]) or []:
            if M3.match(str(a.get('motion',''))): m=a['motion']
            if E3.match(str(a.get('exp',''))): e=a['exp']
          ss=1 if v.get('renderSecondScreen') else (0 if c else None)
          pv=None
          if isinstance(v.get('paramValue'),list):
            pv={x['name']:x.get('value',0) for x in v['paramValue'] if isinstance(x,dict) and x.get('name')}
          if c or pos or m or e or pv: out.append(['C',i,c,pos,m,e,ss,pv])
      elif name=='moveCamera':
        pid=(v.get('pos') or {}).get('positionId')
        if pid in('MC','L','R'): out.append(['K',pid])
      elif name=='bgm':
        if 'play' in v and isinstance(v['play'],dict) and v['play'].get('fileName'): out.append(['A',v['play']['fileName'].split('/')[-1]])
        elif 'stop' in v: out.append(['A',None])
      elif name=='se':
        pl=v.get('play')
        if isinstance(pl,dict) and pl.get('cueName'):
          cn=pl['cueName'].strip()
          cn={'se_adv_Flashaback_01':'se_adv_flashback_01','kmf_170102_skilll_01':'kmf_170102_skill_01','kmf_mvs_drawn_sword_02':'kmf_mvs_drawn_sword_02_1','se_adv_1044_loop':'se_adv_1044'}.get(cn,cn)
          out.append(['E',cn])
        st=v.get('stop')
        if isinstance(st,dict) and st.get('filePath'): out.append(['Es',st['filePath'].split('/')[-1]])
      elif name in('knightmareCutScene','captionMovie','movie'):
        out.append(['V',name,v.get('path') or v.get('fileName') or v.get('movieName')])
    groups[g]=out
  return {'start':first,'groups':groups,'lines':k}

CH=json.load(open('../gloss/chapter_titles_ko.json',encoding='utf-8'))
EXTRA={'4부':['그 길이 향하는 곳','당신에게 보내는 말','저항하는 의지','부활의 여정'],'4.5':['작아도 죽음에 이르는 상처','작별 인사 대신'],
 '5부':['철벽을 꿰뚫는 달빛','스스로 고른 길','그 마음, 엇갈려서','설레는 마음','퍼져 가는 파문','어두운 밤으로 떨어지다','당신이 없는 나날','균열','양보할 수 없는 마음','종언의 아침','살아가는 의미','미지의 길']}
PARTS={'1':('1부 R1',CH['1부']),'2':('1.5부 로스트 제로',CH['1.5부']),'3':('2부 R2',CH['2부']),'4':('3부 부활의 를르슈',CH['3부']+EXTRA['4부']),
 '5':('4부 신결의 알마리아',[t.replace("PLUS '","").rstrip("'") for t in CH['4부']]+EXTRA['4.5']),'6':('5부',EXTRA['5부'])}
def label_main(key):
  m=re.match(r'main_(\d)(\d\d)(\d\d\d)_(\d+)_(\d+)',key); return m
index=collections.OrderedDict()
CATS=[('prologue','프롤로그'),('main','메인 스토리'),('storyevent','이벤트 스토리'),('akito','아키토 편'),('another','어나더'),('entangle','엔탱글'),('bondslevel','인연(본즈) 에피소드'),('gacha','가챠 스토리'),('gachanews','가챠 뉴스'),('birthday','생일'),('tutorial','튜토리얼'),('expedition','원정')]
totals=collections.Counter(); chapter_titles={}
eps_all={}
for cat,_ in CATS:
  for f in sorted(glob.glob(f'{SRC}/{cat}/*/*_command.json')):
    key=os.path.basename(f)[:-len('_command.json')]
    d=compile_file(f)
    # main chapter titles
    for g in d['groups'].values():
      for it in g:
        if it[0]=='T' and cat=='main':
          m=label_main(key); chapter_titles[(m.group(1),m.group(2))]=it[2]
    # speakers summary for labels
    sp=collections.Counter(it[1] for g in d['groups'].values() for it in g if it[0]=='S' and it[1] not in('[HERO_NAME]','','？？？'))
    d['key']=key
    json.dump(d,open(f'{OUT}/ep/{key}.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    eps_all[key]=(cat,d['lines'],[s for s,_ in sp.most_common(3)])
    totals[cat]+=d['lines']

def natkey(s): return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)',s)]
idx=[]
for cat,label in CATS:
  keys=sorted([k for k,v in eps_all.items() if v[0]==cat],key=natkey)
  keys=[k for k in keys if eps_all[k][1]>0]
  groups=collections.OrderedDict()
  for k in keys:
    lines=eps_all[k][1]; spk=eps_all[k][2]
    if cat=='main':
      m=label_main(k); s,ch,ep,part,_=m.groups()
      gk=f'{s}{ch}'; pt=PARTS.get(s,(s+'부',None)); kt=pt[1][int(ch)-1] if pt[1] and int(ch)<=len(pt[1]) else None
      gl=f'{pt[0]} · {int(ch)}장 「{kt}」' if kt else f'{pt[0]} · {int(ch)}장'+(f' 「{chapter_titles[(s,ch)]}」' if (s,ch) in chapter_titles else '')
      el=f'{int(ep)}화'+(f' ({part})' if part!='1' else '')
    elif cat=='storyevent':
      m=re.match(r'storyevent_(\d+|prologue)_?(\d+)?_?(\d+)?',k)
      if k.startswith('storyevent_prologue'): gk='prologue'; gl='이벤트 프롤로그'; el=k.split('_')[-1]
      else:
        gk=m.group(1); gl=f'이벤트 {gk}'; el=f'{int(m.group(2))}화'+(f' ({m.group(3)})' if m.group(3) not in(None,'1') else '')
    elif cat=='bondslevel':
      m=re.match(r'bondslevel_(\d)_(\d+)',k); gk=m.group(2)[:3]; gl=f'캐릭터 {gk}'; el=f'Lv.{m.group(1)} · {m.group(2)}'
    elif cat in('gacha','gachanews'):
      num=k.split('_')[-1]; gk=num[:3]; gl=f'캐릭터 {gk}' if cat=='gacha' else f'뉴스 {num[:4]}'; el=num
    elif cat=='another':
      m=re.match(r'another_(\d+)_(\d+)',k); gk=m.group(1); gl=f'어나더 {gk}'; el=f'{m.group(2)}화'
    elif cat=='entangle':
      m=re.match(r'entangle_(\d+)',k); gk=m.group(1)[:3]; gl=f'엔탱글 {gk}'; el=m.group(1)
    elif cat=='akito':
      n=k.split('_')[1]; gk=n[0]; gl=f'아키토 {gk}장'; el=f'{int(n[1:])}화'
    elif cat=='birthday':
      gk=k.split('_')[1]; gl='캐릭터 생일' if gk=='chara' else '주인공 생일'; el=k.split('_')[-1]
    else:
      gk='all'; gl=label; el=f'{sum(len(g["eps"]) for g in groups.values())+1}화'
    if gk not in groups: groups[gk]={'title':gl,'eps':[]}
    groups[gk]['eps'].append([k,el,lines,spk[:2]])
  # refine character group titles by top speaker
  KN=json.load(open(OUT+'/ko/names.json',encoding='utf-8'))
  kn=lambda x:KN.get(x,x)
  if cat=='entangle':
    ROUTE={'101':'프롤로그','102':'카렌 루트 「새벽녘의 약속」','103':'유페미아 루트 「평화로의 계단」','104':'셜리 루트 「통곡의 하늘」','105':'니나 루트 「전별의 태양」'}
    for gk,g in groups.items():
      g['title']=ROUTE.get(gk,g['title'])
      for i,e in enumerate(g['eps']): e[1]=f'{i+1}화'
  if cat in('bondslevel','gacha'):
    for gk,g in groups.items():
      c=collections.Counter(s for e in g['eps'] for s in e[3])
      if c: g['title']=kn(c.most_common(1)[0][0])
      if gk=='512': g['title']='주인공 (의상 인연)'
      g['sub']=f'캐릭터 번호 {gk}'
      if cat=='gacha':
        for i,e in enumerate(g['eps']):
          sfx=' (여주)' if e[0].endswith('_female') else (' (남주)' if e[0].endswith('_male') else '')
          e[1]=f'{i+1}편{sfx}'
      else:
        for e in g['eps']:
          m=re.match(r'bondslevel_(\d)_(\d+)(?:_(male|female))?',e[0]); sfx={'male':' (남주)','female':' (여주)'}.get(m.group(3),'')
          e[1]=f'인연 Lv.{m.group(1)} · {m.group(2)}{sfx}'
  if cat in('storyevent','another'):
    for gk,g in groups.items():
      c=collections.Counter(s for e in g['eps'] for s in e[3])
      if c and gk!='prologue': g['sub']=' · '.join(kn(x) for x,_ in c.most_common(3))
  idx.append({'id':cat,'title':label,'lines':totals[cat],'groups':list(groups.values())})
json.dump(idx,open(f'{OUT}/index.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print({c:totals[c] for c,_ in CATS}, 'chapters titled',len(chapter_titles))

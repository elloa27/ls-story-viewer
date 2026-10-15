import json,base64,struct,csv,sys
def load(path):
  j=json.load(open(path))
  ids=j['m_InternalIds']; ex=base64.b64decode(j['m_ExtraDataString']); ed=base64.b64decode(j['m_EntryDataString'])
  n=struct.unpack_from('<i',ed,0)[0]; out={}
  for k in range(n):
    iid,prov,dk,dh,di,pk,rt=struct.unpack_from('<7i',ed,4+k*28)
    if di<0: continue
    t=ex[di]; o=di+1
    if t!=7: continue
    al=ex[o]; o+=1+al; cl=ex[o]; o+=1+cl
    jl=struct.unpack_from('<i',ex,o)[0]; o+=4
    js=json.loads(ex[o:o+jl].decode('utf-16-le'))
    out[ids[iid]]=js
  return out
if __name__=='__main__':
  m=load(sys.argv[1]); print(len(m)); k=[x for x in m if 'prologue_op0030_1' in x][0]; print(k,m[k])

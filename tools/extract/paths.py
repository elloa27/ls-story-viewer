import json,sys
mp=json.load(open('ls/jsonmap.json'))
B='C:\\Users\\<USER>\\Downloads\\com.dmm.games.loststories\\files\\UnityCache\\Shared\\'
pat=sys.argv[1]
ps=[B+v[0] for k,v in sorted(mp.items()) if pat in k]
print(json.dumps(ps))

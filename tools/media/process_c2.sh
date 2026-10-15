#!/bin/bash
# usage: process_c2.sh N
B=/tmp/claude-0/-home-claude/9fb202a6-a8f5-5195-ba97-f2d8ea26cb60/scratchpad
Z=/mnt/user-data/uploads/Downloads/ls_c2_part$1.zip
for t in $(seq 120); do [ -f $Z ] && unzip -tq $Z >/dev/null 2>&1 && break; sleep 10; done
U=$B/c2u/p$1; rm -rf $U; mkdir -p $U
cd $U && unzip -q $Z && rm -f $Z
python3 - "$U" <<'PY'
import os,sys
u=sys.argv[1]
for f in os.listdir(u):
    if '\\' in f:
        p=os.path.join(u,*f.split('\\')); os.makedirs(os.path.dirname(p),exist_ok=True); os.rename(os.path.join(u,f),p)
PY
[ -d $U/snd ] && $B/conv_snd.sh $U/snd
cd $B/l2d && python3 -I extract_part.py $U ids_p$1.txt
rm -rf $U
echo PART$1DONE

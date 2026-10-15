#!/bin/bash
# usage: conv_snd.sh <snd root dir (contains Bgm/ Se/)>
V=/tmp/claude-0/-home-claude/9fb202a6-a8f5-5195-ba97-f2d8ea26cb60/scratchpad/vgmstream/build/cli/vgmstream-cli
OUT=/tmp/claude-0/-home-claude/9fb202a6-a8f5-5195-ba97-f2d8ea26cb60/scratchpad/pack/snd
T=$(mktemp -d)
mkdir -p $OUT/bgm $OUT/se
find "$1/Bgm" -name '*.awb' | while read f; do
  n=$(basename "$f" .awb); [ -f $OUT/bgm/$n.ogg ] && continue
  $V -i -o $T/b.wav "$f" >/dev/null 2>&1 && ffmpeg -nostdin -hide_banner -loglevel error -y -i $T/b.wav -c:a libopus -b:a 56k $OUT/bgm/$n.ogg
done
find "$1/Se" -name '*.acb' | while read f; do
  rm -f $T/s_*.wav
  $V -S 0 -i -o "$T/s_?n.wav" "$f" >/dev/null 2>&1
  for w in $T/s_*.wav; do [ -f "$w" ] || continue
    n=$(basename "$w" .wav); n=${n#s_}; n=$(echo "$n" | tr 'A-Z' 'a-z')
    [ -f "$OUT/se/$n.ogg" ] && continue
    ffmpeg -nostdin -hide_banner -loglevel error -y -i "$w" -c:a libopus -b:a 48k "$OUT/se/$n.ogg"
  done
done
rm -rf $T
python3 - <<PY
import os,json
o='$OUT'
json.dump({'bgm':sorted(f[:-4] for f in os.listdir(o+'/bgm')),'se':sorted(f[:-4] for f in os.listdir(o+'/se'))},open(o+'/list.json','w'))
print({k:len(os.listdir(o+'/'+k)) for k in ('bgm','se')})
PY

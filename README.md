# LS Story Viewer (비공개)

코드기어스 로스트 스토리즈(일본판) 스토리를 한국어로 읽는 안드로이드 뷰어와, 그 뷰어를 만드는 데 쓴 도구 모음입니다.

> **이 저장소에는 게임 에셋(이미지·Live2D·음악·효과음·일본어 대사 원문)이 들어 있지 않습니다.**
> 뷰어를 빌드하려면 본인 폰에 내려받은 게임 데이터에서 다시 추출해야 합니다.
> 서명 키(`ls.keystore`)도 넣지 않았습니다. 키는 PC의 `다운로드\ls_collect\ls.keystore`에 있습니다
> (비밀번호 `lsviewer`, alias `ls`). 같은 키로 서명해야 기존 설치 위에 업데이트됩니다.

## 폴더 구성

| 폴더 | 내용 |
|---|---|
| `viewer/` | 뷰어 화면(`index.html`), Live2D 표시 라이브러리(`lib/`), 목록 인덱스(`data/index.json`) |
| `android/` | 안드로이드 앱 껍데기 (apktool 형식: Manifest, smali, 아이콘) |
| `translation/ko/` | 한국어 번역 4,224화 (`<회차키>.json` = `{줄번호: 번역}`), `names.json`(화자 이름), `_list.json` |
| `glossary/` | 고유명사 용어집(311개, 나무위키 표기 기준), 한국어판 챕터 제목, 커뮤니티 검토용 시트 |
| `translator/` | 제미나이 번역기 (PC용 GUI, 표준 라이브러리만 사용). API 키는 실행할 때 입력하며 저장소에 없습니다 |
| `tools/collect/` | PC에서 게임 캐시에서 필요한 파일만 골라 zip으로 묶는 PowerShell 스크립트 |
| `tools/extract/` | Addressables 카탈로그 해석, 스토리 JSON 추출, 뷰어용 회차 데이터 생성(`build_pack.py`) |
| `tools/live2d/` | Cubism for Unity 모델 → 웹 재생용(moc3 + webp + motion3/exp3/pose3) 변환 |
| `tools/media/` | 배경/CG → webp 변환, 배경음악/효과음(CRI ACB/AWB, HCA) → ogg(opus) 변환 |
| `tools/kmf/` | 나이트메어 전투 연출: 타임라인 해석(`parse_kmf.py`), 기체 일러스트 변환(`conv_kmf.py`), 뷰어 데이터 생성(`build_kmf.py`) |

## 전체 흐름

1. **게임 데이터 확보** — 폰의 `Android/data/com.dmm.games.loststories/files`를 adb로 PC에 복사
   (`UnityCache/Shared`, `raw_data/Sound`, `com.unity.addressables`).
2. **카탈로그 해석** — `tools/extract/cat.py`로 `catalog`을 읽어 번들 경로 → 캐시 파일명(`<bundleName>_<hash>`) 매핑.
3. **필요 파일 수집** — `tools/collect/*.ps1`(PC에서 실행)로 스토리 JSON / 배경·CG / Live2D·사운드를 zip으로 묶음.
4. **추출·변환** (Linux, Python 3 + UnityPy, Pillow, ffmpeg, vgmstream-cli)
   - 스토리: `extract.py` → `build_pack.py` (→ `data/ep/*.json`, `data/index.json`)
   - 이미지: `tools/media/conv_img.py <zip>` (→ `data/img/bg`, `data/img/still`)
   - Live2D: `tools/live2d/extract_part.py` (→ `data/l2d/<charId>/`)
   - 사운드: `tools/media/conv_snd.sh <Sound 폴더>` (→ `data/snd/bgm`, `data/snd/se`)
   - 전투 연출: `knightmarestories-kmfstory_*` 번들 → `parse_kmf.py`, `kmf_<id>_l.bundle` → `conv_kmf.py`, 이어서 `build_kmf.py` (→ `data/kmf/`, `data/kmf/img/`)
     - HCA 키는 vgmstream의 `hca_keys.h`에 등록되어 있어 자동 적용됨
5. **번역** — `translator/translator.py` (배치 모드 지원). 결과 `ko/*.json`을 `data/ko/`에 둠.
6. **APK 빌드**
   ```
   cp -r viewer/* android/assets/        # + data/ (ep, ko, img, l2d, snd)
   java -jar apktool.jar b android -o unsigned.apk
   java -jar apksigner.jar sign --ks ls.keystore --ks-pass pass:lsviewer --out LS_Story_Viewer.apk unsigned.apk
   ```
   apktool 2.9.3 / apksigner는 npm `@postar/apktool-node`에 포함된 jar 사용.

스크립트 안의 경로는 작업하던 환경 기준으로 하드코딩되어 있으니, 쓰기 전에 맞게 고쳐야 합니다.

## 뷰어 회차 데이터 형식 (`build_pack.py` 출력)

`{"start": 시작그룹, "groups": {그룹: [명령...]}, "lines": 줄수, "key": 회차키}`

| 명령 | 의미 |
|---|---|
| `['S', 화자, 대사, k, voice?]` / `['N', 텍스트, k]` / `['T', 장번호, 제목, k]` | 대사 / 나레이션 / 장 제목 (`k` = 번역 키) |
| `['B', bgId]` / `['B2', bgId]` / `['P', stillId]` | 배경 / 분할화면 배경 / CG |
| `['C', id, charId, pos, motion, exp, ss, params]` / `['X', id]` / `['L', id]` | 캐릭터 표시·변경 / 퇴장 / 말하는 캐릭터 |
| `['K', MC\|L\|R]` / `['HS', 1\|-1\|0]` | 카메라 위치 / 분할화면(통신창) |
| `['A', bgm]` / `['E', se]` / `['Es', se]` | 배경음악 / 효과음 재생 / 정지 |
| `['G', 그룹]` / `['H', 남, 여]` / `['R', 큐]` / `['M', 스토리, 큐]` | 분기 / 성별 분기 / 서브루틴 / 회상 |
| `['V', 종류, 경로]` | 전투 연출(`knightmareCutScene` → `data/kmf/<경로>.json` 재생)·영상(안내 문구만) |

## 버전 기록

- v0.2.0 첫 한국어 번역판
- v0.3.0 배경·CG, 목록 제목 한글화
- v0.4.0 Live2D 캐릭터, 배경음악·효과음
- v0.4.1 카메라 이동 후 캐릭터 누락 수정, 여성 주인공, 효과음 오타 보정
- v0.4.2 분할화면(통신창), 장면별 파라미터(망토 등), 캐릭터 크기 조정
- v0.4.3 나이트메어 전투 연출 423종 (기체 일러스트 + 카메라 컷·흔들림·섬광 + 효과음 + 한국어 자막)

## 남은 작업

- 전투 연출 중 3D·이펙트·Live2D 컷인은 재현하지 않음(일러스트 근사), 일러스트가 없는 양산기·적기 39편은 배경만 표시
- 자막 영상(254종), 영상(13종)
- 빠진 캐릭터 9명(폰에 미다운로드), 주인공 인연 모델(512xxx, 게임 데이터에 없음 → 기본 모델 대체 중)
- 배포용 구조: 에셋 없는 뷰어 APK + 사용자가 자기 데이터로 만드는 추출기

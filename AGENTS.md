# 디아블로 4 (Diablo IV) 빌드 가이드 공식 한국어 현지화 및 그래픽 제작 규칙

이 워크스페이스에서 디아블로 4 빌드 가이드(D4Builds.gg, Maxroll, Wowhead 등)를 번역하거나 시각 그래픽(PNG) 및 인터랙티브 뷰어(HTML), 마크다운 가이드를 제작할 때는 **반드시 아래의 공식 한국어 현지화 원칙과 검증된 용어 사전**을 준수해야 합니다.

---

## 1. 핵심 현지화 원칙 (필수 준수)

1. **100% 블리자드 코리아 공식 인게임 명칭 사용**:
   - 영문 명칭을 임의로 직역하지 않고, 반드시 **디아블로 4 한국어 클라이언트 및 국내 공식 DB(디아블로4 인벤 DB 등)**를 교차 검증하여 실제 인게임 표기 명칭을 사용합니다.
   - 예: `Beastfall Boots` $\rightarrow$ **`야수내림 장화`** (`야수추락 장화` X), `Tricks of the Trade` $\rightarrow$ **`영업 비밀`** (`거래의 기술` X), `Assassin` 문양 $\rightarrow$ **`종결자`** (`암살자` X), `Devious` 문양 $\rightarrow$ **`간악함`** (`교활` X), `Chip` 문양 $\rightarrow$ **`부스러기`** (`깎아내기` X).
2. **영문 약어 및 미번역 텍스트 완전 배제**:
   - 그래픽 이미지와 HTML 툴팁에 영문 약어가 남지 않도록 순수 한국어 표기로 통일합니다.
   - `[GA]` (Greater Affix) $\rightarrow$ **`★ [상급]`** (상급 어픽스)
   - `15 / 15 pt` $\rightarrow$ **`15 / 15`** 또는 **`83 포인트`**
   - `Lv.100` $\rightarrow$ **`100레벨`**
   - 정복자 보드 21×21 격자 표기: `G`, `L`, `R`, `M` $\rightarrow$ **`문`(문양 홈), `전`(전설 노드), `희`(희귀 노드), `마`(마법 노드)**
   - 인터랙티브 HTML 뷰어의 정복자 보드 타일 툴팁(미선택 노드 포함 전체)은 노드 분류(`[일반 노드]`, `[마법 노드]`, `[희귀 노드: ...]`, `[전설 노드: ...]`, `[정복자 문양 홈]`)와 모든 스탯 옵션을 **100% 한국어**로 변환하여 출력합니다.
3. **그래픽 레이아웃 및 가독성 규칙**:
   - Pillow(`PIL`)로 그래픽 생성 시 긴 설명문은 글자 수 단순 자르기(`eff[:36]`)를 금지하며, 반드시 **공백(단어) 단위 픽셀 너비 계산 함수(`wrap_korean_by_width`)**를 사용해 단어나 괄호 수치가 중간에 끊기지 않게 줄바꿈합니다.
   - `NotoSansCJK` 폰트에서 글리프 누락(`☒`)이 발생하는 컬러 이모지(`⚡`, `💡` 등) 대신 **`★`, `◆`, `▶`, `●`, `①~⑦`** 기호를 사용합니다.
   - 정복자 보드 21×21 격자는 각 보드의 회전 각도(`0°`, `90°`, `180°`, `270°`)를 좌표 변환 함수(`rot_rc`)로 실제 적용하여, 인게임 화면에서 보이는 방향 그대로 렌더링합니다.

---

## 2. 디아블로 4 공식 한국어 용어 사전 (교차 검증 완료)

### A. 직업 전문화 · 기술 · 상태 효과 · 태그 (도적 기준 및 공통)
| 영문 원문 | 공식 한국어 명칭 | 오역 주의 (사용 금지) | 비고 |
| :--- | :--- | :--- | :--- |
| `Preparation` | **전투 준비** | 준비 | 도적 직업 전문화 |
| `Combo Points` | **연계 점수** | 콤보 포인트 | 도적 직업 전문화 |
| `Inner Sight` | **내면의 시야** | 내면의 눈 | 도적 직업 전문화 |
| `Marksman` | **명사수** | 사격 | 도적 원거리 기술 태그 |
| `Cutthroat` | **단검** | 목긋기 / 자객 | 도적 근거리 기술 태그 |
| `Subterfuge` | **기만** | 속임수 | 도적 기술 범주 |
| `Agility` | **날렵함** | 민첩성 | 도적 기술 범주 |
| `Imbuement` | **주입** | 부여 | 도적 기술 범주 |
| `Ultimate` | **궁극기** | 궁극 | 기술 범주 |
| `Concealment` | **은폐** | 은신 (스킬명 기준) | 스킬명은 **은폐**, 버프 상태가 **은신(Stealth)** |
| `Countering Concealment` | **역습하는 은폐** | 역습하는 은신 | `네르(Ner)` 룬 등으로 발동하는 은폐 강화 |
| `Dark Shroud` | **어둠의 장막** | 다크 슈라우드 | 기만 기술 |
| `Cold Imbuement` | **냉기 주입** | 한기 주입 | 주입 기술 |
| `Poison Imbuement` | **독 주입** | 맹독 주입 | 주입 기술 |
| `Shadow Imbuement` | **암흑 주입** | 그림자 주입 | 주입 기술 |
| `Rain of Arrows` | **화살비** | 화살 세례 | 도적 궁극기 |
| `Ferocity` | **포악함** | 맹렬 / 사나움 | 중첩형 버프 효과 |
| `Resolve` | **결의** | 결단 | 피해 감소 중첩 효과 |
| `Vulnerable` | **취약** | 약화 | 상태 이상 |
| `Unstoppable` | **저지 불가** | 막을 수 없음 | 상태 효과 |
| `Overpower` | **제압** | 압도 | 공격 판정 |
| `Evade` | **피하기** | 회피 (스킬명 기준) | 기본 스페이스바 이동기 (스탯 회피 확률은 `회피 확률`) |

### B. 고유/신화 아이템 · 위상 · 담금질 조리법 · 룬어 · 탈리스만/부적
| 분류 | 영문 원문 | 공식 한국어 명칭 | 오역 주의 / 상세 |
| :---: | :--- | :--- | :--- |
| **고유/신화** | `Leoric's Crown` | **레오릭의 왕관** | 투구 |
| **고유/신화** | `Gladiator's Triumph` | **검투사의 승리** | 장갑 (명사수 기술 극대화 시너지) |
| **고유/신화** | `Tibault's Will` | **티볼트의 의지** | 바지 |
| **고유/신화** | `Beastfall Boots` | **야수내림 장화** | `야수추락 장화` (X) |
| **고유/신화** | `Melted Heart of Selig` | **셀리그의 녹아내린 심장** | 신화 고유 목걸이 |
| **전설 위상** | `Earthstriker's Aspect` | **대지격퇴자의 위상** | `대지강타자의 위상` (X) |
| **전설 위상** | `Ferocious Aspect` | **포악한 위상** | `사나운 위상` (X) — 최대 **포악함** 중첩 증가 |
| **전설 위상** | `Aspect of Aftermath` | **여파의 위상** | 궁극기 등급당 기력 회복 |
| **전설 위상** | `Aspect of Inner Calm` | **내면의 고요의 위상** | 가만히 서 있을 때 피해 증가 |
| **담금질** | `Worldly Endurance` | **속세의 인내** | `세속적 인내` (X) |
| **담금질** | `Worldly Finesse` | **속세의 기교** | `세속적 기교` (X) |
| **담금질** | `Worldly Stability` | **속세의 안정성** | `세속적 안정성` (X) |
| **담금질** | `Natural Motion` | **타고난 움직임** | `자연스러운 움직임` (X) — 피하기 재사용 대기시간 감소 |
| **룬** | `Mal` / `Ner` / `Zan` / `Mot` / `Poc` / `Vex` / `Lac` | **말 / 네르 / 잔 / 못 / 포크 / 벡스 / 라크 룬** | 한글 음차 표기 필수 |
| **룬어** | `Enigma (JahIthBer)` | **수수께끼 (자 + 아이드 + 베르)** | 피하기가 원소술사의 순간이동으로 변경 |
| **룬어** | `Insight (RalTirTalSol)` | **통찰 (랄 + 티르 + 탈 + 솔)** | 양손 원거리/미늘창 룬어 |
| **룬어** | `Spirit (TalThulOrtAmn)` | **영혼 (탈 + 주울 + 오르트 + 앰)** | 한손 무기 룬어 |
| **영혼석 파편** | `Splinter of Pain` | **고통의 파편** | 피해 감소 25%, 이동 속도 -30% |
| **영혼석 파편** | `Splinter of Anguish` | **고뇌의 파편** | 극확/공속 +20%, 자원 소모량 +30% |
| **영혼석 파편** | `Splinter of the Black Soulstone` | **검은 영혼석의 파편** | 영혼당 피해 x2.5% (최대 200중첩) |
| **인장/부적** | `Signet of Pelghain` | **펠가인의 인장** | 세트 보너스 요구 부적 수 -1 감소 |
| **인장/부적** | `Legacy of the Sightless` | **눈먼 자의 유산** | `보이지 않는 자의 유산` (X) — `눈먼 자의 페르/믈로르/포바` |
| **인장/부적** | `Scoundrel's Kiss` | **건달의 입맞춤** | 포악함 획득 및 명사수 피해 증폭 |
| **인장/부적** | `Endurant Faith` | **인내하는 신앙** | 피해 분산 및 피해 감소 |
| **인장/부적** | `Fists of Fate` | **운명의 주먹** | 고유 부적 (무작위 1%~[250~300%] 피해) |
| **인장/부적** | `Hellfire Torch` | **지옥불 횃불** | 신화 부적 (세트 부적 카운트 +1) |

### C. 용병 및 대악마의 힘
| 영문 원문 | 공식 한국어 명칭 | 주요 기술 공식 명칭 |
| :--- | :--- | :--- |
| `Subo, The Drunken Archer` | **현상금 사냥꾼 수보** (주정뱅이 궁수 수보) | `Seeker` (**추적자**), `Wire Trap` (**철사 덫**), `Piercing Arrows` (**관통 화살**), `Cover Fire` (**엄호 사격**), `Opening Fire` (**개전의 신호탄** / 선제 사격) |
| `Aldkin, The Cursed Child` | **저주받은 아이 알드킨** | `Field of Languish` (**쇠약장** — `쇠약의 들판` X) |
| `Raheir, The Shieldbearer` | **방패지기 라헤어** | `Bastion` (**보루**), `Crater` (**분화구**) |
| `Varyana, The Berserker Crone` | **광전사 노파 바랴나** | `Bloodthirst` (**피의 갈증**), `Harpoon` (**작살**) |
| `Ghosts of Odium` | **증오의 유령** | 시즌 15 메피스토 대악마의 힘 |

### D. 도적 정복자 보드 · 문양 · 희귀 노드 · 스탯 효과 공식 명칭
* **8대 도적 정복자 보드 (전설 노드)**:
  * `Starting Board` (**시작 보드**)
  * `Exploit Weakness` (**약점 노출**)
  * `Cheap Shot` (**비열한 습격**)
  * `No Witnesses` (**목격자 제거**)
  * `Tricks of the Trade` (**영업 비밀** — `거래의 기술` X)
  * `Eldritch Bounty` (**소름돋는 전리품**)
  * `Deadly Ambush` (**치명적인 매복**)
  * `Leyrana's Instinct` (**레이라나의 본능**)
  * `Cunning Stratagem` (**교활한 책략**)
* **도적 주요 정복자 문양 (Glyphs)**:
  * `Versatility` (**다재다능**), `Combat` (**전투**), `Assassin` (**종결자**), `Devious` (**간악함**), `Chip` (**부스러기**), `Exploit` (**착취**), `Control` (**통제**), `Canny` (**영리함**), `Fluidity` (**유연성**), `Closer` (**마무리꾼**), `Ambush` (**매복**), `Ranger` (**순찰자**), `Turf` (**세력권**), `Pride` (**긍지**).
* **도적 정복자 희귀 노드 (Rare Nodes)**:
  * `Prime` (**으뜸**), `Skillful` (**숙련됨**), `Outlaw` (**무법자**), `Resilience` (**회복력**), `Exploit` (**착취**), `Artifice` (**교묘함**), `Misery` (**비참**), `Unassailable` (**난공불락**), `Defensive Stance` (**방어 태세**), `Toughened` (**단련됨**), `Calculated` (**계산된**), `Devious` (**간악함**), `Deliverance` (**구원**), `Culler` (**도살자**), `Fleeting` (**순간적**), `Surgical` (**외과적 수술**), `Focused` (**집중**), `Ranger` (**순찰자**), `Brawler` (**싸움꾼**), `Deviant` (**일탈**), `Haven` (**피난처**), `Recuperate` (**회복**), `Safeguard` (**보호**), `Shrouded` (**장막**), `Spearhead` (**선봉**), `Training` (**훈련**), `Potent` (**강력**), `Concoction` (**혼합물**), `Imbuer` (**주입가**), `Ready Supply` (**준비된 보급품**), `Restorative` (**회복**), `Suffused Resilience` (**스며든 회복력**).
* **정복자 일반/마법/희귀 노드 스탯 표기 표준**:
  * `Dexterity` (**민첩**), `Strength` (**힘**), `Intelligence` (**지능**), `Willpower` (**의지력**)
  * `Damage` (**피해**), `Damage to Elites` (**정예에게 주는 피해**), `Vulnerable Damage` (**취약 피해**), `Damage to Crowd Controlled Enemies` (**군중 제어 상태인 적에게 주는 피해**), `Ultimate Damage` (**궁극기 피해**), `Damage to Distant Enemies` (**원거리의 적에게 주는 피해**), `Damage to Close Enemies` (**근거리의 적에게 주는 피해**), `Damage to Healthy Enemies` (**건강 상태인 적에게 주는 피해**), `Marksman Damage` (**명사수 기술 피해**), `Cutthroat Damage` (**단검 기술 피해**), `Non-Physical Damage` (**비물리 피해**)
  * `Maximum Life` (**최대 생명력**), `Total Armor` (**총 방어도**), `Resistance to All Elements` (**모든 원소 저항**), `Lucky Hit Chance` (**행운의 적중 확률**), `Attack Speed` (**공격 속도**), `Dodge Chance` (**회피 확률**), `Impairment Reduction` (**방해 효과 감소**), `Life per 5 Seconds` (**5초당 생명력 회복**)

### E. 시즌 15 전쟁 계획 (War Plans) 7대 엔드게임 콘텐츠 공식 명칭
1. `Whispers` $\rightarrow$ **속삭임의 나무**
2. `Undercity` $\rightarrow$ **쿠라스트 지하도시**
3. `Nightmare Dungeons` $\rightarrow$ **악몽 던전**
4. `Pits` / `The Pit` $\rightarrow$ **명공의 나락**
5. `Boss Lairs` $\rightarrow$ **소굴 우두머리**
6. `Infernal Hordes` $\rightarrow$ **지옥불 군세**
7. `Helltides` $\rightarrow$ **지옥물결**

---

## 3. 신규 빌드 가이드 요청 시 표준 작업 절차 (Workflow)

사용자가 다른 디아블로 4 빌드 URL(예: `https://d4builds.gg/builds/...`)에 대해 한국어 번역 및 그래픽 가이드를 요청할 경우 다음 절차를 자동으로 수행합니다:

1. **원본 데이터 추출 및 복호화**:
   - 페이지의 `page-data.json`에서 `seoId`를 확인한 뒤 Firestore 문서(`https://firestore.googleapis.com/v1/projects/d4builds-prod/databases/(default)/documents/builds/<seoId>`)를 가져와 선택된 변형(`?var=N`)의 전체 데이터를 추출합니다.
   - `d4builds.gg`의 AES 암호화된 정적 DB(`skills`, `uniques`, `codexes`, `paragons`, `skill-trees`, `paragon-boards`, `paragon-glyphs`, `tempering-stats`, `charms`, `charm-sets`, `skilltree-*`)를 복호화하여 ID를 실제 옵션과 매핑합니다.
2. **공식 한국어 용어 전수 조사 및 매핑**:
   - 본 `AGENTS.md`의 공식 용어 사전을 기본 적용하고, 새로운 직업/스킬/아이템/문양/희귀 노드가 등장할 경우 **반드시 국내 공식 디아블로 4 DB(인벤 DB, 블리자드 코리아 공식 패치노트 등)를 먼저 검색하여 정확한 한국어 클라이언트 명칭을 확인**합니다.
3. **고해상도 한국어 그래픽 4종 + 인터랙티브 HTML 뷰어 + 마크다운 아티팩트 생성**:
   - `1_gear_and_charms_kr.png`: 장비 · 보석/룬/영혼석 · 어픽스(`[상급]`/`[명품화]`) · 탈리스만/부적 및 작동 기준치 요약
   - `2_skills_and_merc_kr.png`: 장착 스킬 바 · 직업 전문화 · 시즌 권능 · 스킬 트리 · 용병 및 증원군
   - `3_paragon_boards_kr.png`: 회전 각도가 실제 반영된 21×21 정복자 보드 격자(`문`/`전`/`희`) 및 전체 보드 배치도
   - `4_war_plans_kr.png`: 전쟁 계획 7대 엔드게임 콘텐츠 트리
   - `<build_name>_kr.html`: 4종의 그래픽 탭과 함께 **모든 정복자 보드 타일 툴팁이 100% 한국어로 표시되는 인터랙티브 HTML 뷰어**

---

## 4. 매크로 및 시스템 개발 핵심 원칙: "보고 전 무조건 자동 검증 완료" (필수 불변 수칙)

사용자의 특별한 지시가 없더라도, **모든 코드 수정이나 기능 변경 후 사용자에게 보고 또는 마무리를 전달하기 전에 반드시 아래 절차를 자동으로 수행**해야 합니다:

1. **실제 단위 검증 스크립트 작성 및 100% 통과 확인**:
   - 코드 문법(Syntax) 검증에 그치지 않고, 수정된 로직이 실제 시뮬레이션 환경(키 누름, 뗌, 지연시간, 큐 누적 여부, 반응 속도 등)에서 정상 작동하는지 테스트 스크립트를 직접 실행하여 검증합니다.
2. **반응 속도(Latency) 및 큐 누적(Buffer Bloat) 실측**:
   - 특히 입력 매크로(스킬 연타, 매크로 1, 매크로 2 등)의 경우, 손을 떼거나 정지 명령을 내렸을 때 잔여 이벤트가 남지 않고 즉각(수 ms 이내) 종료되는지 실측 수치를 확인합니다.
3. **독립 실행 바이너리(`diablo4-macro`) 재빌드 및 배포 완료**:
   - 검증 통과 후 즉시 최신 바이너리를 재빌드하여 실제 실행 가능한 상태로 배포합니다.
4. **결과 보고 시 검증 데이터 및 수치 제시**:
   - 사용자에게 완료 보고 시 단순 "수정했습니다"가 아니라, 실제 검증된 수치(정지 반응 시간, 초당 사이클, 누적 이벤트 0건 확인 등)를 명확히 제시합니다.

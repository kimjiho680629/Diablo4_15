---
name: d4-korean-build-guide
description: >-
  디아블로 4 빌드 가이드(D4Builds.gg 등)를 블리자드 코리아 공식 인게임 한국어 명칭으로 100% 현지화하여
  고해상도 그래픽 시트 4종(장비/부적, 스킬/용병, 21x21 회전 정복자 보드, 전쟁 계획)과
  인터랙티브 한국어 HTML 뷰어 및 상세 가이드를 제작하는 스킬입니다.
---

# 디아블로 4 공식 한국어 빌드 가이드 & 그래픽 생성 워크플로우

사용자가 디아블로 4 빌드 URL(예: `https://d4builds.gg/builds/...`)의 한국어 번역 및 시각 가이드를 요청할 때 이 스킬을 활성화하여 수행합니다.

## 1. 필수 준수 사항
- 루트 디렉토리의 [AGENTS.md](file:///mnt/Data1/Gemini_Job/Diablo4_15/AGENTS.md)에 정의된 **디아블로 4 공식 한국어 용어 사전**과 **현지화 원칙**을 100% 준수합니다.
- 사전에 없는 신규 스킬/아이템/문양/정복자 노드가 등장하면 **반드시 국내 공식 DB(디아블로4 인벤 DB, 블리자드 코리아 공식 자료)를 검색하여 정확한 인게임 한국어 명칭을 확인한 뒤** 적용합니다. (임의 직역 절대 금지)
- 이미지 내 모든 영문 약어(`[GA]`, `pt`, `Lv.`, 정복자 격자의 `G/L/R/M`)는 순수 한국어(`★ [상급]`, `포인트`, `100레벨`, `문/전/희/마`)로 표기합니다.
- Pillow(`PIL`) 텍스트 렌더링 시 반드시 공백(단어) 단위 픽셀 너비 계산 함수(`wrap_korean_by_width`)를 사용하여 단어나 괄호 수치가 중간에 잘리지 않게 줄바꿈합니다.
- 인터랙티브 HTML 뷰어 생성 시 정복자 보드의 모든 타일(미선택 타일 포함 700여 개 전체) 툴팁에 영문이 남지 않도록 100% 한국어로 변환합니다.

## 2. D4Builds.gg 데이터 추출 및 복호화 방법
1. `https://d4builds.gg/page-data/builds/<build-slug>/page-data.json`에서 `seoId`를 추출합니다.
2. Firestore REST API(`https://firestore.googleapis.com/v1/projects/d4builds-prod/databases/(default)/documents/builds/<seoId>`)에서 전체 빌드 JSON을 다운로드하고, URL의 `?var=N` 파라미터(0-indexed: `var=4`는 `variants[3]`)에 해당하는 변형 데이터를 파싱합니다.
3. `d4builds.gg`의 웹팩 번들 내 AES 복호화 키를 사용하여 정적 DB(`skills-ptr.json`, `uniques-ptr.json`, `codexes-ptr.json`, `paragons-ptr.json`, `skill-trees-ptr.json`, `paragon-boards-ptr.json`, `paragon-glyphs-ptr.json`, `tempering-stats-ptr.json`, `charms-ptr.json`, `charm-sets-ptr.json`, `skilltree-*-ptr.json`)를 복호화합니다.

## 3. 정복자 보드 21×21 회전 좌표 변환 공식
각 보드의 `rotation` 값(`deg`)에 따라 원본 `(row, col)` (1~21) 좌표를 인게임 화면 좌표 `(rr, cc)`로 변환합니다:
```python
def rot_rc(r, c, deg):
    deg = deg % 360
    if deg == 0:
        return r, c
    elif deg == 90:
        return c, 22 - r
    elif deg == 180:
        return 22 - r, 22 - c
    elif deg == 270:
        return 22 - c, r
    return r, c
```

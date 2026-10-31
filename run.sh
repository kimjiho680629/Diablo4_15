#!/usr/bin/env bash
# 디아블로 4 매크로 실행 스크립트 (Kitty 터미널 창을 띄워 실행)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kitty --title "디아블로4 스킬 매크로" bash -c "$DIR/d4_macro; echo ''; read -p '엔터를 누르면 창이 닫힙니다...'"

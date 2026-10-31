#!/usr/bin/env bash
# 디아블로 IV PyQt6 통합 매크로 리눅스 실행 스크립트
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "⚔️ 디아블로 IV PyQt6 통합 매크로를 실행합니다..."
python3 d4_macro_qt.py "$@"

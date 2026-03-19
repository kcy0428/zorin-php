# LAMP Stack IoT 실시간 모니터링 시스템

> 캡스톤 디자인 / 임베디드 리눅스 3주차 과제

VMware 위의 Zorin OS에 LAMP 스택을 구성하고, 가상 IoT 센서 데이터를 생성·저장·시각화하는 실시간 모니터링 웹 시스템입니다.

---

## 시스템 구성

| 계층 | 기술 |
|------|------|
| 게스트 OS | Zorin OS (Ubuntu 24.04) on VMware |
| 웹 서버 | Apache 2.4 |
| 데이터베이스 | MySQL 8.0 |
| 서버 언어 | PHP 8.3 |
| 데이터 생성 | Python 3.12 + uv |

## 주요 파일

| 파일 | 설명 |
|------|------|
| `injector.py` | 가상 IoT 센서 데이터 생성기 (2초 간격 MySQL INSERT) |
| `monitor.php` | 실시간 모니터링 대시보드 |
| `monitor_api.php` | JSON REST API |
| `process.md` | 전체 구현 과정 및 시스템 블록도 |
| `project.md` | 프로젝트 계획서 |

## 실행 방법

```bash
# 1. 가상환경 세팅
uv venv && uv sync

# 2. 데이터 생성기 실행
uv run python3 injector.py

# 3. 브라우저에서 접속
http://localhost/shop/monitor.php
```

## 모니터링 기능

- 5개 가상 장치(DEV-001 ~ DEV-005) 실시간 상태 카드
- 정상 / 경고 / 위험 상태 색상 구분
- 온도·습도·CPU·메모리 시계열 차트 (Chart.js)
- 경보 로그 테이블
- 2초마다 자동 갱신

## 상세 문서

전체 구현 과정 및 Mermaid 시스템 블록도 → [process.md](process.md)

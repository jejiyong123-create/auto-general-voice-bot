# Koyeb 배포 자동화 안내

1. 시크릿 준비 (GitHub 저장소 설정)
   - `Settings` → `Secrets and variables` → `Actions`에서 다음 시크릿을 추가하세요:
     - `KOYEB_API_TOKEN`: Koyeb CLI/API 토큰
     - `KOYEB_APP`: Koyeb 앱 이름
     - `KOYEB_SERVICE`: Koyeb 서비스 이름
   - `DISCORD_TOKEN`은 Koyeb 앱의 환경변수(Secrets)로 추가하세요. 이 토큰은 저장소 시크릿으로도 관리 가능합니다.
   - (선택) Slack 실패 알림을 사용하려면 Slack에서 Incoming Webhook을 생성하고 `SLACK_WEBHOOK`이라는 이름으로 시크릿에 추가하세요.

2. 워크플로 동작
   - `.github/workflows/deploy-to-koyeb.yml` 파일은 `main` 브랜치로의 푸시 시 다음을 수행합니다:
     - 이미지를 빌드하고 `ghcr.io/${{ github.repository_owner }}/discord-bot:latest`로 푸시
     - Koyeb CLI로 로그인 후 해당 앱의 서비스를 업데이트하거나(없으면 생성) 배포

3. 주의사항
   - GHCR의 프라이빗 이미지를 Koyeb에서 직접 pull하려면 Koyeb에서의 인증 설정이 필요하거나 이미지를 공개로 설정하세요.
   - 커밋에 포함된 토큰은 즉시 폐기하세요(토큰 재발급).

4. 토큰 회수(로컬 가이드)
   - Git 기록에서 민감정보를 제거하려면 `git filter-repo` 또는 `BFG`를 사용하세요. 예 (BFG):

```bash
# 저장소 백업 후 실행
# java -jar bfg.jar --delete-files .env
# git reflog expire --expire=now --all && git gc --prune=now --aggressive
# 강제 푸시
# git push --force
```

5. 추가 도움
   - 원하시면 제가 워크플로를 조금 더 견고하게(태그 관리, SHA 태그 추가, 실패 알림 등) 개선해 드리겠습니다.

6. Slack 설정 예시
   - Slack 앱에서 Incoming Webhooks을 활성화하고 Webhook URL을 생성합니다.
   - 생성된 Webhook URL을 GitHub 저장소의 `Settings` → `Secrets and variables` → `Actions`에 `SLACK_WEBHOOK`으로 추가하세요.
   - 워크플로에서 배포 실패 시 자동으로 Slack 채널에 메시지가 전송됩니다.
# Bank Statement Normalizer (GitHub-only)

## Как пользоваться
1. Откройте страницу: `https://globalsynergycom.github.io/Bank_Statement/`.
2. Загрузите выписку (`.xlsx`, `.xls` или `.csv`) через форму — файл попадёт в `/inbox`.
3. Подождите 10–60 сек: GitHub Actions создаст `outbox/normalized_<file>.csv`, исходник переедет в `/archive/<timestamp>_<file>`.

## Интеграция с n8n
- Public repo: читайте `https://raw.githubusercontent.com/globalsynergycom/Bank_Statement/main/outbox/<file>.csv`
- Private repo: тот же URL + заголовок  
  `Authorization: Bearer <PAT with repo:contents read>`

## Технические детали
- Страница формы в `docs/index.html` (GitHub Pages: Settings → Pages → main /docs).
- Воркер Cloudflare (серверless) принимает файл и кладёт в `/inbox` через GitHub Contents API.
- Workflow `.github/workflows/normalize.yml` нормализует данные `normalizer/normalize.py`.
- Ограничение GitHub: файлы до ~25–50 МБ.

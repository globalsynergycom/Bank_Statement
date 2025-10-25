# Bank Statement Normalizer (GitHub-only)

Как пользоваться:
1) Загрузите выписку (.xlsx или .csv) в папку `/inbox`.
2) Подождите 10–40 секунд: в `/outbox` появится `normalized_<имя>.csv`, а исходник переедет в `/archive`.
3) Подключите n8n к `/outbox` (см. ниже).

## n8n
- **Public repo**: читайте `https://raw.githubusercontent.com/<owner>/<repo>/main/outbox/normalized_*.csv`
- **Private repo**: используйте GitHub API с PAT:

  - GET список файлов:  
    `GET https://api.github.com/repos/<owner>/<repo>/contents/outbox`
  - Скачать файл (raw):  
    `GET https://raw.githubusercontent.com/<owner>/<repo>/main/outbox/<file>.csv`  
    c заголовком `Authorization: Bearer <PAT>`

## Ограничения
- Файлы в Git лучше до ~25 МБ. Крупные выгрузки → разбить или включить Git LFS.
- Обработка запускается на push в `/inbox/**`. При необходимости добавьте ручной dispatch.

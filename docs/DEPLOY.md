# Deploy

Найпростіший шлях для MVP - Docker Compose на VPS.

## 1. Підготувати `.env`

Створи `.env` на основі `.env.production.example`:

```text
SESSION_SECRET=довгий_випадковий_рядок
DATABASE_URL=sqlite:////data/learning_mvp.db

AI_PROVIDER=gemini
AI_FALLBACK_TO_MOCK=false
GEMINI_API_KEY=твій_gemini_ключ
GEMINI_MODEL=gemini-2.5-flash
```

## 2. Запустити

```bash
docker compose up --build -d
```

## 3. Перевірити

```text
http://your-server-ip:8000/api/health
```

## 4. Дані

SQLite база живе у Docker volume `learning_data`. При перестворенні контейнера дані не зникають.

## 5. Google OAuth

Для локального MVP можна користуватися демо-входом. Для production потрібно додати:

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

І в Google Cloud Console додати redirect URI:

```text
https://your-domain/auth/google/callback
```

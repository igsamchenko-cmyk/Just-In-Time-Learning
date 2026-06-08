# Gemini Provider

Gemini підключається через REST `generateContent` API.

1. Створи файл `.env` у корені проєкту.

2. Додай:

```text
AI_PROVIDER=gemini
AI_FALLBACK_TO_MOCK=true
GEMINI_API_KEY=твій_ключ_з_Google_AI_Studio
GEMINI_MODEL=gemini-3.5-flash
```

3. Перезапусти застосунок:

```powershell
.\run.ps1
```

4. Перевір статус:

```text
http://127.0.0.1:8000/api/health
```

Очікувано:

```json
{
  "configured_provider": "gemini",
  "active_provider": "gemini",
  "gemini_configured": true
}
```

Якщо ключ не заданий і `AI_FALLBACK_TO_MOCK=true`, застосунок продовжить працювати через `MockProvider`.

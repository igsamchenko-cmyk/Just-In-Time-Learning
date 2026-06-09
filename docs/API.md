# API MVP

Усі API-маршрути використовують session-cookie після входу через Google або демо-входу.

## Користувач

```http
GET /api/health
```

Повертає стан застосунку та активний AI provider.

```http
GET /api/me
```

Повертає поточного користувача.

## Курси

```http
GET /api/courses
```

Повертає список курсів поточного користувача.

```http
POST /api/courses
Content-Type: application/json

{
  "goal": "Хочу навчитися швидко робити презентації для роботи",
  "notes": "Вмію користуватися PowerPoint, але погано структурую думки"
}
```

Створює курс. Якщо запит нечіткий, курс матиме статус `needs_clarification`.

```http
GET /api/courses/{course_id}
```

Повертає курс, модулі та уточнювальні питання.

```http
DELETE /api/courses/{course_id}
```

Видаляє курс поточного користувача.

```http
GET /api/courses/{course_id}/export.md
```

Експортує курс, матеріали модулів, завдання та фідбек у Markdown.

```http
POST /api/courses/{course_id}/clarifications
Content-Type: application/json

{
  "answers": [
    "Хочу вміти робити робочі презентації за 30 хвилин",
    "Маю базовий рівень",
    "Можу вчитися 20 хвилин на день"
  ]
}
```

Зберігає відповіді на уточнення і генерує план курсу.

## Модулі

```http
GET /api/courses/{course_id}/modules/{module_id}
```

Відкриває модуль. Якщо контент ще не створений, генерує його через AI provider.

```http
POST /api/courses/{course_id}/modules/{module_id}/attempts
Content-Type: application/json

{
  "answer": "Я спочатку визначу головний результат модуля, бо це звузить тему, і перевірю себе через короткий список критеріїв."
}
```

Перевіряє відповідь і повертає навчальний фідбек.

```http
POST /api/courses/{course_id}/modules/{module_id}/continue
```

Дозволяє продовжити після пояснення, якщо користувач зробив кілька невдалих спроб.

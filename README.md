# LinguaBeat

Веб-платформа для изучения русского языка как иностранного (РКИ) через лицензированную музыку и алгоритм интервального повторения FSRS-5.

Первый рынок: иностранные студенты российских вузов (РУДН, СПбГУ и др.).
Бизнес-модель: freemium, 250 руб./мес. за полный доступ.

---

## Быстрый старт

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
# → http://localhost:8000/health
# → http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Docker Compose
```bash
cp .env.example .env
docker compose up --build
```

---

## Структура проекта

```
linguabeat/
├── backend/          # FastAPI + Python 3.11 + SQLAlchemy 2.0
│   ├── app/
│   │   ├── api/v1/   # Роутеры: auth, tracks, words, srs, progress
│   │   ├── models/   # SQLAlchemy ORM (User, Track, UserWord, ...)
│   │   ├── schemas/  # Pydantic v2 схемы
│   │   ├── services/ # Бизнес-логика
│   │   ├── core/     # Config, Security, Database
│   │   └── domain/   # core_srs.py — FSRS-5, stdlib only
│   └── tests/
├── frontend/         # React 18 + TypeScript + Vite + TailwindCSS
│   └── src/
│       ├── pages/    # LibraryPage, PlayerPage, ReviewPage, ...
│       ├── components/ # Player, SubtitleLine, SRSCard, ProgressChart
│       ├── hooks/    # useAuth, usePlayer, useSRS
│       └── api/      # Типизированный HTTP-клиент
├── docs/
│   └── ARCHITECTURE.md
└── docker-compose.yml
```

---

## API

Документация: `http://localhost:8000/docs` (Swagger UI)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Вход (JWT) |
| GET | `/api/v1/tracks` | Библиотека треков |
| POST | `/api/v1/words` | Добавить слово из субтитра |
| GET | `/api/v1/srs/due` | Карточки к повторению |
| POST | `/api/v1/srs/review` | Оценить повторение (FSRS-5) |
| GET | `/api/v1/progress` | Прогресс пользователя |

---

## Технологии

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 15, Redis, JWT
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **SRS-ядро**: FSRS-5 (−25% повторений при том же 90% retention), реализован в `backend/app/domain/core_srs.py`
- **Деплой**: Docker Compose, Nginx (reverse proxy + TLS)

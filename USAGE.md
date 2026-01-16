# Quick Start

## 1. Сборка

```bash
gradle shadowJar
```

## 2. Подготовка

### GitHub Token
1. Перейди на https://github.com/settings/tokens
2. Создай token (Classic) с scope `repo`
3. Сохрани токен

### VPS
- SSH доступ (порт 22)
- Пользователь с sudo или root

## 3. Запуск

```bash
java -jar build/libs/project-starter-1.0.0-all.jar create
```

## 4. Ответы на вопросы

```
Название проекта:          My Awesome App
Описание:                  My first Kotlin MVP
VPS хост:                  192.168.1.100
VPS пользователь:          root
VPS пароль:                [ввод пароля]
GitHub token:              [ввод токена]
```

## 5. Результат

- ✅ GitHub репозиторий создан
- ✅ Ktor проект сгенерирован
- ✅ VPS настроен (Docker + SSH)
- ✅ GitHub Actions задеплоен

**Через 2-3 минуты проект доступен на `http://ваш-vps-ip`**

---

**Всё!** CLI сделает всё остальное автоматически.

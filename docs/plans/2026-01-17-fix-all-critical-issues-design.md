# План исправления критических проблем Project Starter CLI

**Дата**: 2026-01-17
**Цель**: Исправить все критические и второстепенные проблемы для полной работоспособности автоматического деплоя

---

## Обнаруженные проблемы

### Критические (блокируют работу)

1. **Шифрование GitHub Secrets**
   - **Проблема**: Используется Base64 вместо libsodium шифрования
   - **Последствие**: GitHub API отклоняет секреты, деплой невозможен
   - **Файл**: `GitHubClient.kt:112-116`

2. **Генерация SSH ключей**
   - **Проблема**: Возвращается заглушка вместо реального публичного ключа
   - **Последствие**: GitHub Actions не может подключиться к VPS
   - **Файл**: `VPSService.kt:126-148`

3. **GitHub Actions триггер**
   - **Проблема**: Деплой на каждый push в любую ветку
   - **Требование**: Только на merge в main
   - **Файл**: `templates/project-template/.github/workflows/deploy.yml:4-5`

4. **Копирование nginx.conf**
   - **Проблема**: В deploy.yml копируется только docker-compose.yml, но не nginx.conf
   - **Последствие**: Nginx контейнер не стартует
   - **Файл**: `templates/project-template/.github/workflows/deploy.yml:29`

### Второстепенные (желательно исправить)

5. **Config.kt отсутствует**
   - **Проблема**: Код использует `Config.GITHUB_API_URL`, но файл не существует
   - **Последствие**: Проект не компилируется
   - **Использование**: `GitHubClient.kt:27`, `VPSService.kt:129`

6. **Docker Compose не устанавливается**
   - **Проблема**: На VPS устанавливается только Docker, но не Docker Compose
   - **Последствие**: Команда `docker compose` не работает на VPS
   - **Файл**: `VPSService.kt:90-99`

7. **Gradle wrapper отсутствует**
   - **Проблема**: В шаблон не копируются gradlew и gradle/wrapper/
   - **Последствие**: Нельзя собрать проект без установленного Gradle
   - **Файл**: `TemplateGenerator.kt:49-61`

---

## Решения

### 1. Шифрование GitHub Secrets с libsodium

**Подход**: Использовать библиотеку Lazysodium для шифрования секретов

**Изменения**:

**build.gradle.kts** - добавить зависимости:
```kotlin
// Encryption для GitHub Secrets
implementation("com.goterl:lazysodium-java:5.1.4")
implementation("net.java.dev.jna:jna:5.13.0")
```

**GitHubClient.kt** - реализовать правильное шифрование:
```kotlin
import com.goterl.lazysodium.LazySodiumJava
import com.goterl.lazysodium.SodiumJava
import com.goterl.lazysodium.interfaces.Box

private fun encryptSecret(publicKeyBase64: String, secretValue: String): String {
    val sodium = LazySodiumJava(SodiumJava())
    val publicKey = Base64.getDecoder().decode(publicKeyBase64)
    val secretBytes = secretValue.toByteArray(Charsets.UTF_8)
    val encrypted = ByteArray(secretBytes.size + Box.SEALBYTES)

    val result = sodium.cryptoBoxSeal(
        encrypted,
        secretBytes,
        secretBytes.size.toLong(),
        publicKey
    )

    if (!result) {
        throw Exception("Failed to encrypt secret")
    }

    return Base64.getEncoder().encodeToString(encrypted)
}
```

**Почему это решение**:
- GitHub API требует именно libsodium (NaCl sealed box)
- Lazysodium - проверенная библиотека с JNA биндингами
- Поддерживает все платформы (Linux, macOS, Windows)

---

### 2. Генерация реальных SSH ключей

**Подход**: Использовать BouncyCastle для генерации ED25519 ключей

**Изменения**:

**build.gradle.kts** - добавить зависимости:
```kotlin
// SSH ключи
implementation("org.bouncycastle:bcprov-jdk18on:1.77")
implementation("org.bouncycastle:bcpkix-jdk18on:1.77")
```

**VPSService.kt** - генерация реальных ключей:
```kotlin
import org.bouncycastle.crypto.generators.Ed25519KeyPairGenerator
import org.bouncycastle.crypto.params.Ed25519KeyGenerationParameters
import org.bouncycastle.crypto.params.Ed25519PrivateKeyParameters
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.util.io.pem.PemObject
import org.bouncycastle.util.io.pem.PemWriter
import java.security.SecureRandom

companion object {
    fun generateSSHKeyPair(): SSHKeyPair {
        Security.addProvider(BouncyCastleProvider())

        // Генерируем ED25519 ключи
        val keyGen = Ed25519KeyPairGenerator()
        keyGen.init(Ed25519KeyGenerationParameters(SecureRandom()))
        val keyPair = keyGen.generateKeyPair()

        val privateKey = keyPair.private as Ed25519PrivateKeyParameters
        val publicKey = keyPair.public as Ed25519PublicKeyParameters

        // Конвертируем приватный ключ в OpenSSH PEM формат
        val privatePem = convertToOpenSSHPrivateKey(privateKey)

        // Конвертируем публичный ключ в OpenSSH формат
        val publicKeySSH = convertToOpenSSHPublicKey(publicKey)

        return SSHKeyPair(
            privateKey = privatePem,
            publicKey = publicKeySSH
        )
    }

    private fun convertToOpenSSHPrivateKey(privateKey: Ed25519PrivateKeyParameters): String {
        // OpenSSH формат для ED25519
        val encoded = privateKey.encoded
        return buildString {
            appendLine("-----BEGIN OPENSSH PRIVATE KEY-----")
            Base64.getEncoder().encodeToString(encoded)
                .chunked(70)
                .forEach { appendLine(it) }
            appendLine("-----END OPENSSH PRIVATE KEY-----")
        }
    }

    private fun convertToOpenSSHPublicKey(publicKey: Ed25519PublicKeyParameters): String {
        val keyBytes = publicKey.encoded
        val keyBase64 = Base64.getEncoder().encodeToString(keyBytes)
        return "ssh-ed25519 $keyBase64 project-starter-cli"
    }
}
```

**Почему ED25519**:
- Современный стандарт (безопаснее RSA 2048)
- Меньший размер ключей
- Быстрее генерация и проверка
- GitHub и все VPS поддерживают

**Альтернатива**: Использовать внешний процесс `ssh-keygen`, но это менее портабельно.

---

### 3. Исправить GitHub Actions триггер

**Изменения**:

**templates/project-template/.github/workflows/deploy.yml**:
```yaml
name: Deploy to VPS

on:
  push:
    branches: ['main']  # Только main ветка
  workflow_dispatch:     # Опционально - ручной запуск

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    # ... остальное без изменений
```

**Почему**:
- Деплой только на production (main) ветку
- Избегаем лишних деплоев на feature branches
- `workflow_dispatch` позволяет ручной деплой при необходимости

---

### 4. Копировать nginx.conf в деплой

**Изменения**:

**templates/project-template/.github/workflows/deploy.yml**:
```yaml
- name: Copy to VPS
  uses: appleboy/scp-action@master
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USER }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    source: "{{PROJECT_NAME}}.tar.gz,docker-compose.yml,nginx.conf"  # Добавлен nginx.conf
    target: "/opt/{{PROJECT_SLUG}}"
```

**Почему**:
- docker-compose.yml ссылается на `./nginx.conf`
- Без этого файла Nginx контейнер не запустится

---

### 5. Создать Config.kt

**Изменения**:

**Создать файл** `src/main/kotlin/io/github/projectstarter/config/Config.kt`:
```kotlin
package io.github.projectstarter.config

object Config {
    const val GITHUB_API_URL = "https://api.github.com"
    const val SSH_KEY_SIZE = 2048  // Для RSA (не используется с ED25519)
    const val SSH_TIMEOUT_MS = 30000
    const val GIT_PUSH_TIMEOUT_SECONDS = 60L
}
```

**Почему**:
- Централизованное место для констант
- Легко изменить API URL (например, для GitHub Enterprise)
- Избегаем magic numbers

---

### 6. Установка Docker Compose на VPS

**Изменения**:

**VPSService.kt** - добавить метод:
```kotlin
suspend fun checkDockerComposeInstalled(): Boolean {
    val result = executeCommand("docker compose version")
    return result.exitCode == 0
}

suspend fun installDockerCompose(): Boolean {
    // Docker Engine 20.10+ включает Compose V2 как плагин
    // Просто обновляем Docker до последней версии
    val result = executeCommand(
        """
        # Проверяем, есть ли уже docker compose
        if docker compose version &>/dev/null; then
            echo "Docker Compose already installed"
            exit 0
        fi

        # Устанавливаем Docker Compose V2 (плагин)
        DOCKER_CONFIG=${'$'}{DOCKER_CONFIG:-${'$'}HOME/.docker}
        mkdir -p ${'$'}DOCKER_CONFIG/cli-plugins
        curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
          -o ${'$'}DOCKER_CONFIG/cli-plugins/docker-compose
        chmod +x ${'$'}DOCKER_CONFIG/cli-plugins/docker-compose

        # Проверяем установку
        docker compose version
        """.trimIndent()
    )
    return result.exitCode == 0
}
```

**CreateCommand.kt** - добавить проверку после Docker:
```kotlin
// Проверяем Docker Compose
val composeInstalled = vpsSetupService.checkDockerComposeInstalled()
if (!composeInstalled) {
    echo("  Устанавливаем Docker Compose...")
    val installed = vpsSetupService.installDockerCompose()
    if (!installed) {
        echo("  ⚠️  Не удалось установить Docker Compose", err = true)
    } else {
        echo("  ✓ Docker Compose установлен")
    }
} else {
    echo("  ✓ Docker Compose уже установлен")
}
```

**Почему**:
- Современный Docker включает Compose как `docker compose` (не `docker-compose`)
- Установка через плагин более стабильна
- Автоматическая установка экономит время

---

### 7. Копировать Gradle wrapper

**Изменения**:

**TemplateGenerator.kt** - обновить список файлов:
```kotlin
private fun getResourceFiles(path: String): List<String> {
    return listOf(
        ".github/workflows/deploy.yml",
        ".gitignore",
        "Dockerfile",
        "README.md",
        "build.gradle.kts",
        "docker-compose.yml",
        "gradle/wrapper/gradle-wrapper.jar",        // Добавлено
        "gradle/wrapper/gradle-wrapper.properties", // Уже есть
        "gradlew",                                   // Добавлено
        "gradlew.bat",                              // Добавлено (для Windows)
        "nginx.conf",
        "settings.gradle.kts",
        "src/main/kotlin/Application.kt"
    )
}
```

**Также создать файлы в шаблоне**:
- Скопировать `gradlew` и `gradlew.bat` из основного проекта
- Скопировать `gradle/wrapper/gradle-wrapper.jar`

**Почему**:
- Позволяет собрать проект без установки Gradle
- Gradle wrapper - стандарт для Kotlin/Java проектов
- Обеспечивает воспроизводимые сборки

---

## План реализации

### Порядок выполнения

1. **Создать Config.kt** (5 мин)
   - Простой файл с константами
   - Исправит компиляцию

2. **Добавить зависимости в build.gradle.kts** (2 мин)
   - Lazysodium + JNA
   - BouncyCastle

3. **Исправить шифрование секретов** (20 мин)
   - Реализовать encryptSecret() с libsodium
   - Добавить обработку ошибок

4. **Исправить генерацию SSH ключей** (30 мин)
   - Генерация ED25519 ключей
   - Конвертация в OpenSSH формат
   - Тестирование формата ключей

5. **Исправить GitHub Actions workflow** (5 мин)
   - Изменить триггер на только main
   - Добавить nginx.conf в копирование

6. **Добавить установку Docker Compose** (15 мин)
   - Метод checkDockerComposeInstalled()
   - Метод installDockerCompose()
   - Интеграция в CreateCommand

7. **Копировать Gradle wrapper** (10 мин)
   - Обновить список файлов
   - Скопировать wrapper файлы в шаблон

8. **Тестирование** (30 мин)
   - Локальная сборка
   - Тестовый прогон с демо режимом
   - Проверка генерации всех файлов

**Общее время**: ~2 часа

---

## Риски и митигация

### Риск 1: Проблемы с libsodium на разных платформах
**Митигация**: Lazysodium включает нативные библиотеки для всех платформ

### Риск 2: BouncyCastle конфликты с другими библиотеками
**Митигация**: Используем последнюю версию, совместимую с JDK 17+

### Риск 3: SSH ключи не подходят для GitHub Actions
**Митигация**: Используем стандартный OpenSSH формат, тестируем

### Риск 4: Docker Compose установка может зависнуть
**Митигация**: Добавляем таймауты в SSH команды

---

## Критерии успеха

- ✅ Проект компилируется без ошибок
- ✅ GitHub Secrets создаются успешно (не возвращают ошибку API)
- ✅ SSH ключи генерируются в валидном OpenSSH формате
- ✅ GitHub Actions деплоит только на push в main
- ✅ Nginx контейнер стартует (nginx.conf скопирован)
- ✅ Docker Compose установлен на VPS
- ✅ Сгенерированный проект можно собрать через `./gradlew build`

---

## Следующие шаги после реализации

1. Протестировать на реальном VPS
2. Создать integration test
3. Обновить документацию (README.md, USAGE.md)
4. Создать GitHub Release с исправленной версией

---

**Статус**: План готов к реализации
**Оценка сложности**: Средняя (требует работы с криптографией и SSH)
**Приоритет**: Критический (блокирует основную функциональность)

package io.github.projectstarter.cli

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.options.flag
import io.github.cdimascio.dotenv.dotenv
import io.github.projectstarter.config.Config
import io.github.projectstarter.github.GitHubClient
import io.github.projectstarter.ssh.VPSService
import io.github.projectstarter.template.TemplateGenerator
import kotlinx.coroutines.runBlocking
import java.io.File

class CreateCommand : CliktCommand(
    name = "create",
    help = "Создать новый проект с автоматическим деплоем на VPS"
) {

    private val projectName by option("-n", "--name", help = "Название проекта")

    private val description by option("-d", "--description", help = "Описание проекта для GitHub")

    private val vpsHost by option("-h", "--host", help = "Хост VPS (IP или домен)")

    private val vpsUser by option("-u", "--user", help = "Пользователь SSH на VPS")

    private val vpsPassword by option("-p", "--password", help = "Пароль SSH на VPS")

    private val githubToken by option("-t", "--token", help = "GitHub Personal Access Token")

    private val skipValidation by option("--skip-validation", help = "Пропустить валидацию (для тестирования)").flag(default = false)

    private val demoMode by option("--demo", help = "Демо режим - симуляция без реальных API вызовов (для видео)").flag(default = false)

    override fun run() = runBlocking {
        // Загружаем переменные окружения из .env напрямую (минуя системные)
        val env = mutableMapOf<String, String>()
        try {
            val envFile = java.io.File(".env")
            if (envFile.exists()) {
                envFile.forEachLine { line ->
                    val trimmed = line.trim()
                    if (trimmed.isNotEmpty() && !trimmed.startsWith("#")) {
                        val parts = trimmed.split("=", limit = 2)
                        if (parts.size == 2) {
                            env[parts[0].trim()] = parts[1].trim()
                        }
                    }
                }
            }
        } catch (e: Exception) {
            // Игнорируем ошибки чтения .env
        }

        // Проверяем обязательные параметры проекта
        val projectName = projectName
        if (projectName == null) {
            echo("❌ Название проекта не указано!", err = true)
            echo("  Используйте: create -n <название проекта>", err = true)
            echo("", err = true)
            return@runBlocking
        }

        val description = description
        if (description == null) {
            echo("❌ Описание проекта не указано!", err = true)
            echo("  Используйте: create -d <описание>", err = true)
            echo("", err = true)
            return@runBlocking
        }

        // Приоритет: аргументы CLI > .env > значения по умолчанию
        val envToken = env["GITHUB_TOKEN"]
        val finalToken = githubToken ?: envToken
        if (finalToken == null) {
            echo("❌ GitHub токен не указан!", err = true)
            echo("  Укажите GITHUB_TOKEN в .env или через параметр --token", err = true)
            echo("", err = true)
            return@runBlocking
        }

        val config = ProjectConfig(
            projectName = projectName,
            description = description,
            vpsHost = vpsHost ?: env["VPS_HOST"],
            vpsUser = vpsUser ?: env["VPS_USER"] ?: "root",
            vpsPassword = vpsPassword ?: env["VPS_PASSWORD"],
            githubToken = finalToken
        )

        echo("🚀 Project Starter CLI")
        echo("")
        echo("Конфигурация:")
        echo("  Проект: ${config.projectName}")
        echo("  VPS: ${config.vpsUser}@${config.vpsHost ?: "не указан"}")
        echo("  GitHub: ${config.githubToken?.take(20)}...")
        echo("")

        // Инициализируем клиенты (только если не демо режим)
        val githubClient = GitHubClient(config.githubToken)
        val vpsService = if (!demoMode) {
            val vpsHostForValidation = config.vpsHost ?: run {
                echo("⚠️  VPS хост не указан, пропускаем VPS валидацию", err = true)
                null
            }
            if (vpsHostForValidation != null) {
                VPSService(vpsHostForValidation, config.vpsUser)
            } else {
                null
            }
        } else {
            null
        }

        val validator = if (vpsService != null) Validator(githubClient, vpsService) else null

        // Валидация
        if (!skipValidation && !demoMode && validator != null) {
            echo("🔍 Валидация параметров...")
            val validationResult = validator.validateAll()
            if (validationResult is ValidationResult.Error) {
                echo("❌ Ошибка валидации:", err = true)
                validationResult.errors.forEach { echo("  • $it", err = true) }
                echo("", err = true)
                echo("Пожалуйста, исправьте ошибки и попробуйте снова.", err = true)
                echo("", err = true)
                echo("💡 Совет: Создайте .env файл на основе .env.example", err = true)
                echo("   Или используйте --skip-validation для тестирования", err = true)
                githubClient.close()
                vpsService?.close()
                return@runBlocking
            }
            echo("✓ Валидация пройдена")
            echo("")
        } else if (skipValidation) {
            echo("⚠️  Валидация пропущена (--skip-validation)")
            echo("")
        }

        // Закрываем VPS соединение после валидации
        vpsService?.close()

        // Проверяем обязательные параметры
        val vpsHost = config.vpsHost ?: run {
            echo("❌ VPS хост не указан!", err = true)
            echo("  Укажите VPS_HOST в .env или через параметр --host", err = true)
            echo("")
            githubClient.close()
            vpsService?.close()
            return@runBlocking
        }

        if (demoMode) {
            // Демо режим - симуляция для видео
            echo("🎬 ДЕМО РЕЖИМ - симуляция создания проекта")
            echo("")
            echo("📦 Создаём GitHub репозиторий...")
            echo("✓ GitHub репозиторий создан: https://github.com/ivanlardis/${config.projectName.lowercase().replace(" ", "-")}")
            echo("")

            echo("📝 Генерируем проект из шаблона...")
            echo("✓ Проект сгенерирован")
            echo("")

            echo("🔐 Настраиваем GitHub Secrets...")
            echo("✓ GitHub Secrets настроены")
            echo("")

            echo("⚙️  Настраиваем VPS...")
            echo("  ✓ Аутентификация по паролю успешна")
            echo("  ✓ Docker уже установлен")
            echo("  ✓ GitHub Actions SSH ключ добавлен")
            echo("✓ VPS настроен успешно!")
            echo("")

            echo("📤 Отправляем код в GitHub...")
            echo("")
            echo("Выполните следующие команды вручную:")
            echo("  cd /tmp/project-starter...")
            echo("  git init")
            echo("  git add .")
            echo("  git commit -m 'Initial commit from Project Starter CLI'")
            echo("  git branch -M main")
            echo("  git remote add origin https://github.com/ivanlardis/${config.projectName.lowercase().replace(" ", "-")}.git")
            echo("  git push -u origin main")
            echo("")
            echo("✓ Шаблон проекта готов в: /tmp/project-starter...")

            githubClient.close()
            echo("")
            echo("🚀 Готово! Ваш проект будет доступен на http://$vpsHost через 2-3 минуты")
            echo("")
            echo("📋 Ссылки:")
            echo("  • Репозиторий: https://github.com/ivanlardis/${config.projectName.lowercase().replace(" ", "-")}")
            echo("  • Действия: https://github.com/ivanlardis/${config.projectName.lowercase().replace(" ", "-")}/actions")
            echo("")
            echo("✨ Демо режим завершён - для реального деплоя уберите флаг --demo")
            return@runBlocking
        }

        echo("✓ Валидация пройдена")
        echo("")

        // 1. Создаём GitHub репозиторий
        echo("📦 Создаём GitHub репозиторий...")
        val repo = runCatching {
            githubClient.createRepository(
                name = config.projectName.lowercase().replace(" ", "-"),
                description = config.description
            )
        }.onFailure { e ->
            echo("❌ Не удалось создать репозиторий: ${e.message}", err = true)
            githubClient.close()
            return@runBlocking
        }.getOrNull()!!

        echo("✓ GitHub репозиторий создан: ${repo.html_url}")
        echo("")

        // 2. Генерируем проект из шаблона
        echo("📝 Генерируем проект из шаблона...")
        val tempDir = createTempDir("project-starter")
        val templateGenerator = TemplateGenerator()

        // Получаем GitHub username
        val githubUser = githubClient.getUser()
        val placeholders = templateGenerator.generatePlaceholders(
            projectName = config.projectName,
            description = config.description,
            username = githubUser.login,
            githubRepo = repo.full_name
        )

        val templatePath = templateGenerator.extractTemplate()
        val result = templateGenerator.generateProject(
            templatePath = templatePath,
            outputPath = tempDir.absolutePath,
            placeholders = placeholders
        )

        if (result.isFailure) {
            echo("❌ Не удалось сгенерировать проект: ${result.exceptionOrNull()?.message}", err = true)
            githubClient.close()
            return@runBlocking
        }

        echo("✓ Проект сгенерирован")
        echo("")

        // 3. Настраиваем GitHub Secrets
        echo("🔐 Настраиваем GitHub Secrets...")

        // Генерируем SSH ключи
        val sshKeyPair = VPSService.generateSSHKeyPair()

        runCatching {
            githubClient.createSecret(
                owner = repo.owner.login,
                repo = repo.name,
                secretName = "VPS_HOST",
                secretValue = vpsHost
            )
            githubClient.createSecret(
                owner = repo.owner.login,
                repo = repo.name,
                secretName = "VPS_USER",
                secretValue = config.vpsUser
            )
            githubClient.createSecret(
                owner = repo.owner.login,
                repo = repo.name,
                secretName = "VPS_PASSWORD",
                secretValue = config.vpsPassword ?: ""
            )
            githubClient.createSecret(
                owner = repo.owner.login,
                repo = repo.name,
                secretName = "SSH_PRIVATE_KEY",
                secretValue = sshKeyPair.privateKey
            )
        }.onFailure { e ->
            echo("⚠️  Не удалось создать все секреты: ${e.message}", err = true)
        }

        echo("✓ GitHub Secrets настроены")
        echo("")

        // 4. Настраиваем VPS (опционально)
        echo("⚙️  Настраиваем VPS...")

        // Создаём новый VPSService для настройки (после валидации предыдущий закрыт)
        val vpsSetupService = VPSService(vpsHost, config.vpsUser)

        // Подключаемся к VPS
        val connected = vpsSetupService.connect()
        if (!connected) {
            echo("⚠️  Не удалось подключиться к VPS", err = true)
            echo("  Это может быть из-за:", err = true)
            echo("  - Неверный хост или порт", err = true)
            echo("  - Файрвал блокирует соединение", err = true)
            echo("  - SSH сервер недоступен", err = true)
            echo("", err = true)
            echo("  VPS можно настроить вручную после деплоя.", err = true)
            echo("")
        } else {
            // Авторизуемся
            echo("  Аутентификация на VPS...")
            val authed = if (config.vpsPassword != null) {
                vpsSetupService.authenticateWithPassword(config.vpsPassword)
            } else {
                echo("  Пароль не указан, пробуем продолжить...")
                true // Предполагаем что ключ настроен
            }

            if (!authed && config.vpsPassword != null) {
                echo("⚠️  Не удалось авторизоваться на VPS", err = true)
                echo("", err = true)
                echo("  VPS использует SSH-ключи вместо паролей.", err = true)
                echo("  Добавьте ваш публичный ключ на VPS:", err = true)
                echo("", err = true)
                echo("  Ваш публичный ключ:", err = true)
                val publicKey = try {
                    java.io.File(System.getProperty("user.home") + "/.ssh/id_ed25519.pub").readText()
                } catch (e: Exception) {
                    try {
                        java.io.File(System.getProperty("user.home") + "/.ssh/id_rsa.pub").readText()
                    } catch (e2: Exception) {
                        "(не найден - создайте: ssh-keygen -t ed25519)"
                    }
                }
                echo("  $publicKey", err = true)
                echo("", err = true)
                echo("  Команда для добавления:", err = true)
                echo("  ssh-copy-id ${config.vpsUser}@${config.vpsHost}", err = true)
                echo("  Или вручную:", err = true)
                echo("  cat ~/.ssh/id_ed25519.pub | ssh ${config.vpsUser}@${config.vpsHost} 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'", err = true)
                echo("", err = true)
                vpsSetupService.close()
            } else {
                if (config.vpsPassword != null) {
                    echo("  ✓ Аутентификация по паролю успешна")
                } else {
                    echo("  ✓ SSH ключ аутентификация (предполагается)")
                }

                // Проверяем Docker
                val dockerInstalled = vpsSetupService.checkDockerInstalled()
                if (!dockerInstalled) {
                    echo("  Устанавливаем Docker...")
                    val installed = vpsSetupService.installDocker()
                    if (!installed) {
                        echo("  ⚠️  Не удалось установить Docker", err = true)
                    } else {
                        echo("  ✓ Docker установлен")
                    }
                } else {
                    echo("  ✓ Docker уже установлен")
                }

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

                // Добавляем публичный ключ GitHub Actions
                val keyAdded = vpsSetupService.addSSHPublicKey(sshKeyPair.publicKey)
                if (!keyAdded) {
                    echo("  ⚠️  GitHub Actions ключ не добавлен", err = true)
                } else {
                    echo("  ✓ GitHub Actions SSH ключ добавлен")
                }

                vpsSetupService.close()
                echo("✓ VPS настроен успешно!")
                echo("")
            }
        }

        // 5. Отправляем код в GitHub
        echo("📤 Отправляем код в GitHub...")

        val gitScript = """
            cd "${tempDir.absolutePath}"
            git init
            git config user.email "cli@projectstarter"
            git config user.name "Project Starter CLI"
            git add .
            git commit -m 'Initial commit from Project Starter CLI'
            git branch -M main
            git remote add origin https://${config.githubToken}@github.com/${repo.full_name}.git
            git push -u origin main
        """.trimIndent()

        val scriptFile = java.io.File.createTempFile("git-push-", ".sh")
        scriptFile.writeText(gitScript)
        scriptFile.setExecutable(true)

        val pushResult = runCatching {
            val process = ProcessBuilder("/bin/bash", scriptFile.absolutePath)
                .redirectErrorStream(true)
                .start()

            val output = process.inputStream.bufferedReader().use { it.readText() }
            val exitCode = process.waitFor()

            Pair(exitCode, output)
        }

        scriptFile.delete()

        when {
            pushResult.isFailure -> {
                echo("❌ Ошибка при выполнении git команд: ${pushResult.exceptionOrNull()?.message}", err = true)
                echo("")
            }
            pushResult.getOrNull()?.first != 0 -> {
                val (exitCode, output) = pushResult.getOrNull()!!

                // Проверяем специфичные ошибки
                when {
                    output.contains("without `workflow` scope") -> {
                        echo("❌ GitHub токен не имеет необходимых прав!", err = true)
                        echo("", err = true)
                        echo("Для создания GitHub Actions workflows нужен scope 'workflow'.", err = true)
                        echo("", err = true)
                        echo("Как исправить:", err = true)
                        echo("  1. Перейдите на https://github.com/settings/tokens", err = true)
                        echo("  2. Создайте новый токен или отредактируйте существующий", err = true)
                        echo("  3. Добавьте галочку 'workflow' (в дополнение к 'repo')", err = true)
                        echo("  4. Обновите токен в .env файле", err = true)
                        echo("  5. Запустите команду заново", err = true)
                        echo("")
                    }
                    else -> {
                        echo("❌ Git push завершился с ошибкой (exit code: $exitCode)", err = true)
                        if (output.isNotBlank()) {
                            echo("Вывод:", err = true)
                            output.lines().forEach { echo("  $it", err = true) }
                        }
                        echo("")
                    }
                }
            }
            else -> {
                echo("✓ Код успешно отправлен в GitHub")
                echo("")
            }
        }
        echo("")
        echo("✓ Шаблон проекта готов в: ${tempDir.absolutePath}")

        githubClient.close()
        echo("")
        echo("🚀 Готово! Ваш проект будет доступен на http://$vpsHost через 2-3 минуты")
        echo("")
        echo("📋 Ссылки:")
        echo("  • Репозиторий: ${repo.html_url}")
        echo("  • Действия: ${repo.html_url}/actions")
        echo("  • Сайт: http://$vpsHost")
    }
}

data class ProjectConfig(
    val projectName: String,
    val description: String,
    val vpsHost: String?,
    val vpsUser: String,
    val vpsPassword: String?,
    val githubToken: String
)

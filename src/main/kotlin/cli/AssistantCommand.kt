package cli

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.options.help
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.options.required
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import llm.Message
import llm.OpenRouterClient
import llm.PromptBuilder
import mcp.CrmTools
import mcp.GitTools
import mcp.McpServer
import rag.*
import rag.embeddings.OnnxEmbeddingVectorizer

/**
 * Главная CLI команда
 */
class AssistantCommand : CliktCommand(
    name = "project-assistant",
    help = "RAG-ассистент для разработчика"
) {
    private val homeDir by option("--home", "-h")
        .help("Путь к home директории проекта")
        .required()

    private lateinit var vectorizer: OnnxEmbeddingVectorizer
    private lateinit var vectorStore: InMemoryVectorStore
    private lateinit var indexer: DocumentIndexer
    private lateinit var ragService: RagService
    private lateinit var llmClient: OpenRouterClient
    private lateinit var gitTools: GitTools
    private lateinit var crmTools: CrmTools
    private lateinit var mcpServer: McpServer

    override fun run() {
        echo("=== Project Assistant CLI ===")
        echo("Home directory: $homeDir")
        echo("")

        // Инициализация компонентов
        echo("Загрузка ONNX модели...")
        vectorizer = try {
            OnnxEmbeddingVectorizer()
        } catch (e: Exception) {
            echo("Не удалось загрузить ONNX модель: ${e.message}")
            return
        }
        echo("Модель загружена (размерность: ${vectorizer.dimension})")

        vectorStore = InMemoryVectorStore(vectorizer)
        indexer = DocumentIndexer(vectorizer, vectorStore)
        ragService = RagService(vectorizer, vectorStore)
        llmClient = OpenRouterClient()
        gitTools = GitTools(homeDir)
        crmTools = CrmTools("$homeDir/crm-data")
        mcpServer = McpServer(gitTools, crmTools)

        // Запуск интерактивного режима
        startInteractiveMode()

        // Закрытие ресурсов
        if (this::vectorizer.isInitialized) {
            vectorizer.close()
        }
        llmClient.close()
        gitTools.close()
    }

    private fun startInteractiveMode() {
        echo("Введите команду или вопрос (для помощи: /help)")
        echo("")

        val scanner = java.util.Scanner(System.`in`, "UTF-8")

        while (true) {
            print("> ")
            System.out.flush()

            val input = try {
                if (scanner.hasNextLine()) {
                    scanner.nextLine().trim()
                } else {
                    break
                }
            } catch (e: Exception) {
                echo("Ошибка чтения ввода: ${e.message}")
                continue
            }

            if (input.isEmpty()) continue

            when {
                input == "/exit" || input == "/quit" -> {
                    echo("До свидания!")
                    break
                }
                input == "/help" -> showHelp()
                input == "/index" -> runIndexCommand()
                input == "/git" -> showGitInfo()
                input == "/git-changes" -> showGitChanges()
                input == "/stats" -> showStats()
                else -> answerQuestion(input)
            }

            echo("")
        }

        scanner.close()
    }

    private fun showHelp() {
        echo("""
            === Доступные команды ===

            /index  - Переиндексировать проект
            /help   - Показать эту справку
            /git    - Показать информацию о git-репозитории
            /git-changes - Показать незакоммиченные/новые файлы
            /stats  - Показать статистику индекса
            /exit   - Выход из программы

            === Примеры вопросов ===

            - Как работает аутентификация в проекте?
            - Где находится класс UserService?
            - Какие API endpoints есть?
            - Покажи структуру базы данных

            === Работа ===

            1. Сначала выполните /index для индексации проекта
            2. Задавайте вопросы - ассистент найдет релевантный код и ответит
        """.trimIndent())
    }

    private fun runIndexCommand() {
        echo("Начинаю индексацию проекта...")

        try {
            val stats = indexer.indexDirectory(homeDir) { progress ->
                echo(progress)
            }

            echo("")
            echo("=== Результат индексации ===")
            echo("Всего файлов: ${stats.totalFiles}")
            echo("  Kotlin:   ${stats.kotlinFiles}")
            echo("  Java:     ${stats.javaFiles}")
            echo("  Markdown: ${stats.markdownFiles}")

        } catch (e: Exception) {
            echo("Ошибка при индексации: ${e.message}")
        }
    }

    private fun showGitInfo() {
        echo(mcpServer.getGitInfo())
    }

    private fun showGitChanges() {
        echo(mcpServer.getUncommittedFiles())
    }

    private fun showStats() {
        val size = ragService.getIndexSize()
        echo("Проиндексировано документов: $size")
        if (size == 0) {
            echo("Выполните /index для индексации проекта")
        }
    }

    private fun answerQuestion(query: String) {
        if (ragService.getIndexSize() == 0) {
            echo("Индекс пуст. Сначала выполните /index для индексации проекта.")
            return
        }

        echo("Поиск релевантных документов...")

        // RAG поиск
        val ragResults = ragService.search(query)

        if (ragResults.isEmpty()) {
            echo("Релевантные документы не найдены.")
            return
        }

        echo("Найдено документов: ${ragResults.size}")
        ragResults.forEachIndexed { idx, result ->
            echo("  ${idx + 1}. ${result.document.filePath} (score: ${"%.2f".format(result.score)})")
        }
        echo("")

        val extraContext = buildMcpContextIfNeeded(query)
        if (extraContext != null) {
            echo("Добавлен контекст из MCP (git).")
        }

        // Запрос к LLM
        echo("Отправка запроса к LLM...")
        val messages = PromptBuilder.buildMessages(query, ragResults, extraContext)
        val initialResponse = runBlocking { llmClient.chat(messages) }
        val tool = parseToolCall(initialResponse)

        if (tool != null) {
            echo("LLM запросила MCP: $tool")
            val toolResult = when {
                tool.startsWith("crm_get_user:") -> {
                    val arg = tool.substringAfter("crm_get_user:").trim()
                    mcpServer.getUser(arg)
                }
                tool == "crm_list_users" -> mcpServer.listUsers()
                tool.startsWith("crm_get_user_tickets:") -> {
                    val userId = tool.substringAfter("crm_get_user_tickets:").trim()
                    mcpServer.getUserTickets(userId)
                }
                tool.startsWith("crm_get_ticket:") -> {
                    val ticketId = tool.substringAfter("crm_get_ticket:").trim()
                    mcpServer.getTicket(ticketId)
                }
                tool.startsWith("crm_get_user_subscriptions:") -> {
                    val userId = tool.substringAfter("crm_get_user_subscriptions:").trim()
                    mcpServer.getUserSubscriptions(userId)
                }
                tool == "git_info" -> mcpServer.getGitInfo()
                tool == "git_uncommitted" -> mcpServer.getUncommittedFiles()
                else -> null
            }

            if (toolResult != null) {
                val followUp = messages +
                    Message(role = "assistant", content = initialResponse) +
                    Message(
                        role = "system",
                        content = "Результат MCP ($tool):\n$toolResult"
                    ) +
                    Message(
                        role = "user",
                        content = "Дай окончательный ответ пользователю с учетом результата MCP выше."
                    )

                val finalResponse = runBlocking { llmClient.chat(followUp) }
                echo("")
                echo("=== Ответ ===")
                echo(finalResponse)
                return
            }
        }

        echo("")
        echo("=== Ответ ===")
        echo(initialResponse)
    }

    private fun buildMcpContextIfNeeded(query: String): String? {
        val q = query.lowercase()
        val gitKeywords = listOf("git", "гит", "ветк", "branch", "commit", "коммит", "репозитор", "статус", "status")
        val needsGit = gitKeywords.any { q.contains(it) }
        val needsChanges = listOf("изменен", "изменения", "uncommitted", "untracked", "новые файлы", "не закоммит", "modified", "diff", "diffs")
            .any { q.contains(it) }

        val crmKeywords = listOf("пользовател", "user", "тикет", "ticket", "подписк", "subscription", "план", "plan", "клиент", "client", "crm")
        val needsCrm = crmKeywords.any { q.contains(it) }

        if (!needsGit && !needsChanges && !needsCrm) return null

        return buildString {
            if (needsGit || needsChanges) {
                appendLine(mcpServer.getGitInfo())
                if (needsChanges) {
                    appendLine()
                    appendLine(mcpServer.getUncommittedFiles())
                }
            }

            if (needsCrm) {
                if (isNotEmpty()) appendLine()
                appendLine(mcpServer.listUsers())
            }
        }.trim()
    }

    private fun parseToolCall(response: String): String? {
        val trimmed = response.trim()
        if (!trimmed.startsWith("{")) return null
        return try {
            val json = Json.parseToJsonElement(trimmed)
            val toolObj = json.jsonObject["tool"]?.jsonPrimitive?.contentOrNull
            val argsObj = json.jsonObject["args"]?.jsonPrimitive?.contentOrNull

            if (toolObj != null && argsObj != null) {
                "$toolObj:$argsObj"
            } else {
                toolObj
            }
        } catch (_: Exception) {
            null
        }
    }
}

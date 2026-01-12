package cli

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.options.required
import com.github.ajalt.clikt.parameters.options.help
import kotlinx.coroutines.runBlocking
import llm.OpenRouterClient
import llm.PromptBuilder
import mcp.GitTools
import mcp.McpServer
import rag.*

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

    private lateinit var vectorizer: TfIdfVectorizer
    private lateinit var vectorStore: InMemoryVectorStore
    private lateinit var indexer: DocumentIndexer
    private lateinit var ragService: RagService
    private lateinit var llmClient: OpenRouterClient
    private lateinit var gitTools: GitTools
    private lateinit var mcpServer: McpServer

    override fun run() {
        echo("=== Project Assistant CLI ===")
        echo("Home directory: $homeDir")
        echo("")

        // Инициализация компонентов
        vectorizer = TfIdfVectorizer()
        vectorStore = InMemoryVectorStore(vectorizer)
        indexer = DocumentIndexer(vectorizer, vectorStore)
        ragService = RagService(vectorizer, vectorStore)
        llmClient = OpenRouterClient()
        gitTools = GitTools(homeDir)
        mcpServer = McpServer(gitTools)

        // Запуск интерактивного режима
        startInteractiveMode()

        // Закрытие ресурсов
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
            echo("Всего токенов: ${stats.totalTokens}")

        } catch (e: Exception) {
            echo("Ошибка при индексации: ${e.message}")
        }
    }

    private fun showGitInfo() {
        echo(mcpServer.getGitInfo())
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

        // Запрос к LLM
        echo("Отправка запроса к LLM...")
        val messages = PromptBuilder.buildMessages(query, ragResults)

        runBlocking {
            val response = llmClient.chat(messages)
            echo("")
            echo("=== Ответ ===")
            echo(response)
        }
    }
}

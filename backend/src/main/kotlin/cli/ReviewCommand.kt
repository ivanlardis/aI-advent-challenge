package cli

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.options.default
import com.github.ajalt.clikt.parameters.options.help
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.options.required
import kotlinx.coroutines.runBlocking
import llm.OpenRouterClient
import review.GitDiffExtractor
import review.GitHubCommentPublisher
import review.PRAnalysisService
import kotlin.system.exitProcess

/**
 * CLI команда для автоматического ревью Pull Request
 */
class ReviewCommand : CliktCommand(
    name = "review-pr",
    help = "Автоматический code review Pull Request с помощью AI"
) {
    private val prNumber by option("--pr-number", "-p")
        .required()
        .help("Номер Pull Request для анализа")

    private val repoPath by option("--repo-path", "-r")
        .default(".")
        .help("Путь к git репозиторию (по умолчанию: текущая директория)")

    override fun run() = runBlocking {
        echo("🤖 AI Code Review для PR #${prNumber.toInt()}")
        echo("")

        try {
            // Инициализация компонентов
            val diffExtractor = GitDiffExtractor()
            val llmClient = OpenRouterClient()
            val analysisService = PRAnalysisService(diffExtractor, llmClient)
            val commentPublisher = GitHubCommentPublisher()

            // Анализ PR
            echo("📊 Получение diff...")
            val result = analysisService.analyzePR(prNumber.toInt(), repoPath).getOrElse { error ->
                echo("❌ Ошибка при анализе PR: ${error.message}", err = true)

                // Попытка опубликовать fallback комментарий
                tryPublishErrorComment(commentPublisher, prNumber.toInt(), error.message ?: "Неизвестная ошибка")

                llmClient.close()
                exitProcess(1)
            }

            echo("✅ Анализ завершен (файлов: ${result.filesAnalyzed})")
            echo("")

            // Публикация комментария
            echo("📝 Публикация комментария в PR...")
            commentPublisher.postComment(prNumber.toInt(), result.comment, repoPath).getOrElse { error ->
                echo("❌ Не удалось опубликовать комментарий: ${error.message}", err = true)
                echo("")
                echo("Сгенерированный комментарий:")
                echo("─".repeat(80))
                echo(result.comment)
                echo("─".repeat(80))

                llmClient.close()
                exitProcess(1)
            }

            echo("✅ Комментарий успешно опубликован!")
            echo("")
            echo("Просмотреть: gh pr view ${prNumber.toInt()}")

            // Закрытие ресурсов
            llmClient.close()

        } catch (e: Exception) {
            echo("❌ Непредвиденная ошибка: ${e.message}", err = true)
            e.printStackTrace()
            exitProcess(1)
        }
    }

    /**
     * Попытаться опубликовать fallback комментарий при ошибке
     */
    private fun tryPublishErrorComment(publisher: GitHubCommentPublisher, prNumber: Int, errorMessage: String) {
        try {
            val fallbackComment = """
                ## ❌ AI Code Review - Ошибка

                К сожалению, не удалось выполнить автоматическое ревью этого PR.

                **Причина:** $errorMessage

                Пожалуйста, проверьте логи GitHub Actions для деталей.

                ---
                *Powered by Grok 4.1 Fast*
            """.trimIndent()

            publisher.postComment(prNumber, fallbackComment, repoPath)
        } catch (e: Exception) {
            // Игнорируем ошибки при публикации fallback комментария
            echo("⚠️ Не удалось опубликовать fallback комментарий: ${e.message}", err = true)
        }
    }
}

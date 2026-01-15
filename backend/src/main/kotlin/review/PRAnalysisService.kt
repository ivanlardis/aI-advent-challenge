package review

import config.Config
import llm.OpenRouterClient
import org.slf4j.LoggerFactory

/**
 * Сервис для анализа Pull Request
 */
class PRAnalysisService(
    private val diffExtractor: GitDiffExtractor,
    private val llmClient: OpenRouterClient
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Анализировать PR и вернуть результат ревью
     */
    suspend fun analyzePR(prNumber: Int, repoPath: String = "."): Result<ReviewResult> {
        return try {
            logger.info("Начало анализа PR #$prNumber")

            // 1. Получить diff
            val diffResult = diffExtractor.getPRDiff(prNumber, repoPath).getOrElse {
                logger.error("Не удалось получить diff", it)
                return Result.failure(it)
            }

            logger.info("Получено файлов для анализа: ${diffResult.files.size}")

            // 2. Проверить лимит файлов
            val limitedDiff = if (diffResult.files.size > Config.REVIEW_MAX_FILES) {
                logger.warn("PR содержит ${diffResult.files.size} файлов, ограничиваем до ${Config.REVIEW_MAX_FILES}")
                diffResult.copy(files = diffResult.files.take(Config.REVIEW_MAX_FILES))
            } else {
                diffResult
            }

            // 3. Сформировать промпт
            val messages = ReviewPromptBuilder.buildPrompt(limitedDiff)

            // 4. Получить ревью от LLM
            logger.info("Отправка запроса к LLM...")
            val reviewText = llmClient.chat(messages)

            if (reviewText.startsWith("Ошибка")) {
                logger.error("LLM вернул ошибку: $reviewText")
                return Result.failure(Exception(reviewText))
            }

            // 5. Добавить footer
            val footer = buildFooter(diffResult.files.size, limitedDiff.files.size)
            val finalComment = "$reviewText\n\n$footer"

            logger.info("Анализ PR #$prNumber завершен успешно")

            Result.success(
                ReviewResult(
                    comment = finalComment,
                    filesAnalyzed = limitedDiff.files.size
                )
            )

        } catch (e: Exception) {
            logger.error("Ошибка при анализе PR #$prNumber", e)
            Result.failure(e)
        }
    }

    /**
     * Построить footer для комментария
     */
    private fun buildFooter(totalFiles: Int, analyzedFiles: Int): String {
        val sb = StringBuilder()
        sb.appendLine("---")

        if (analyzedFiles < totalFiles) {
            sb.appendLine("⚠️ **Внимание:** PR содержит $totalFiles файлов, проанализированы первые $analyzedFiles")
        }

        sb.append("*Проанализировано файлов: $analyzedFiles | ")
        sb.append("Powered by Grok 4.1 Fast*")

        return sb.toString()
    }
}

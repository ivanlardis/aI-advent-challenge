package review

import org.slf4j.LoggerFactory
import java.io.File

/**
 * Публикация комментариев в GitHub PR через gh CLI
 */
class GitHubCommentPublisher {
    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Опубликовать комментарий к PR
     */
    fun postComment(prNumber: Int, comment: String, repoPath: String = "."): Result<Unit> {
        return try {
            logger.info("Публикация комментария в PR #$prNumber")

            // Создать временный файл для комментария (избежать проблем с экранированием)
            val tempFile = File.createTempFile("pr-comment-", ".md")
            try {
                tempFile.writeText(comment)

                val process = ProcessBuilder(
                    "gh", "pr", "comment", prNumber.toString(),
                    "--body-file", tempFile.absolutePath
                )
                    .directory(File(repoPath))
                    .redirectErrorStream(true)
                    .start()

                val output = process.inputStream.bufferedReader().readText()
                val exitCode = process.waitFor()

                if (exitCode == 0) {
                    logger.info("Комментарий успешно опубликован в PR #$prNumber")
                    Result.success(Unit)
                } else {
                    val error = "gh CLI вернул ошибку (exit code: $exitCode): $output"
                    logger.error(error)
                    Result.failure(Exception(error))
                }
            } finally {
                tempFile.delete()
            }

        } catch (e: Exception) {
            logger.error("Ошибка при публикации комментария", e)
            Result.failure(e)
        }
    }
}

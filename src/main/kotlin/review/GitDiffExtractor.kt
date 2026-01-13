package review

import config.Config
import org.slf4j.LoggerFactory
import java.io.File

/**
 * Извлечение diff из Pull Request через gh CLI
 */
class GitDiffExtractor {
    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Получить diff PR с измененными файлами
     */
    fun getPRDiff(prNumber: Int, repoPath: String = "."): Result<DiffResult> {
        return try {
            // Проверка наличия gh CLI
            val whichGh = ProcessBuilder("which", "gh")
                .start()
                .waitFor()

            if (whichGh != 0) {
                return Result.failure(Exception("gh CLI не найден. Установите: https://cli.github.com/"))
            }

            // Получить список измененных файлов
            val process = ProcessBuilder(
                "gh", "pr", "diff", prNumber.toString(),
                "--name-status"
            )
                .directory(File(repoPath))
                .redirectErrorStream(true)
                .start()

            val output = process.inputStream.bufferedReader().readText()
            val exitCode = process.waitFor()

            if (exitCode != 0) {
                return Result.failure(Exception("Ошибка gh CLI: $output"))
            }

            // Парсинг вывода формата: "A\tfile.kt" или "M\tfile.kt"
            val lines = output.trim().lines().filter { it.isNotBlank() }
            val changedFiles = mutableListOf<ChangedFile>()
            var totalAdditions = 0
            var totalDeletions = 0

            for (line in lines) {
                val parts = line.split("\t", limit = 2)
                if (parts.size != 2) continue

                val statusChar = parts[0].trim()
                val filePath = parts[1].trim()

                // Фильтр по расширениям
                val extension = filePath.substringAfterLast('.', "")
                if (extension !in Config.SUPPORTED_EXTENSIONS) {
                    logger.debug("Пропуск файла $filePath: неподдерживаемое расширение")
                    continue
                }

                val changeType = when (statusChar) {
                    "A" -> ChangeType.ADD
                    "M" -> ChangeType.MODIFY
                    "D" -> ChangeType.DELETE
                    else -> {
                        logger.warn("Неизвестный статус: $statusChar для $filePath")
                        ChangeType.MODIFY
                    }
                }

                // Читать содержимое файла (кроме удаленных)
                val content = if (changeType != ChangeType.DELETE) {
                    val file = File(repoPath, filePath)
                    if (file.exists()) {
                        val text = file.readText()
                        totalAdditions += text.lines().size
                        text
                    } else {
                        logger.warn("Файл не найден: $filePath")
                        ""
                    }
                } else {
                    totalDeletions += 1
                    ""
                }

                changedFiles.add(
                    ChangedFile(
                        path = filePath,
                        changeType = changeType,
                        content = content
                    )
                )

                // Ограничение на количество файлов
                if (changedFiles.size >= Config.REVIEW_MAX_FILES) {
                    logger.info("Достигнут лимит файлов: ${Config.REVIEW_MAX_FILES}")
                    break
                }
            }

            if (changedFiles.isEmpty()) {
                return Result.failure(Exception("Нет файлов для анализа (возможно, только binary файлы)"))
            }

            Result.success(
                DiffResult(
                    files = changedFiles,
                    additionsCount = totalAdditions,
                    deletionsCount = totalDeletions
                )
            )

        } catch (e: Exception) {
            logger.error("Ошибка при получении diff", e)
            Result.failure(e)
        }
    }
}

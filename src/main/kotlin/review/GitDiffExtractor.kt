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

            // Получить список измененных файлов через --name-only
            val nameOnlyProcess = ProcessBuilder(
                "gh", "pr", "diff", prNumber.toString(),
                "--name-only"
            )
                .directory(File(repoPath))
                .redirectErrorStream(true)
                .start()

            val nameOnlyOutput = nameOnlyProcess.inputStream.bufferedReader().readText()
            val exitCode = nameOnlyProcess.waitFor()

            if (exitCode != 0) {
                return Result.failure(Exception("Ошибка gh CLI: $nameOnlyOutput"))
            }

            // Парсинг списка файлов
            val fileNames = nameOnlyOutput.trim().lines().filter { it.isNotBlank() }

            if (fileNames.isEmpty()) {
                return Result.failure(Exception("PR не содержит изменений"))
            }

            // Получить статусы файлов через git diff
            val gitStatusProcess = ProcessBuilder(
                "git", "diff", "--name-status",
                "origin/main...HEAD"
            )
                .directory(File(repoPath))
                .redirectErrorStream(false)
                .start()

            val gitStatusOutput = gitStatusProcess.inputStream.bufferedReader().readText()
            gitStatusProcess.waitFor()

            // Создать map статусов файлов
            val fileStatusMap = mutableMapOf<String, String>()
            gitStatusOutput.trim().lines().forEach { line ->
                val parts = line.split("\t", limit = 2)
                if (parts.size == 2) {
                    fileStatusMap[parts[1].trim()] = parts[0].trim()
                }
            }

            val changedFiles = mutableListOf<ChangedFile>()
            var totalAdditions = 0
            var totalDeletions = 0

            for (filePath in fileNames) {
                // Фильтр по расширениям
                val extension = filePath.substringAfterLast('.', "")
                if (extension !in Config.SUPPORTED_EXTENSIONS) {
                    logger.debug("Пропуск файла $filePath: неподдерживаемое расширение")
                    continue
                }

                // Определить тип изменения
                val statusChar = fileStatusMap[filePath] ?: "M"
                val changeType = when {
                    statusChar.startsWith("A") -> ChangeType.ADD
                    statusChar.startsWith("D") -> ChangeType.DELETE
                    else -> ChangeType.MODIFY
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

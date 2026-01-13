package review

/**
 * Результат получения diff PR
 */
data class DiffResult(
    val files: List<ChangedFile>,
    val additionsCount: Int,
    val deletionsCount: Int
)

/**
 * Информация об измененном файле
 */
data class ChangedFile(
    val path: String,
    val changeType: ChangeType,
    val content: String
)

/**
 * Тип изменения файла
 */
enum class ChangeType {
    ADD,    // Новый файл
    MODIFY, // Изменен
    DELETE  // Удален
}

/**
 * Результат анализа PR
 */
data class ReviewResult(
    val comment: String,
    val filesAnalyzed: Int
)

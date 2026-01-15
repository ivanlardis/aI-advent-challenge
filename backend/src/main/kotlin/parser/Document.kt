package parser

/**
 * Представление проиндексированного документа
 */
data class Document(
    val content: String,
    val filePath: String,
    val metadata: Map<String, String> = emptyMap()
)

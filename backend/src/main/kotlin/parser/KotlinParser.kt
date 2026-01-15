package parser

import java.io.File

/**
 * Парсер для Kotlin файлов (.kt)
 */
class KotlinParser : FileParser {
    override fun parse(file: File): Document {
        val content = file.readText()

        val metadata = mapOf(
            "type" to "kotlin",
            "extension" to "kt",
            "size" to file.length().toString()
        )

        return Document(
            content = content,
            filePath = file.absolutePath,
            metadata = metadata
        )
    }

    override fun supports(file: File): Boolean {
        return file.extension == "kt"
    }
}

package parser

import java.io.File

/**
 * Парсер для Markdown файлов (.md)
 */
class MarkdownParser : FileParser {
    override fun parse(file: File): Document {
        val content = file.readText()

        val metadata = mapOf(
            "type" to "markdown",
            "extension" to "md",
            "size" to file.length().toString()
        )

        return Document(
            content = content,
            filePath = file.absolutePath,
            metadata = metadata
        )
    }

    override fun supports(file: File): Boolean {
        return file.extension == "md"
    }
}

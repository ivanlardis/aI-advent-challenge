package parser

import java.io.File

/**
 * Парсер для Java файлов (.java)
 */
class JavaParser : FileParser {
    override fun parse(file: File): Document {
        val content = file.readText()

        val metadata = mapOf(
            "type" to "java",
            "extension" to "java",
            "size" to file.length().toString()
        )

        return Document(
            content = content,
            filePath = file.absolutePath,
            metadata = metadata
        )
    }

    override fun supports(file: File): Boolean {
        return file.extension == "java"
    }
}

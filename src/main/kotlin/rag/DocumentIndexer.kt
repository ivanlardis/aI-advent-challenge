package rag

import config.Config
import parser.*
import rag.embeddings.Vectorizer
import java.io.File

/**
 * Индексатор документов из директории проекта.
 */
class DocumentIndexer(
    private val vectorizer: Vectorizer,
    private val vectorStore: InMemoryVectorStore
) {
    private val parsers: List<FileParser> = listOf(
        KotlinParser(),
        JavaParser(),
        MarkdownParser()
    )

    data class IndexStats(
        val totalFiles: Int,
        val kotlinFiles: Int,
        val javaFiles: Int,
        val markdownFiles: Int,
        val totalTokens: Int = 0
    )

    /**
     * Индексировать директорию (однопроходная индексация для dense-векторов).
     */
    fun indexDirectory(homeDir: String, onProgress: ((String) -> Unit)? = null): IndexStats {
        val homeDirFile = File(homeDir)
        if (!homeDirFile.exists() || !homeDirFile.isDirectory) {
            throw IllegalArgumentException("Директория не существует: $homeDir")
        }

        vectorStore.clear()

        val files = collectFiles(homeDirFile)
        onProgress?.invoke("Найдено файлов: ${files.size}")
        onProgress?.invoke("Индексация документов...")

        var kotlinCount = 0
        var javaCount = 0
        var markdownCount = 0

        files.forEachIndexed { index, file ->
            try {
                val parser = findParser(file)
                if (parser != null) {
                    val doc = parser.parse(file)
                    val vector = vectorizer.vectorize(doc.content)
                    vectorStore.addDocument(doc, vector)

                    when (file.extension) {
                        "kt" -> kotlinCount++
                        "java" -> javaCount++
                        "md" -> markdownCount++
                    }

                    if ((index + 1) % 5 == 0) {
                        onProgress?.invoke("Обработано: ${index + 1}/${files.size}")
                    }
                }
            } catch (e: Exception) {
                onProgress?.invoke("Ошибка при индексации ${file.name}: ${e.message}")
            }
        }

        onProgress?.invoke("Индексация завершена!")

        return IndexStats(
            totalFiles = files.size,
            kotlinFiles = kotlinCount,
            javaFiles = javaCount,
            markdownFiles = markdownCount
        )
    }

    private fun collectFiles(dir: File): List<File> {
        val result = mutableListOf<File>()

        dir.walkTopDown()
            .filter { it.isFile }
            .filter { it.extension in Config.SUPPORTED_EXTENSIONS }
            .forEach { result.add(it) }

        return result
    }

    private fun findParser(file: File): FileParser? {
        return parsers.firstOrNull { it.supports(file) }
    }
}

package rag

import config.Config
import parser.*
import java.io.File

/**
 * Индексатор документов из директории проекта
 */
class DocumentIndexer(
    private val vectorizer: TfIdfVectorizer,
    private val vectorStore: InMemoryVectorStore
) {
    private val parsers: List<FileParser> = listOf(
        KotlinParser(),
        JavaParser(),
        MarkdownParser()
    )

    /**
     * Статистика индексации
     */
    data class IndexStats(
        val totalFiles: Int,
        val kotlinFiles: Int,
        val javaFiles: Int,
        val markdownFiles: Int,
        val totalTokens: Int
    )

    /**
     * Индексировать директорию
     */
    fun indexDirectory(homeDir: String, onProgress: ((String) -> Unit)? = null): IndexStats {
        val homeDirFile = File(homeDir)
        if (!homeDirFile.exists() || !homeDirFile.isDirectory) {
            throw IllegalArgumentException("Директория не существует: $homeDir")
        }

        // Очистка предыдущих данных
        vectorizer.clear()
        vectorStore.clear()

        // Сбор всех файлов
        val files = collectFiles(homeDirFile)
        onProgress?.invoke("Найдено файлов: ${files.size}")

        // Первый проход: обновление IDF
        onProgress?.invoke("Вычисление статистики...")
        files.forEach { file ->
            try {
                val parser = findParser(file)
                if (parser != null) {
                    val doc = parser.parse(file)
                    val tokens = vectorizer.tokenize(doc.content)
                    vectorizer.updateDocumentFrequency(tokens)
                }
            } catch (e: Exception) {
                onProgress?.invoke("Ошибка при обработке ${file.name}: ${e.message}")
            }
        }

        // Второй проход: векторизация и индексация
        onProgress?.invoke("Индексация документов...")
        var kotlinCount = 0
        var javaCount = 0
        var markdownCount = 0
        var totalTokens = 0

        files.forEach { file ->
            try {
                val parser = findParser(file)
                if (parser != null) {
                    val doc = parser.parse(file)
                    val vector = vectorizer.vectorize(doc.content)
                    vectorStore.addDocument(doc, vector)

                    totalTokens += vectorizer.tokenize(doc.content).size

                    when (file.extension) {
                        "kt" -> kotlinCount++
                        "java" -> javaCount++
                        "md" -> markdownCount++
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
            markdownFiles = markdownCount,
            totalTokens = totalTokens
        )
    }

    /**
     * Рекурсивно собрать все поддерживаемые файлы из директории
     */
    private fun collectFiles(dir: File): List<File> {
        val result = mutableListOf<File>()

        dir.walkTopDown()
            .filter { it.isFile }
            .filter { it.extension in Config.SUPPORTED_EXTENSIONS }
            .forEach { result.add(it) }

        return result
    }

    /**
     * Найти подходящий парсер для файла
     */
    private fun findParser(file: File): FileParser? {
        return parsers.firstOrNull { it.supports(file) }
    }
}

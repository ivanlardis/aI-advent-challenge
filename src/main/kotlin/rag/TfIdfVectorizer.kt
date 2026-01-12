package rag

import kotlin.math.log10
import kotlin.math.sqrt

/**
 * TF-IDF векторизатор для преобразования текста в векторы
 */
class TfIdfVectorizer {
    private val documentFrequency = mutableMapOf<String, Int>()
    private var totalDocuments = 0

    /**
     * Токенизация текста
     */
    fun tokenize(text: String): List<String> {
        return text
            .lowercase()
            .replace(Regex("[^a-zа-я0-9\\s]"), " ")
            .split(Regex("\\s+"))
            .filter { it.length > 2 }
    }

    /**
     * Вычисление частоты термов (TF) в документе
     */
    fun computeTermFrequency(tokens: List<String>): Map<String, Double> {
        val termCount = tokens.groupingBy { it }.eachCount()
        val maxFreq = termCount.values.maxOrNull() ?: 1

        return termCount.mapValues { (_, count) ->
            count.toDouble() / maxFreq
        }
    }

    /**
     * Обновление частоты документов (DF) для коллекции
     */
    fun updateDocumentFrequency(tokens: List<String>) {
        val uniqueTokens = tokens.toSet()
        uniqueTokens.forEach { token ->
            documentFrequency[token] = (documentFrequency[token] ?: 0) + 1
        }
        totalDocuments++
    }

    /**
     * Вычисление обратной частоты документов (IDF)
     */
    fun computeIdf(token: String): Double {
        val df = documentFrequency[token] ?: 0
        if (df == 0) {
            // Для неизвестных токенов используем максимальный IDF (сглаживание)
            return if (totalDocuments > 0) {
                log10(totalDocuments.toDouble() + 1.0)
            } else {
                1.0
            }
        }

        // Добавляем сглаживание +1 для избежания деления на 0
        return log10((totalDocuments.toDouble() + 1.0) / (df + 1.0))
    }

    /**
     * Преобразование текста в TF-IDF вектор
     */
    fun vectorize(text: String): Map<String, Double> {
        val tokens = tokenize(text)
        val tf = computeTermFrequency(tokens)

        return tf.mapValues { (token, tfValue) ->
            tfValue * computeIdf(token)
        }
    }

    /**
     * Вычисление косинусного сходства между двумя векторами
     */
    fun cosineSimilarity(vec1: Map<String, Double>, vec2: Map<String, Double>): Double {
        if (vec1.isEmpty() || vec2.isEmpty()) return 0.0

        val dotProduct = vec1.entries.sumOf { (token, value) ->
            value * (vec2[token] ?: 0.0)
        }

        val magnitude1 = sqrt(vec1.values.sumOf { it * it })
        val magnitude2 = sqrt(vec2.values.sumOf { it * it })

        if (magnitude1 == 0.0 || magnitude2 == 0.0) return 0.0

        return dotProduct / (magnitude1 * magnitude2)
    }

    /**
     * Очистка всех данных
     */
    fun clear() {
        documentFrequency.clear()
        totalDocuments = 0
    }
}

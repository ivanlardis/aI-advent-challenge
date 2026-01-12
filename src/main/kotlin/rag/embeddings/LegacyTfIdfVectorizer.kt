package rag.embeddings

import kotlin.math.log10
import kotlin.math.sqrt

/**
 * Legacy TF-IDF векторизатор (оставлен для сравнения и тестов).
 */
class LegacyTfIdfVectorizer(
    private val maxVocabularySize: Int = 10_000
) : Vectorizer {

    private val documentFrequency = mutableMapOf<String, Int>()
    private val vocabulary = mutableMapOf<String, Int>()
    private var totalDocuments = 0

    override val dimension: Int = maxVocabularySize

    fun tokenize(text: String): List<String> {
        return text
            .lowercase()
            .replace(Regex("[^a-zа-я0-9\\s]"), " ")
            .split(Regex("\\s+"))
            .filter { it.length > 2 }
    }

    fun computeTermFrequency(tokens: List<String>): Map<String, Double> {
        val termCount = tokens.groupingBy { it }.eachCount()
        val maxFreq = termCount.values.maxOrNull() ?: 1

        return termCount.mapValues { (_, count) ->
            count.toDouble() / maxFreq
        }
    }

    fun updateDocumentFrequency(tokens: List<String>) {
        val uniqueTokens = tokens.toSet()
        uniqueTokens.forEach { token ->
            documentFrequency[token] = (documentFrequency[token] ?: 0) + 1
        }
        totalDocuments++
    }

    private fun computeIdf(token: String): Double {
        val df = documentFrequency[token] ?: 0
        if (df == 0) {
            return if (totalDocuments > 0) {
                log10(totalDocuments.toDouble() + 1.0)
            } else {
                1.0
            }
        }

        return log10((totalDocuments.toDouble() + 1.0) / (df + 1.0))
    }

    override fun vectorize(text: String): FloatArray {
        val sparseVec = vectorizeToSparse(text)
        val denseVec = FloatArray(dimension)

        sparseVec.forEach { (token, value) ->
            val idx = vocabulary.getOrPut(token) { vocabulary.size }
            if (idx < dimension) {
                denseVec[idx] = value.toFloat()
            }
        }

        return denseVec
    }

    private fun vectorizeToSparse(text: String): Map<String, Double> {
        val tokens = tokenize(text)
        val tf = computeTermFrequency(tokens)

        return tf.mapValues { (token, tfValue) ->
            tfValue * computeIdf(token)
        }
    }

    override fun cosineSimilarity(vec1: FloatArray, vec2: FloatArray): Double {
        return super.cosineSimilarity(vec1, vec2)
    }

    override fun close() {
        // Нет ресурсов для освобождения
    }

    fun clear() {
        documentFrequency.clear()
        vocabulary.clear()
        totalDocuments = 0
    }
}

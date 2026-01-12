package rag.embeddings

/**
 * Общий интерфейс для векторизаторов текста.
 */
interface Vectorizer : AutoCloseable {
    /** Размерность выходных векторов. */
    val dimension: Int

    /** Построить вектор для заданного текста. */
    fun vectorize(text: String): FloatArray

    /** Косинусное сходство между двумя векторами. */
    fun cosineSimilarity(vec1: FloatArray, vec2: FloatArray): Double {
        require(vec1.size == vec2.size) { "Vectors must have same dimension" }

        var dot = 0.0
        var norm1 = 0.0
        var norm2 = 0.0

        for (i in vec1.indices) {
            val v1 = vec1[i].toDouble()
            val v2 = vec2[i].toDouble()
            dot += v1 * v2
            norm1 += v1 * v1
            norm2 += v2 * v2
        }

        val denom = kotlin.math.sqrt(norm1) * kotlin.math.sqrt(norm2)
        return if (denom == 0.0) 0.0 else dot / denom
    }

    override fun close() {
        // По умолчанию ресурсов нет
    }
}

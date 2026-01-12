package rag

import parser.Document
import rag.embeddings.Vectorizer

/**
 * In-memory хранилище для документов и их dense-векторов.
 */
class InMemoryVectorStore(private val vectorizer: Vectorizer) {
    private val documents = mutableListOf<Document>()
    private val vectors = mutableListOf<FloatArray>()

    fun addDocument(doc: Document, vector: FloatArray) {
        documents.add(doc)
        vectors.add(vector)
    }

    fun search(queryVector: FloatArray, topK: Int, minSimilarity: Double = 0.0): List<SearchResult> {
        if (documents.isEmpty()) return emptyList()

        val results = documents.indices.map { idx ->
            val doc = documents[idx]
            val vec = vectors[idx]
            val similarity = vectorizer.cosineSimilarity(queryVector, vec)

            SearchResult(doc, similarity)
        }

        return results
            .filter { it.score >= minSimilarity }
            .sortedByDescending { it.score }
            .take(topK)
    }

    fun clear() {
        documents.clear()
        vectors.clear()
    }

    fun size(): Int = documents.size

    fun getAllDocuments(): List<Document> = documents.toList()
}

package rag

import config.Config
import rag.embeddings.Vectorizer

/**
 * RAG сервис для поиска релевантных документов.
 */
class RagService(
    private val vectorizer: Vectorizer,
    private val vectorStore: InMemoryVectorStore
) {
    fun search(query: String): List<SearchResult> {
        val queryVector = vectorizer.vectorize(query)

        return vectorStore.search(
            queryVector = queryVector,
            topK = Config.RAG_TOP_K,
            minSimilarity = Config.RAG_MIN_SIMILARITY
        )
    }

    fun getIndexSize(): Int = vectorStore.size()
}

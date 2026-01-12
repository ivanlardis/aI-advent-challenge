package rag

import config.Config

/**
 * RAG сервис для поиска релевантных документов
 */
class RagService(
    private val vectorizer: TfIdfVectorizer,
    private val vectorStore: InMemoryVectorStore
) {
    /**
     * Поиск релевантных документов по запросу пользователя
     */
    fun search(query: String): List<SearchResult> {
        val queryVector = vectorizer.vectorize(query)

        return vectorStore.search(
            queryVector = queryVector,
            topK = Config.RAG_TOP_K,
            minSimilarity = Config.RAG_MIN_SIMILARITY
        )
    }

    /**
     * Получить количество проиндексированных документов
     */
    fun getIndexSize(): Int = vectorStore.size()
}

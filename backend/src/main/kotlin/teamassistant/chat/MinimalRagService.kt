package teamassistant.chat

import rag.SearchResult

/**
 * Minimal RAG service interface for ChatService.
 * Returns empty results for now - full RAG integration requires proper setup.
 *
 * TODO: Integrate proper RagService when TeamAssistantCommand is updated
 */
class MinimalRagService {
    suspend fun search(query: String): List<SearchResult> {
        // Return empty results for now
        // Full RAG integration will be added later
        return emptyList()
    }
}

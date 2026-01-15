package teamassistant.scoring

import dto.GitHubIssue
import rag.RagService
import rag.SearchResult
import org.slf4j.LoggerFactory

/**
 * Scorer на основе релевантности документации (RAG)
 * Использует существующий RagService для поиска похожих документов
 */
class RagRelevanceScorer(
    private val ragService: RagService
) {
    private val logger = LoggerFactory.getLogger(RagRelevanceScorer::class.java)

    /**
     * Рассчитать score на основе RAG поиска
     * Возвращает максимальную схожесть среди результатов
     */
    suspend fun score(issue: GitHubIssue, topK: Int = 5): Double {
        return try {
            // Формируем запрос из title и body issue
            val query = buildString {
                append(issue.title)
                if (!issue.body.isNullOrBlank()) {
                    append("\n")
                    append(issue.body)
                }
            }

            // Ищем релевантные документы
            val results: List<SearchResult> = ragService.search(query)

            if (results.isEmpty()) {
                logger.debug("No RAG results for issue #${issue.number}")
                return 0.0
            }

            // Берем максимальный score (бинарная релевантность)
            val maxScore = results.take(topK).maxOfOrNull { it.score } ?: 0.0

            logger.debug("RAG score for issue #${issue.number}: $maxScore (from ${results.size} results)")
            maxScore
        } catch (e: Exception) {
            logger.warn("Failed to calculate RAG score for issue #${issue.number}", e)
            0.0
        }
    }

    /**
     * Рассчитать score на основе среднего значения релевантности
     */
    suspend fun scoreAverage(issue: GitHubIssue, topK: Int = 5): Double {
        return try {
            val query = buildString {
                append(issue.title)
                if (!issue.body.isNullOrBlank()) {
                    append("\n")
                    append(issue.body)
                }
            }

            val results: List<SearchResult> = ragService.search(query)

            if (results.isEmpty()) return 0.0

            val avgScore = results.take(topK).map { it.score }.average()
            avgScore
        } catch (e: Exception) {
            logger.warn("Failed to calculate average RAG score for issue #${issue.number}", e)
            0.0
        }
    }
}

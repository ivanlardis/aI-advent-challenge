package teamassistant.scoring

import config.TeamAssistantConfig
import dto.GitHubCommit
import dto.GitHubIssue
import dto.ScoredIssue
import org.slf4j.LoggerFactory
import rag.RagService

/**
 * Calculator для приоритизации задач
 * Комбинирует три метрики с весами:
 * - Commit Activity (по умолчанию 0.6)
 * - Recency (по умолчанию 0.3)
 * - RAG Relevance (по умолчанию 0.1)
 */
class PriorityCalculator(
    private val commitScorer: CommitActivityScorer,
    private val recencyScorer: RecencyScorer,
    private val ragScorer: RagRelevanceScorer?,
    private val config: TeamAssistantConfig
) {
    private val logger = LoggerFactory.getLogger(PriorityCalculator::class.java)

    private val weights = config.scoring.weights

    /**
     * Рассчитать приоритет для одной задачи
     */
    suspend fun calculateScore(
        issue: GitHubIssue,
        linkedCommits: List<GitHubCommit>
    ): ScoredIssue {
        // 1. Commit Activity Score
        val commitScore = commitScorer.score(issue, linkedCommits)

        // 2. Recency Score
        val recencyScore = recencyScorer.score(issue)

        // 3. RAG Relevance Score (опционально)
        val ragScore = if (ragScorer != null) {
            ragScorer.score(issue)
        } else {
            0.0
        }

        // 4. Total weighted score
        val priorityScore = calculateWeightedScore(commitScore, recencyScore, ragScore)

        return ScoredIssue(
            issue = issue,
            priorityScore = priorityScore,
            commitCount = linkedCommits.size,
            commitScore = commitScore,
            recencyScore = recencyScore,
            ragScore = ragScore,
            linkedCommits = linkedCommits
        )
    }

    /**
     * Рассчитать приоритеты для списка задач
     */
    suspend fun calculateScores(
        issuesWithCommits: Map<GitHubIssue, List<GitHubCommit>>
    ): List<ScoredIssue> {
        logger.info("Calculating scores for ${issuesWithCommits.size} issues")

        val results = issuesWithCommits.map { (issue, commits) ->
            calculateScore(issue, commits)
        }

        logger.info("Calculated scores: min=${results.minOfOrNull { it.priorityScore }}, " +
                   "max=${results.maxOfOrNull { it.priorityScore }}")

        return results
    }

    /**
     * Рассчитать взвешенный score на основе трех компонент
     */
    private fun calculateWeightedScore(
        commitScore: Double,
        recencyScore: Double,
        ragScore: Double
    ): Double {
        return commitScore * weights.commitActivity +
               recencyScore * weights.recency +
               ragScore * weights.ragRelevance
    }

    /**
     * Валидировать веса (должны суммироваться в 1.0)
     */
    fun validateWeights(): Boolean {
        return config.scoring.validateWeights()
    }

    companion object {
        /**
         * Создать calculator с настройками по умолчанию
         */
        fun createDefault(
            ragService: RagService?,
            config: TeamAssistantConfig
        ): PriorityCalculator {
            val commitScorer = CommitActivityScorer(config.github.maxCommits)
            val recencyScorer = RecencyScorer()
            val ragScorer = if (ragService != null) {
                RagRelevanceScorer(ragService)
            } else {
                null
            }

            return PriorityCalculator(
                commitScorer = commitScorer,
                recencyScorer = recencyScorer,
                ragScorer = ragScorer,
                config = config
            )
        }
    }
}

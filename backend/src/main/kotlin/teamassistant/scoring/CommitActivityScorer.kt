package teamassistant.scoring

import dto.GitHubCommit
import dto.GitHubIssue
import kotlin.math.max
import kotlin.math.min

/**
 * Scorer на основе активности коммитов
 * Чем больше коммитов связано с issue, тем выше приоритет
 * Нормализация: 0 commits → 0.0, 50+ commits → 1.0
 */
class CommitActivityScorer(
    private val maxCommitsForNormalization: Int = 50
) {
    /**
     * Рассчитать score на основе количества связанных коммитов
     */
    fun score(issue: GitHubIssue, linkedCommits: List<GitHubCommit>): Double {
        val commitCount = linkedCommits.size
        val normalized = min(commitCount.toDouble() / maxCommitsForNormalization, 1.0)

        return normalized
    }

    /**
     * Рассчитать score на основе просто количества коммитов
     */
    fun scoreFromCount(commitCount: Int): Double {
        val normalized = min(commitCount.toDouble() / maxCommitsForNormalization, 1.0)
        return normalized
    }
}

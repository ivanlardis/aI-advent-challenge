package teamassistant.scoring

import dto.GitHubIssue
import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlin.math.exp
import kotlin.math.max
import kotlin.time.Duration
import kotlin.time.Duration.Companion.days

/**
 * Scorer на основе свежести (recency) задачи
 * Чем более недавно была активность, тем выше приоритет
 * Использует exponential decay: e^(-days/30)
 */
class RecencyScorer(
    private val halfLifeDays: Int = 30
) {
    /**
     * Рассчитать score на основе времени последнего обновления
     */
    fun score(issue: GitHubIssue): Double {
        return try {
            val updatedAt = Instant.parse(issue.updatedAt)
            val now = Clock.System.now()
            val daysSinceUpdate = now - updatedAt

            // Exponential decay: newer updates have higher score
            // 0 days → 1.0, 30 days → ~0.37, 60 days → ~0.14
            val daysPassed = daysSinceUpdate.inWholeDays.toInt()
            val decay = exp(-daysPassed.toDouble() / halfLifeDays)

            decay
        } catch (e: Exception) {
            // Если не смогли распарсить дату, возвращаем низкий score
            0.0
        }
    }

    /**
     * Рассчитать score на основе возраста задачи (created_at)
     */
    fun scoreByAge(issue: GitHubIssue): Double {
        return try {
            val createdAt = Instant.parse(issue.createdAt)
            val now = Clock.System.now()
            val age = now - createdAt

            // Older issues have lower score
            val daysOld = age.inWholeDays.toInt()
            val decay = exp(-daysOld.toDouble() / halfLifeDays)

            decay
        } catch (e: Exception) {
            0.0
        }
    }
}

package config

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class TeamAssistantConfig(
    val github: GitHubConfig = GitHubConfig(),
    val scoring: ScoringConfig = ScoringConfig(),
    val cache: CacheConfig = CacheConfig(),
    val server: ServerConfig = ServerConfig()
) {
    @Serializable
    data class GitHubConfig(
        val owner: String = "",
        val repo: String = "",
        val maxIssues: Int = 30,
        val maxCommits: Int = 50
    )

    @Serializable
    data class ScoringConfig(
        val weights: Weights = Weights()
    ) {
        @Serializable
        data class Weights(
            val commitActivity: Double = 0.6,
            val recency: Double = 0.3,
            val ragRelevance: Double = 0.1
        )

        fun validateWeights(): Boolean {
            return (weights.commitActivity + weights.recency + weights.ragRelevance).compareTo(1.0) == 0
        }
    }

    @Serializable
    data class CacheConfig(
        val enabled: Boolean = true,
        val ttlMinutes: Int = 60,
        val filePath: String = ".team-assistant/cache.json"
    )

    @Serializable
    data class ServerConfig(
        val port: Int = 8080,
        val host: String = "0.0.0.0"
    )
}

@Serializable
data class CachedIssuesData(
    val issues: List<CachedIssue>,
    @SerialName("last_updated")
    val lastUpdated: String
)

@Serializable
data class CachedIssue(
    val number: Int,
    val title: String,
    val state: String,
    @SerialName("created_at")
    val createdAt: String,
    @SerialName("updated_at")
    val updatedAt: String,
    @SerialName("priority_score")
    val priorityScore: Double,
    @SerialName("commit_count")
    val commitCount: Int,
    @SerialName("rag_relevance")
    val ragRelevance: Double
)

fun CachedIssue.toScoredIssue(): dto.ScoredIssue {
    return dto.ScoredIssue(
        issue = dto.GitHubIssue(
            id = 0,
            number = number,
            title = title,
            body = null,
            state = state,
            createdAt = createdAt,
            updatedAt = updatedAt,
            user = dto.GitHubUser(0, "", null),
            assignee = null,
            milestone = null
        ),
        priorityScore = priorityScore,
        commitCount = commitCount,
        commitScore = 0.0,
        recencyScore = 0.0,
        ragScore = ragRelevance
    )
}

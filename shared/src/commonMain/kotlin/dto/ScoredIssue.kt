package dto

import kotlinx.serialization.Serializable

@Serializable
data class ScoredIssue(
    val issue: GitHubIssue,
    val priorityScore: Double,
    val commitCount: Int,
    val commitScore: Double,
    val recencyScore: Double,
    val ragScore: Double,
    val ragDocuments: List<String> = emptyList(),
    val linkedCommits: List<GitHubCommit> = emptyList()
)

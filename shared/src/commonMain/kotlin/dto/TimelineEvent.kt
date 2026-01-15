package dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class TimelineEvent(
    val id: String,
    val event: String,
    @SerialName("created_at")
    val createdAt: String,
    val actor: GitHubUser?,
    @SerialName("issue_url")
    val issueUrl: String?,
    // For commit referenced events
    @SerialName("commit_id")
    val commitId: String?,
    // For cross-referenced events
    val source: IssueSource?
)

@Serializable
data class IssueSource(
    val issue: GitHubIssue?,
    val type: String
)

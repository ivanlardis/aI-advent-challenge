package dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GitHubIssue(
    val id: Long,
    val number: Int,
    val title: String,
    val body: String? = null,
    val state: String,
    @SerialName("created_at")
    val createdAt: String,
    @SerialName("updated_at")
    val updatedAt: String,
    val user: GitHubUser,
    val labels: List<GitHubLabel> = emptyList(),
    val assignee: GitHubUser? = null,
    val milestone: GitHubMilestone? = null,
    val comments: Int = 0
)

@Serializable
data class GitHubUser(
    val id: Long,
    val login: String,
    @SerialName("avatar_url")
    val avatarUrl: String?
)

@Serializable
data class GitHubLabel(
    val id: Long,
    val name: String,
    val color: String
)

@Serializable
data class GitHubMilestone(
    val id: Long,
    val title: String,
    val state: String,
    @SerialName("due_on")
    val dueOn: String?
)

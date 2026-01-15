package dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GitHubCommit(
    val sha: String,
    @SerialName("commit")
    val commitDetails: CommitDetails,
    val author: GitHubAuthor?
)

@Serializable
data class CommitDetails(
    val message: String,
    val author: CommitAuthor
)

@Serializable
data class CommitAuthor(
    val name: String,
    val email: String,
    val date: String
)

@Serializable
data class GitHubAuthor(
    val id: Long,
    val login: String,
    @SerialName("avatar_url")
    val avatarUrl: String?
)

package teamassistant.github

import dto.*
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.slf4j.LoggerFactory

class GitHubClient(
    private val token: String,
    private val client: HttpClient = HttpClient(CIO) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
            })
        }
        expectSuccess = false // Handle errors manually
    }
) {
    private val logger = LoggerFactory.getLogger(GitHubClient::class.java)

    companion object {
        const val GITHUB_API_BASE = "https://api.github.com"
        const val GITHUB_API_VERSION = "2022-11-28"
    }

    /**
     * Получить список issues для репозитория
     * GET /repos/{owner}/{repo}/issues
     */
    suspend fun getIssues(
        owner: String,
        repo: String,
        state: String = "open",
        limit: Int = 30
    ): Result<List<GitHubIssue>> {
        return try {
            logger.debug("Fetching issues for $owner/$repo (state=$state, limit=$limit)")

            val response: List<GitHubIssue> = client.get("$GITHUB_API_BASE/repos/$owner/$repo/issues") {
                headers {
                    append("Authorization", "Bearer $token")
                    append("Accept", "application/vnd.github+json")
                    append("X-GitHub-Api-Version", GITHUB_API_VERSION)
                }
                parameter("state", state)
                parameter("per_page", limit.coerceAtMost(100))
                parameter("sort", "updated")
                parameter("direction", "desc")
            }.body()

            logger.info("Fetched ${response.size} issues for $owner/$repo")
            Result.success(response)
        } catch (e: Exception) {
            logger.error("Failed to fetch issues for $owner/$repo", e)
            Result.failure(e)
        }
    }

    /**
     * Получить timeline событий для issue
     * GET /repos/{owner}/{repo}/issues/{issue_number}/timeline
     */
    suspend fun getTimeline(
        owner: String,
        repo: String,
        issueNumber: Int
    ): Result<List<TimelineEvent>> {
        return try {
            logger.debug("Fetching timeline for $owner/$repo#$issueNumber")

            val response: List<TimelineEvent> = client.get("$GITHUB_API_BASE/repos/$owner/$repo/issues/$issueNumber/timeline") {
                headers {
                    append("Authorization", "Bearer $token")
                    append("Accept", "application/vnd.github+json")
                    append("X-GitHub-Api-Version", GITHUB_API_VERSION)
                }
                parameter("per_page", 100)
            }.body()

            logger.debug("Fetched ${response.size} timeline events for #$issueNumber")
            Result.success(response)
        } catch (e: Exception) {
            logger.error("Failed to fetch timeline for $owner/$repo#$issueNumber", e)
            Result.failure(e)
        }
    }

    /**
     * Получить коммиты репозитория
     * GET /repos/{owner}/{repo}/commits
     */
    suspend fun getCommits(
        owner: String,
        repo: String,
        since: String? = null,
        limit: Int = 50
    ): Result<List<GitHubCommit>> {
        return try {
            logger.debug("Fetching commits for $owner/$repo (limit=$limit)")

            val response: List<GitHubCommit> = client.get("$GITHUB_API_BASE/repos/$owner/$repo/commits") {
                headers {
                    append("Authorization", "Bearer $token")
                    append("Accept", "application/vnd.github+json")
                    append("X-GitHub-Api-Version", GITHUB_API_VERSION)
                }
                parameter("per_page", limit.coerceAtMost(100))
                parameter("since", since)
            }.body()

            logger.info("Fetched ${response.size} commits for $owner/$repo")
            Result.success(response)
        } catch (e: Exception) {
            logger.error("Failed to fetch commits for $owner/$repo", e)
            Result.failure(e)
        }
    }

    /**
     * Проверить rate limit статус
     * GET /rate_limit
     */
    suspend fun getRateLimitStatus(): Result<RateLimit> {
        return try {
            val response: RateLimitResponse = client.get("$GITHUB_API_BASE/rate_limit") {
                headers {
                    append("Authorization", "Bearer $token")
                    append("Accept", "application/vnd.github+json")
                    append("X-GitHub-Api-Version", GITHUB_API_VERSION)
                }
            }.body()

            Result.success(response.resources.core)
        } catch (e: Exception) {
            logger.error("Failed to fetch rate limit status", e)
            Result.failure(e)
        }
    }

    /**
     * Валидировать токен, получив информацию о пользователе
     */
    suspend fun validateToken(): Result<Boolean> {
        return try {
            // Try to fetch user info
            client.get("$GITHUB_API_BASE/user") {
                headers {
                    append("Authorization", "Bearer $token")
                    append("Accept", "application/vnd.github+json")
                    append("X-GitHub-Api-Version", GITHUB_API_VERSION)
                }
            }
            Result.success(true)
        } catch (e: Exception) {
            logger.error("Token validation failed", e)
            Result.failure(e)
        }
    }

    /**
     * Создать новый issue в репозитории
     * POST /repos/{owner}/{repo}/issues
     */
    suspend fun createIssue(
        owner: String,
        repo: String,
        issue: CreateIssueRequest
    ): Result<dto.GitHubIssue> {
        return try {
            logger.info("Creating issue in $owner/$repo: ${issue.title}")

            val json = Json { ignoreUnknownKeys = true }
            val response: dto.GitHubIssue = client.post("$GITHUB_API_BASE/repos/$owner/$repo/issues") {
                headers {
                    append("Authorization", "Bearer $token")
                    append("Accept", "application/vnd.github+json")
                    append("X-GitHub-Api-Version", GITHUB_API_VERSION)
                }
                setBody(json.encodeToString(issue))
                contentType(ContentType.Application.Json)
            }.body()

            logger.info("Created issue #${response.number} in $owner/$repo")
            Result.success(response)
        } catch (e: Exception) {
            logger.error("Failed to create issue in $owner/$repo", e)
            Result.failure(e)
        }
    }

    fun close() {
        client.close()
    }
}

@Serializable
data class CreateIssueRequest(
    val title: String,
    val body: String? = null,
    val labels: List<String> = emptyList()
)

@Serializable
data class RateLimitResponse(
    val resources: Resources
) {
    @Serializable
    data class Resources(
        val core: RateLimit
    )
}

@Serializable
data class RateLimit(
    val limit: Int,
    val remaining: Int,
    val reset: Long,
    val used: Int
)

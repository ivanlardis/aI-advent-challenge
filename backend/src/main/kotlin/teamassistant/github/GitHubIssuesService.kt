package teamassistant.github

import dto.GitHubCommit
import dto.GitHubIssue
import dto.TimelineEvent
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import org.slf4j.LoggerFactory
import java.util.regex.Pattern

/**
 * Сервис для работы с GitHub Issues и коммитами
 * Связывает issues с commits через Timeline API
 */
class GitHubIssuesService(
    private val client: GitHubClient
) {
    private val logger = LoggerFactory.getLogger(GitHubIssuesService::class.java)

    // Паттерн для поиска issue references в commit messages
    private val issueRefPattern = Pattern.compile("(?:fixes|fix|closes|close|refs|ref|related to)\\s+#(\\d+)", Pattern.CASE_INSENSITIVE)

    /**
     * Получить issues с их связанными коммитами
     */
    suspend fun fetchIssuesWithCommits(
        owner: String,
        repo: String,
        state: String = "open",
        limit: Int = 30
    ): Result<Map<GitHubIssue, List<GitHubCommit>>> {
        return coroutineScope {
            try {
                // 1. Fetch issues
                val issuesResult = client.getIssues(owner, repo, state, limit)
                if (issuesResult.isFailure) {
                    return@coroutineScope Result.failure(issuesResult.exceptionOrNull()!!)
                }

                val issues = issuesResult.getOrNull() ?: emptyList()
                logger.info("Fetched ${issues.size} issues for $owner/$repo")

                // 2. Fetch commits for repo
                val commitsResult = client.getCommits(owner, repo, limit = limit * 2)
                if (commitsResult.isFailure) {
                    logger.warn("Failed to fetch commits, continuing without commit linkage")
                    return@coroutineScope Result.success(issues.associateWith { emptyList() })
                }

                val commits = commitsResult.getOrNull() ?: emptyList()
                logger.info("Fetched ${commits.size} commits for $owner/$repo")

                // 3. Link commits to issues
                val issueToCommits = linkCommitsToIssues(issues, commits)
                logger.debug("Linked commits to issues: ${issueToCommits.size} issues with commits")

                Result.success(issueToCommits)
            } catch (e: Exception) {
                logger.error("Failed to fetch issues with commits", e)
                Result.failure(e)
            }
        }
    }

    /**
     * Получить детальную информацию об issue с timeline
     */
    suspend fun fetchIssueDetail(
        owner: String,
        repo: String,
        issueNumber: Int
    ): Result<Pair<GitHubIssue, List<TimelineEvent>>> {
        return try {
            // 1. Fetch issue (из списка issues берем конкретный)
            val issuesResult = client.getIssues(owner, repo, "all", 100)
            if (issuesResult.isFailure) {
                return Result.failure(issuesResult.exceptionOrNull()!!)
            }

            val issue = issuesResult.getOrNull()?.find { it.number == issueNumber }
                ?: return Result.failure(Exception("Issue #$issueNumber not found"))

            // 2. Fetch timeline
            val timelineResult = client.getTimeline(owner, repo, issueNumber)
            if (timelineResult.isFailure) {
                return Result.failure(timelineResult.exceptionOrNull()!!)
            }

            Result.success(Pair(issue, timelineResult.getOrNull()!!))
        } catch (e: Exception) {
            logger.error("Failed to fetch issue detail for #$issueNumber", e)
            Result.failure(e)
        }
    }

    /**
     * Связать коммиты с issues на основе:
     * 1. Timeline API (committed events)
     * 2. Commit messages (refs #123)
     */
    private fun linkCommitsToIssues(
        issues: List<GitHubIssue>,
        commits: List<GitHubCommit>
    ): Map<GitHubIssue, List<GitHubCommit>> {
        val issueMap = issues.associateBy { it.number }
        val result = mutableMapOf<GitHubIssue, MutableList<GitHubCommit>>()

        // Initialize with empty lists
        issues.forEach { result[it] = mutableListOf() }

        // Link commits based on message patterns
        commits.forEach { commit ->
            val message = commit.commitDetails.message
            val matcher = issueRefPattern.matcher(message)

            while (matcher.find()) {
                val issueNumber = matcher.group(1).toIntOrNull() ?: continue
                val issue = issueMap[issueNumber]

                if (issue != null) {
                    result[issue]?.add(commit)
                }
            }
        }

        return result.mapValues { it.value.toList() }
    }

    /**
     * Подсчитать количество коммитов для issue
     */
    fun countCommitsForIssue(
        issue: GitHubIssue,
        allCommits: List<GitHubCommit>
    ): Int {
        var count = 0
        val matcher = issueRefPattern.matcher("")

        allCommits.forEach { commit ->
            matcher.reset(commit.commitDetails.message)
            if (matcher.find()) {
                val issueNumber = matcher.group(1).toIntOrNull() ?: 0
                if (issueNumber == issue.number) {
                    count++
                }
            }
        }

        return count
    }
}

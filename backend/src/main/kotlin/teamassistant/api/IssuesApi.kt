package teamassistant.api

import config.TeamAssistantConfig
import dto.ScoredIssue
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import teamassistant.cache.IssueCache
import teamassistant.github.GitHubClient
import teamassistant.github.GitHubIssuesService
import teamassistant.scoring.PriorityCalculator
import kotlin.system.measureTimeMillis

class IssuesApi(
    private val config: TeamAssistantConfig,
    private val cache: IssueCache,
    private val calculatorProvider: () -> PriorityCalculator?,
    private val githubClientProvider: () -> GitHubClient?,
    private val authTokenProvider: () -> String? = { null }
) {
    private val lastUpdateTime = kotlin.time.TimeSource.Monotonic.markNow()

    fun install(routing: Routing) {
        routing.route("/api/issues") {
            // GET /api/issues - получить список задач с приоритетами
            get {
                try {
                    // Check config
                    val owner = config.github.owner
                    val repo = config.github.repo

                    if (owner.isBlank() || repo.isBlank()) {
                        call.respond(
                            HttpStatusCode.BadRequest,
                            ErrorResponse("invalid_config", "Please set github.owner and github.repo in config")
                        )
                        return@get
                    }

                    // Check cache first
                    val cachedData = cache.load()
                    if (cachedData != null) {
                        val issues = cache.fromCache(cachedData)
                        call.respond(issues.sortedByDescending { it.priorityScore })
                        return@get
                    }

                    // No cache - fetch and calculate
                    val issues = fetchAndScoreIssues()
                    call.respond(issues)
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.InternalServerError,
                        ErrorResponse("server_error", e.message)
                    )
                }
            }

            // GET /api/issues/{number} - получить детальную информацию о задаче
            get("/{number}") {
                try {
                    val number = call.parameters["number"]?.toIntOrNull()
                    if (number == null) {
                        call.respond(HttpStatusCode.BadRequest, ErrorResponse("invalid_issue_number"))
                        return@get
                    }

                    val owner = config.github.owner
                    val repo = config.github.repo

                    if (owner.isBlank() || repo.isBlank()) {
                        call.respond(
                            HttpStatusCode.BadRequest,
                            ErrorResponse("invalid_config", "GitHub owner/repo not configured")
                        )
                        return@get
                    }

                    val client = githubClientProvider()
                    if (client == null) {
                        call.respond(HttpStatusCode.InternalServerError, ErrorResponse("server_error"))
                        return@get
                    }

                    val service = GitHubIssuesService(client)
                    val result = service.fetchIssueDetail(owner, repo, number)

                    if (result.isFailure) {
                        call.respond(HttpStatusCode.NotFound, ErrorResponse("issue_not_found"))
                        return@get
                    }

                    val (issue, timeline) = result.getOrNull()!!
                    call.respond(mapOf(
                        "issue" to issue,
                        "timeline" to timeline
                    ))
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.InternalServerError,
                        ErrorResponse("server_error", e.message)
                    )
                }
            }

            // POST /api/issues/cache/refresh - обновить кэш
            post("/cache/refresh") {
                try {
                    // Clear cache
                    cache.clear()

                    // Fetch fresh data
                    val durationMs = measureTimeMillis {
                        val issues = fetchAndScoreIssues()
                        cache.save(issues)
                    }

                    call.respond(RefreshResponse(
                        issuesUpdated = config.github.maxIssues,
                        durationMs = durationMs
                    ))
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.InternalServerError,
                        ErrorResponse("server_error", e.message)
                    )
                }
            }
        }

        // GET /api/cache/stats - статистика кэша
        routing.get("/api/cache/stats") {
            val stats = cache.getCacheInfo()
            call.respond(CacheStatsResponse(
                exists = stats.exists,
                size = stats.size,
                lastUpdated = stats.lastUpdated,
                issuesCount = stats.issuesCount
            ))
        }
    }

    private suspend fun fetchAndScoreIssues(): List<ScoredIssue> {
        val client = githubClientProvider()!!
        val owner = config.github.owner
        val repo = config.github.repo

        // Fetch issues with commits
        val service = GitHubIssuesService(client)
        val issuesResult = service.fetchIssuesWithCommits(
            owner = owner,
            repo = repo,
            state = "open",
            limit = config.github.maxIssues
        )

        if (issuesResult.isFailure) {
            throw issuesResult.exceptionOrNull()!!
        }

        val issuesWithCommits = issuesResult.getOrNull()!!

        // Calculate scores
        val calculator = calculatorProvider() ?: PriorityCalculator.createDefault(null, config)
        val scoredIssues = calculator.calculateScores(issuesWithCommits)

        // Save to cache
        cache.save(scoredIssues)

        return scoredIssues.sortedByDescending { it.priorityScore }
    }
}

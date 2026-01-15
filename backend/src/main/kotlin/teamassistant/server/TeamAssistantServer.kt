package teamassistant.server

import config.TeamAssistantConfig
import io.ktor.http.ContentType
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.plugins.cors.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import org.slf4j.LoggerFactory
import teamassistant.api.AuthApi
import teamassistant.api.ChatApi
import teamassistant.api.ConfigApi
import teamassistant.api.IssuesApi
import teamassistant.cache.IssueCache
import teamassistant.chat.ChatService
import teamassistant.chat.SessionManager
import teamassistant.github.GitHubClient
import teamassistant.scoring.PriorityCalculator
import kotlin.time.Duration.Companion.minutes

class TeamAssistantServer(
    private val appConfig: TeamAssistantConfig
) {
    private val logger = LoggerFactory.getLogger(TeamAssistantServer::class.java)

    // Dependencies
    private var githubClient: GitHubClient? = null
    private val cache = IssueCache(
        cacheFilePath = appConfig.cache.filePath,
        ttl = appConfig.cache.ttlMinutes.toLong().minutes
    )
    private var priorityCalculator: PriorityCalculator? = null
    private lateinit var configApi: ConfigApi
    private lateinit var authApi: AuthApi
    private lateinit var issuesApi: IssuesApi
    private lateinit var chatApi: ChatApi

    fun start() {
        val server = embeddedServer(Netty, port = appConfig.server.port, host = appConfig.server.host) {
            install(ContentNegotiation) {
                json()
            }

            install(CORS) {
                anyHost() // Dev mode: allow all origins
            }

            routing {
                // Serve chat UI at root
                get("/") {
                    val htmlContent = java.io.File("backend/src/main/resources/web/chat.html").readText()
                    call.respondText(htmlContent, ContentType.Text.Html)
                }

                // Health check
                get("/health") {
                    call.respond(mapOf("status" to "ok", "service" to "team-assistant"))
                }

                // Initialize APIs
                configApi = ConfigApi(appConfig, appConfig.cache.filePath)
                authApi = AuthApi {
                    githubClient
                }

                issuesApi = IssuesApi(
                    config = appConfig,
                    cache = cache,
                    calculatorProvider = { priorityCalculator },
                    githubClientProvider = { githubClient },
                    authTokenProvider = { authApi.getCurrentToken() }
                )

                // Initialize Chat API components
                val sessionManager = SessionManager()

                // Create ChatService with minimal RAG integration (null for now)
                // RAG will be properly integrated when RagService is passed from CLI
                val chatService = ChatService(
                    ragService = teamassistant.chat.MinimalRagService(),
                    githubClient = githubClient!!,
                    priorityCalculator = priorityCalculator!!,
                    llmClient = llm.OpenRouterClient(),
                    config = appConfig
                )

                chatApi = ChatApi(chatService, sessionManager)

                // Install API routes
                configApi.install(this@routing)
                authApi.install(this@routing)
                issuesApi.install(this@routing)
                chatApi.install(this@routing)
            }
        }

        logger.info("Starting Team Assistant server on ${appConfig.server.host}:${appConfig.server.port}")
        logger.info("Config: maxIssues=${appConfig.github.maxIssues}, maxCommits=${appConfig.github.maxCommits}")
        logger.info("Scoring weights: commit=${appConfig.scoring.weights.commitActivity}, " +
                   "recency=${appConfig.scoring.weights.recency}, rag=${appConfig.scoring.weights.ragRelevance}")

        server.start(wait = true)
    }

    fun setGitHubClient(client: GitHubClient) {
        this.githubClient = client
        this.priorityCalculator = PriorityCalculator.createDefault(null, appConfig)
        logger.info("GitHub client initialized")
    }
}

package teamassistant.chat

import config.TeamAssistantConfig
import llm.Message
import llm.OpenRouterClient
import org.slf4j.LoggerFactory
import rag.SearchResult
import teamassistant.github.GitHubClient
import teamassistant.scoring.PriorityCalculator

/**
 * Main chat service that orchestrates RAG, GitHub, and LLM.
 */
class ChatService(
    private val ragService: MinimalRagService,
    private val githubClient: GitHubClient,
    private val priorityCalculator: PriorityCalculator,
    private val llmClient: OpenRouterClient,
    private val config: TeamAssistantConfig
) {
    private val logger = LoggerFactory.getLogger(ChatService::class.java)

    /**
     * Process a user message and generate a response.
     */
    suspend fun chat(userMessage: String, sessionHistory: List<ChatMessage>): ChatResponse {
        // 1. Recognize intent
        val intent = IntentRecognizer.recognize(userMessage)
        logger.info("📨 Message: $userMessage | Intent: $intent")

        // 2. Gather context based on intent
        val context = when (intent) {
            Intent.QUESTION -> ragContext(userMessage)
            Intent.ANALYZE_ISSUES, Intent.RECOMMEND -> githubIssuesContext()
            Intent.CREATE_ISSUE -> null  // No context needed for creating issues
            Intent.UNKNOWN -> null
        }

        // 3. Build prompt
        val prompt = PromptBuilder.build(userMessage, context, sessionHistory)

        // 4. Call LLM
        val messages = listOf(
            Message(role = "user", content = prompt)
        )

        val llmResponse = llmClient.chat(messages)

        // 5. Perform actions if needed
        var finalResponse = llmResponse
        if (intent == Intent.CREATE_ISSUE) {
            // Extract issue details from USER message and create issue
            val issueDetails = extractIssueDetails(userMessage)
            val issueCreated = createIssueFromDetails(issueDetails)
            if (issueCreated != null) {
                finalResponse = "✅ Создана задача: **#${issueCreated.number}: ${issueCreated.title}**\n\n${issueCreated.body ?: ""}"
            } else {
                finalResponse = "❌ Не удалось создать задачу. Проверьте логи сервера."
            }
        }

        return ChatResponse(
            response = finalResponse,
            intent = intent.name,
            timestamp = kotlinx.datetime.Clock.System.now().toString()
        )
    }

    /**
     * Gather RAG context for project questions.
     */
    private suspend fun ragContext(query: String): String {
        return try {
            val searchResults: List<SearchResult> = ragService.search(query)
            // Take only top 3 results to reduce token usage
            searchResults.take(3).joinToString("\n\n---\n\n") { result ->
                val doc: parser.Document = result.document
                "Файл: ${doc.filePath}\n${doc.content.take(500)}..." // Limit content size
            }
        } catch (e: Exception) {
            logger.error("Failed to gather RAG context", e)
            "Не удалось получить контекст из документации проекта: ${e.message}"
        }
    }

    /**
     * Gather GitHub issues context with priority scores.
     */
    private suspend fun githubIssuesContext(): String {
        return try {
            val result = githubClient.getIssues(
                owner = config.github.owner,
                repo = config.github.repo,
                state = "open",
                limit = config.github.maxIssues
            )

            if (result.isFailure) {
                return "Не удалось загрузить задачи: ${result.exceptionOrNull()?.message}"
            }

            val issues = result.getOrNull() ?: emptyList()

            // Create map with empty commit lists (will be scored with 0 commits)
            val issuesWithCommits = issues.associateWith { emptyList<dto.GitHubCommit>() }
            val scoredIssues = priorityCalculator.calculateScores(issuesWithCommits)

            // Take only top 5 to reduce token usage
            scoredIssues.take(5).joinToString("\n") { scored ->
                val issue = scored.issue
                val priorityPct = (scored.priorityScore * 100).toInt()
                "#${issue.number}: ${issue.title}\n" +
                "  Приоритет: $priorityPct% | Коммиты: ${scored.commitCount} | " +
                "Обновлено: ${formatDate(issue.updatedAt)}"
            }
        } catch (e: Exception) {
            logger.error("Failed to gather GitHub issues context", e)
            "Не удалось загрузить задачи: ${e.message}"
        }
    }

    /**
     * Extract issue details from user message.
     * Expected formats:
     * - "Создай задачу: добавить тестирование"
     * - "Create issue: Add logging"
     * - "Новая задача: реализовать авторизацию"
     */
    private fun extractIssueDetails(userMessage: String): IssueDetails {
        val patterns = listOf(
            Regex("""создай задач[ауы]:?\s*(.+)""", RegexOption.IGNORE_CASE),
            Regex("""create issue:?\s*(.+)""", RegexOption.IGNORE_CASE),
            Regex("""новая задача:?\s*(.+)""", RegexOption.IGNORE_CASE),
            Regex("""создать задачу:?\s*(.+)""", RegexOption.IGNORE_CASE)
        )

        for (pattern in patterns) {
            val match = pattern.find(userMessage)
            if (match != null) {
                val title = match.groupValues[1].trim().trimEnd('.', '!', '?')
                return IssueDetails(
                    title = title.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() },
                    body = "Создано через Team Assistant Chat"
                )
            }
        }

        // Fallback: use whole message as title
        return IssueDetails(
            title = userMessage.take(100).trimEnd('.', '!', '?'),
            body = "Создано через Team Assistant Chat"
        )
    }

    /**
     * Create an issue from extracted details.
     */
    private suspend fun createIssueFromDetails(details: IssueDetails): dto.GitHubIssue? {
        return try {
            logger.info("🔧 Creating issue: ${details.title}")
            val createRequest = teamassistant.github.CreateIssueRequest(
                title = details.title,
                body = details.body,
                labels = listOf("team-assistant")
            )

            val result = githubClient.createIssue(
                owner = config.github.owner,
                repo = config.github.repo,
                issue = createRequest
            )

            if (result.isSuccess) {
                val issue = result.getOrNull()
                logger.info("✅ Issue created: #${issue?.number} - ${issue?.title}")
                issue
            } else {
                logger.error("❌ Failed to create issue: ${result.exceptionOrNull()?.message}")
                null
            }
        } catch (e: Exception) {
            logger.error("❌ Failed to create issue", e)
            null
        }
    }

    private fun formatDate(dateString: String): String {
        return try {
            val instant = kotlinx.datetime.Instant.parse(dateString)
            val now = kotlinx.datetime.Clock.System.now()
            val diff = now - instant
            val days = diff.inWholeDays
            when {
                days == 0L -> "сегодня"
                days == 1L -> "вчера"
                days < 7L -> "$days дн. назад"
                else -> "$days дней назад"
            }
        } catch (e: Exception) {
            dateString
        }
    }
}

/**
 * Data class for extracted issue details.
 */
data class IssueDetails(
    val title: String,
    val body: String
)

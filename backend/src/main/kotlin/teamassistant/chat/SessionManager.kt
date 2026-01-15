package teamassistant.chat

import kotlinx.serialization.Serializable
import kotlinx.datetime.Clock
import java.util.concurrent.ConcurrentHashMap

/**
 * Manages chat sessions in memory.
 * Sessions are cleared on server restart.
 */
class SessionManager {
    private val sessions = ConcurrentHashMap<String, MutableList<ChatMessage>>()

    /**
     * Get or create a session for the given ID.
     * @return List of messages in the session
     */
    fun getOrCreateSession(sessionId: String): List<ChatMessage> {
        return sessions.getOrPut(sessionId) { mutableListOf() }.toList()
    }

    /**
     * Add a message to the session.
     */
    fun addMessage(sessionId: String, message: ChatMessage) {
        sessions.getOrPut(sessionId) { mutableListOf() }.add(message)
    }

    /**
     * Clear all messages in the session.
     */
    fun clearSession(sessionId: String) {
        sessions.remove(sessionId)
    }

    /**
     * Get all session IDs.
     */
    fun getAllSessionIds(): Set<String> = sessions.keys
}

/**
 * Chat message data class.
 */
@Serializable
data class ChatMessage(
    val role: String,  // "user" | "assistant" | "system"
    val content: String,
    val timestamp: String = Clock.System.now().toString()
)

/**
 * Chat request from client.
 */
@Serializable
data class ChatRequest(
    val message: String,
    val sessionId: String = "default"
)

/**
 * Chat response to client.
 */
@Serializable
data class ChatResponse(
    val response: String,
    val intent: String? = null,  // String representation of Intent enum
    val timestamp: String = Clock.System.now().toString()
)

/**
 * Intent enum for recognizing user requests.
 */
enum class Intent {
    QUESTION,           // Question about the project
    ANALYZE_ISSUES,     // Analyze issues/priorities
    CREATE_ISSUE,       // Create a new issue
    RECOMMEND,          // Get recommendations
    UNKNOWN
}

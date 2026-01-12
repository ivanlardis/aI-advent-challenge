package llm

import kotlinx.serialization.Serializable

/**
 * Сообщение для OpenRouter API
 */
@Serializable
data class Message(
    val role: String,
    val content: String
)

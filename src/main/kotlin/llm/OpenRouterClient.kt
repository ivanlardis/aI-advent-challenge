package llm

import config.Config
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * HTTP клиент для OpenRouter API
 */
class OpenRouterClient {
    private val client = HttpClient(CIO) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
            })
        }
    }

    @Serializable
    data class ChatRequest(
        val model: String,
        val messages: List<Message>
    )

    @Serializable
    data class ChatResponse(
        val id: String? = null,
        val choices: List<Choice>,
        val error: ErrorDetails? = null
    )

    @Serializable
    data class Choice(
        val message: Message,
        val finish_reason: String? = null
    )

    @Serializable
    data class ErrorDetails(
        val message: String,
        val code: String? = null
    )

    /**
     * Отправить запрос к OpenRouter API
     */
    suspend fun chat(messages: List<Message>): String {
        try {
            val response = client.post("${Config.OPENROUTER_BASE_URL}/chat/completions") {
                header("Authorization", "Bearer ${Config.OPENROUTER_API_KEY}")
                header("Content-Type", "application/json")
                setBody(
                    ChatRequest(
                        model = Config.OPENROUTER_MODEL,
                        messages = messages
                    )
                )
            }

            if (response.status != HttpStatusCode.OK) {
                return "Ошибка API: ${response.status}"
            }

            val chatResponse = response.body<ChatResponse>()

            if (chatResponse.error != null) {
                return "Ошибка: ${chatResponse.error.message}"
            }

            return chatResponse.choices.firstOrNull()?.message?.content
                ?: "Ответ не получен"

        } catch (e: Exception) {
            return "Ошибка при обращении к API: ${e.message}"
        }
    }

    /**
     * Закрыть HTTP клиент
     */
    fun close() {
        client.close()
    }
}

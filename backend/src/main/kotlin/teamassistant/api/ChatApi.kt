package teamassistant.api

import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.serialization.Serializable
import teamassistant.chat.ChatRequest
import teamassistant.chat.ChatResponse
import teamassistant.chat.ChatService
import teamassistant.chat.SessionManager

/**
 * Chat API endpoints for dialog-based assistant.
 */
class ChatApi(
    private val chatService: ChatService,
    private val sessionManager: SessionManager
) {
    fun install(route: Route) {
        route.route("/api/chat") {
            // POST /api/chat - Send message and get response
            post {
                try {
                    val request = call.receive<ChatRequest>()

                    // Get session history
                    val history = sessionManager.getOrCreateSession(request.sessionId)

                    // Add user message to history
                    sessionManager.addMessage(
                        request.sessionId,
                        teamassistant.chat.ChatMessage(
                            role = "user",
                            content = request.message
                        )
                    )

                    // Get response from chat service
                    val response = chatService.chat(request.message, history)

                    // Add assistant response to history
                    sessionManager.addMessage(
                        request.sessionId,
                        teamassistant.chat.ChatMessage(
                            role = "assistant",
                            content = response.response
                        )
                    )

                    call.respond(response)
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.InternalServerError,
                        ErrorResponse("Failed to process chat message: ${e.message}")
                    )
                }
            }

            // GET /api/chat/history/{sessionId} - Get session history
            get("/history/{sessionId}") {
                try {
                    val sessionId = call.parameters["sessionId"] ?: "default"
                    val history = sessionManager.getOrCreateSession(sessionId)
                    call.respond(history)
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.InternalServerError,
                        ErrorResponse("Failed to get history: ${e.message}")
                    )
                }
            }

            // DELETE /api/chat/history/{sessionId} - Clear session history
            delete("/history/{sessionId}") {
                try {
                    val sessionId = call.parameters["sessionId"] ?: "default"
                    sessionManager.clearSession(sessionId)
                    call.respond(mapOf("status" to "cleared", "sessionId" to sessionId))
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.InternalServerError,
                        ErrorResponse("Failed to clear history: ${e.message}")
                    )
                }
            }
        }
    }

    @Serializable
    data class ErrorResponse(
        val error: String
    )
}

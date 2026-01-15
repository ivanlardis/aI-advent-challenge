package teamassistant.api

import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import teamassistant.github.GitHubClient
import java.util.concurrent.atomic.AtomicReference

class AuthApi(
    private val githubClientProvider: () -> GitHubClient?
) {
    private val sessionToken = AtomicReference<String?>(null)

    fun install(routing: Routing) {
        routing.route("/api/auth") {
            // POST /api/auth/token - установить токен
            post("/token") {
                try {
                    val request = call.receive<TokenRequest>()
                    val token = request.token

                    if (token.isBlank()) {
                        call.respond(
                            HttpStatusCode.BadRequest,
                            ErrorResponse("invalid_token", "Token cannot be blank")
                        )
                        return@post
                    }

                    // Валидация токена через GitHub API
                    val client = githubClientProvider()
                    if (client == null) {
                        call.respond(
                            HttpStatusCode.InternalServerError,
                            ErrorResponse("server_error", "GitHub client not initialized")
                        )
                        return@post
                    }

                    val validationResult = client.validateToken()
                    if (validationResult.isFailure) {
                        call.respond(
                            HttpStatusCode.Unauthorized,
                            ErrorResponse("invalid_token", "Failed to validate GitHub token")
                        )
                        return@post
                    }

                    // Сохраняем токен в сессии
                    sessionToken.set(token)
                    call.respond(HttpStatusCode.OK, mapOf("status" to "authenticated"))
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        ErrorResponse("bad_request", e.message)
                    )
                }
            }

            // GET /api/auth/status - проверить статус авторизации
            get("/status") {
                val isAuthenticated = sessionToken.get() != null
                call.respond(AuthStatusResponse(isAuthenticated))
            }
        }
    }

    fun getCurrentToken(): String? = sessionToken.get()

    fun clearToken() {
        sessionToken.set(null)
    }
}

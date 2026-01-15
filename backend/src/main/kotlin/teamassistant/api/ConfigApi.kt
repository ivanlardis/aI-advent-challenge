package teamassistant.api

import config.TeamAssistantConfig
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.serialization.json.Json
import java.nio.file.Files
import java.nio.file.Paths

class ConfigApi(
    private var config: TeamAssistantConfig,
    private val configPath: String = ".team-assistant/config.json"
) {
    private val json = Json { prettyPrint = true; ignoreUnknownKeys = true }

    fun install(routing: Routing) {
        routing.route("/api/config") {
            // GET /api/config - получить текущую конфигурацию
            get {
                call.respond(config)
            }

            // POST /api/config - обновить конфигурацию
            post {
                try {
                    val newConfig = call.receive<TeamAssistantConfig>()

                    // Валидация
                    if (!newConfig.scoring.validateWeights()) {
                        call.respond(
                            HttpStatusCode.BadRequest,
                            ErrorResponse("invalid_weights", "Weights must sum to 1.0")
                        )
                        return@post
                    }

                    // Сохранить в файл
                    saveConfig(newConfig)

                    // Обновить в памяти
                    config = newConfig

                    call.respond(HttpStatusCode.OK, mapOf("status" to "updated"))
                } catch (e: Exception) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        ErrorResponse("invalid_config", e.message)
                    )
                }
            }
        }
    }

    fun getConfig(): TeamAssistantConfig = config

    private fun saveConfig(newConfig: TeamAssistantConfig) {
        try {
            val path = Paths.get(configPath)
            Files.createDirectories(path.parent)

            val content = json.encodeToString(TeamAssistantConfig.serializer(), newConfig)
            Files.writeString(path, content)
        } catch (e: Exception) {
            throw Exception("Failed to save config: ${e.message}", e)
        }
    }

    fun loadConfig(): TeamAssistantConfig {
        return try {
            val path = Paths.get(configPath)
            if (!Files.exists(path)) {
                return config
            }

            val content = Files.readString(path)
            val loaded = json.decodeFromString<TeamAssistantConfig>(content)
            config = loaded
            loaded
        } catch (e: Exception) {
            throw Exception("Failed to load config: ${e.message}", e)
        }
    }
}

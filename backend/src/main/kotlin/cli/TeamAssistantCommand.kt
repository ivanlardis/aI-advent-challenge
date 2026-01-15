package cli

import config.TeamAssistantConfig
import kotlinx.serialization.json.Json
import teamassistant.github.GitHubClient
import teamassistant.server.TeamAssistantServer
import java.nio.file.Files
import java.nio.file.Paths

class TeamAssistantCommand {
    fun execute(args: Array<String>) {
        val home = args.getOrElse(0) { "." }

        println("🚀 Starting Team Assistant...")
        println("📁 Project directory: $home")

        // Load or create config
        val config = loadOrCreateConfig()
        println("⚙️  Config loaded: ${config.github.owner}/${config.github.repo}")
        println("📊 Max issues: ${config.github.maxIssues}, Max commits: ${config.github.maxCommits}")

        // Check GitHub token (optional for demo mode)
        val token = System.getenv("GITHUB_TOKEN") ?: System.getenv("TEAM_ASSISTANT_GITHUB_TOKEN") ?: ""
        if (token.isNotBlank()) {
            println("🔑 GitHub token: ${token.take(16)}...")
        } else {
            println("⚠️  No GitHub token provided - running in demo mode")
            println("   Set GITHUB_TOKEN environment variable for full functionality")
        }

        // Start server
        val server = TeamAssistantServer(config)
        val client = GitHubClient(token)

        // Set client in server
        server.setGitHubClient(client)

        try {
            server.start()
        } catch (e: Exception) {
            println("❌ Failed to start server: ${e.message}")
            e.printStackTrace()
        } finally {
            client.close()
        }
    }

    private fun readGitHubToken(): String? {
        println("\n🔑 Enter your GitHub Personal Access Token:")
        println("   (Create at: https://github.com/settings/tokens)")
        print("   Token (press Enter to skip): ")

        return readlnOrNull()?.trim()
    }

    private fun loadOrCreateConfig(): TeamAssistantConfig {
        val configPath = Paths.get(".team-assistant/config.json")

        return if (Files.exists(configPath)) {
            val json = Json { ignoreUnknownKeys = true }
            val content = Files.readString(configPath)
            json.decodeFromString<TeamAssistantConfig>(content)
        } else {
            println("⚠️  Config not found, creating default config...")
            val defaultConfig = TeamAssistantConfig()
            saveConfig(defaultConfig)
            defaultConfig
        }
    }

    private fun saveConfig(config: TeamAssistantConfig) {
        val configPath = Paths.get(".team-assistant/config.json")
        Files.createDirectories(configPath.parent)
        val json = Json { prettyPrint = true }
        val content = json.encodeToString(TeamAssistantConfig.serializer(), config)
        Files.writeString(configPath, content)
        println("✅ Config created at ${configPath.toAbsolutePath()}")
        println("⚠️  Please edit config.json and set github.owner and github.repo")
    }
}

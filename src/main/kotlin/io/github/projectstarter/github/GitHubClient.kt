package io.github.projectstarter.github

import io.github.projectstarter.config.Config
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

class GitHubClient(private val token: String) {

    private val client = HttpClient {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
            })
        }
    }

    suspend fun getUser(): GitHubUser {
        val response = client.get("${Config.GITHUB_API_URL}/user") {
            headers {
                append(HttpHeaders.Authorization, "Bearer $token")
                append(HttpHeaders.Accept, "application/vnd.github+json")
            }
        }

        if (response.status.value !in 200..299) {
            val errorBody = response.bodyAsText()
            throw Exception("GitHub API error: ${response.status} - $errorBody")
        }

        val bodyText = response.bodyAsText()
        return Json { ignoreUnknownKeys = true; isLenient = true }
            .decodeFromString<GitHubUser>(bodyText)
    }

    suspend fun createRepository(name: String, description: String): GitHubRepository {
        return client.post("${Config.GITHUB_API_URL}/user/repos") {
            headers {
                append(HttpHeaders.Authorization, "Bearer $token")
                append(HttpHeaders.Accept, "application/vnd.github+json")
                append(HttpHeaders.ContentType, "application/json")
            }
            setBody(
                GitHubCreateRepositoryRequest(
                    name = name,
                    description = description,
                    isPrivate = false,
                    autoInit = false
                )
            )
        }.body<GitHubRepository>()
    }

    suspend fun checkRateLimit(): RateLimit {
        val response = client.get("${Config.GITHUB_API_URL}/rate_limit") {
            headers {
                append(HttpHeaders.Authorization, "Bearer $token")
            }
        }

        if (response.status.value !in 200..299) {
            val errorBody = response.bodyAsText()
            throw Exception("GitHub API error: ${response.status} - $errorBody")
        }

        val bodyText = response.bodyAsText()
        return Json { ignoreUnknownKeys = true; isLenient = true }
            .decodeFromString<RateLimit>(bodyText)
    }

    suspend fun createSecret(
        owner: String,
        repo: String,
        secretName: String,
        secretValue: String
    ) {
        // Для создания секретов нужен public key репозитория
        val publicKey = getRepoPublicKey(owner, repo)

        client.put("${Config.GITHUB_API_URL}/repos/$owner/$repo/actions/secrets/$secretName") {
            headers {
                append(HttpHeaders.Authorization, "Bearer $token")
                append(HttpHeaders.Accept, "application/vnd.github+json")
                append(HttpHeaders.ContentType, "application/json")
            }
            setBody(
                GitHubCreateSecretRequest(
                    keyId = publicKey.keyId,
                    encryptedValue = encryptSecret(publicKey.key, secretValue)
                )
            )
        }
    }

    private suspend fun getRepoPublicKey(owner: String, repo: String): GitHubPublicKey {
        return client.get("${Config.GITHUB_API_URL}/repos/$owner/$repo/actions/secrets/public-key") {
            headers {
                append(HttpHeaders.Authorization, "Bearer $token")
                append(HttpHeaders.Accept, "application/vnd.github+json")
            }
        }.body<GitHubPublicKey>()
    }

    private fun encryptSecret(publicKeyBase64: String, secretValue: String): String {
        // Используем libsodium для шифрования секретов (требование GitHub API)
        val sodium = com.goterl.lazysodium.LazySodiumJava(com.goterl.lazysodium.SodiumJava())

        // Декодируем публичный ключ репозитория
        val publicKey = java.util.Base64.getDecoder().decode(publicKeyBase64)
        val secretBytes = secretValue.toByteArray(Charsets.UTF_8)

        // Шифруем с помощью crypto_box_seal (sealed box)
        val encrypted = ByteArray(secretBytes.size + com.goterl.lazysodium.interfaces.Box.SEALBYTES)

        val result = sodium.cryptoBoxSeal(
            encrypted,
            secretBytes,
            secretBytes.size.toLong(),
            publicKey
        )

        if (!result) {
            throw Exception("Failed to encrypt secret with libsodium")
        }

        // Возвращаем зашифрованное значение в base64
        return java.util.Base64.getEncoder().encodeToString(encrypted)
    }

    suspend fun close() {
        client.close()
    }
}

// Data classes для API ответов

@Serializable
data class GitHubUser(
    val login: String,
    val id: Long,
    val name: String?
)

@Serializable
data class GitHubRepository(
    val id: Long,
    val name: String,
    val full_name: String,
    val owner: GitHubOwner,
    val html_url: String,
    val clone_url: String
)

@Serializable
data class GitHubOwner(
    val login: String
)

@Serializable
data class GitHubCreateRepositoryRequest(
    val name: String,
    val description: String,
    @SerialName("private")
    val isPrivate: Boolean,
    @SerialName("auto_init")
    val autoInit: Boolean
)

@Serializable
data class RateLimit(
    val resources: Resources,
    val rate: RateLimitInfo
)

@Serializable
data class Resources(
    val core: RateLimitInfo,
    val search: RateLimitInfo,
    val graphql: RateLimitInfo,
    val integration_manifest: RateLimitInfo
)

@Serializable
data class RateLimitInfo(
    val limit: Int,
    val remaining: Int,
    val reset: Long
)

@Serializable
data class GitHubPublicKey(
    @SerialName("key_id")
    val keyId: String,
    val key: String
)

@Serializable
data class GitHubCreateSecretRequest(
    @SerialName("key_id")
    val keyId: String,
    @SerialName("encrypted_value")
    val encryptedValue: String
)

package teamassistant.api

import kotlinx.serialization.Serializable

@Serializable
data class TokenRequest(
    val token: String
)

@Serializable
data class AuthStatusResponse(
    val authenticated: Boolean
)

@Serializable
data class ErrorResponse(
    val error: String,
    val message: String? = null
)

@Serializable
data class RefreshResponse(
    val issuesUpdated: Int,
    val durationMs: Long
)

@Serializable
data class CacheStatsResponse(
    val exists: Boolean,
    val size: Long,
    val lastUpdated: String?,
    val issuesCount: Int
)

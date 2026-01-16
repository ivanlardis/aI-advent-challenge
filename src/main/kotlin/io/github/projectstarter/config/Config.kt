package io.github.projectstarter.config

object Config {
    const val GITHUB_API_URL = "https://api.github.com"
    const val SSH_KEY_SIZE = 2048  // Для RSA (не используется с ED25519)
    const val SSH_TIMEOUT_MS = 30000
    const val GIT_PUSH_TIMEOUT_SECONDS = 60L
}

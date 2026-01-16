package io.github.projectstarter.cli

import io.github.projectstarter.github.GitHubClient
import io.github.projectstarter.ssh.VPSService

class Validator(
    private val githubClient: GitHubClient,
    private val vpsService: VPSService?
) {

    suspend fun validateAll(): ValidationResult {
        val errors = mutableListOf<String>()

        // 1. Проверка GitHub token
        val githubResult = validateGitHubToken()
        if (githubResult is ValidationResult.Error) {
            errors.addAll(githubResult.errors)
        }

        // 2. Проверка лимитов GitHub API
        val rateLimitResult = validateRateLimit()
        if (rateLimitResult is ValidationResult.Error) {
            errors.addAll(rateLimitResult.errors)
        }

        // 3. Проверка VPS доступности (если указан)
        if (vpsService != null) {
            val vpsResult = validateVPSAccess()
            if (vpsResult is ValidationResult.Error) {
                errors.addAll(vpsResult.errors)
            }
        }

        return if (errors.isEmpty()) {
            ValidationResult.Success
        } else {
            ValidationResult.Error(errors)
        }
    }

    private suspend fun validateGitHubToken(): ValidationResult {
        return try {
            val user = githubClient.getUser()
            ValidationResult.Success
        } catch (e: Exception) {
            ValidationResult.Error(listOf(
                "Ошибка авторизации GitHub: ${e.message}",
                "Убедитесь, что токен действительный и имеет scope 'repo'"
            ))
        }
    }

    private suspend fun validateRateLimit(): ValidationResult {
        return try {
            val rateLimit = githubClient.checkRateLimit()
            if (rateLimit.resources.core.remaining < 10) {
                ValidationResult.Error(listOf(
                    "Превышены лимиты GitHub API. Осталось запросов: ${rateLimit.resources.core.remaining}",
                    "Попробуйте позже или обновите план GitHub"
                ))
            } else {
                ValidationResult.Success
            }
        } catch (e: Exception) {
            ValidationResult.Error(listOf(
                "Не удалось проверить лимиты GitHub API: ${e.message}"
            ))
        }
    }

    private suspend fun validateVPSAccess(): ValidationResult {
        return try {
            val connected = vpsService!!.connect()
            if (!connected) {
                ValidationResult.Error(listOf(
                    "Не удалось подключиться к VPS",
                    "Проверьте хост и убедитесь, что SSH доступен"
                ))
            } else {
                vpsService!!.close()
                ValidationResult.Success
            }
        } catch (e: Exception) {
            ValidationResult.Error(listOf(
                "Ошибка подключения к VPS: ${e.message}"
            ))
        }
    }
}

sealed class ValidationResult {
    object Success : ValidationResult()
    data class Error(val errors: List<String>) : ValidationResult()
}

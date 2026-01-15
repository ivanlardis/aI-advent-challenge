package mcp

import org.eclipse.jgit.api.Git
import org.eclipse.jgit.lib.Repository
import org.eclipse.jgit.storage.file.FileRepositoryBuilder
import java.io.File

/**
 * Git инструменты через JGit
 */
class GitTools(private val repoPath: String) {
    private val repository: Repository? by lazy {
        try {
            val gitDir = findGitDirectory(File(repoPath))
            if (gitDir != null) {
                FileRepositoryBuilder()
                    .setGitDir(gitDir)
                    .readEnvironment()
                    .findGitDir()
                    .build()
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Найти .git директорию
     */
    private fun findGitDirectory(dir: File): File? {
        var current: File? = dir
        while (current != null) {
            val gitDir = File(current, ".git")
            if (gitDir.exists() && gitDir.isDirectory) {
                return gitDir
            }
            current = current.parentFile
        }
        return null
    }

    /**
     * Получить текущую ветку
     */
    fun getCurrentBranch(): String {
        return try {
            repository?.branch ?: "Не является git-репозиторием"
        } catch (e: Exception) {
            "Ошибка: ${e.message}"
        }
    }

    /**
     * Получить информацию о последнем коммите
     */
    fun getLastCommit(): String {
        return try {
            val repo = repository ?: return "Не является git-репозиторием"
            val git = Git(repo)

            val commits = git.log().setMaxCount(1).call().toList()
            if (commits.isEmpty()) {
                "Нет коммитов"
            } else {
                val commit = commits.first()
                val shortHash = commit.name.take(7)
                val message = commit.shortMessage
                "$shortHash $message"
            }
        } catch (e: Exception) {
            "Ошибка: ${e.message}"
        }
    }

    /**
     * Получить статус репозитория (измененные файлы)
     */
    fun getStatus(): List<String> {
        return try {
            val repo = repository ?: return listOf("Не является git-репозиторием")
            val git = Git(repo)

            val status = git.status().call()
            val result = mutableListOf<String>()

            status.added.forEach { result.add("A  $it") }
            status.modified.forEach { result.add("M  $it") }
            status.removed.forEach { result.add("D  $it") }
            status.untracked.forEach { result.add("?? $it") }

            if (result.isEmpty()) {
                listOf("Нет изменений")
            } else {
                result
            }
        } catch (e: Exception) {
            listOf("Ошибка: ${e.message}")
        }
    }

    /**
     * Закрыть репозиторий
     */
    fun close() {
        repository?.close()
    }
}

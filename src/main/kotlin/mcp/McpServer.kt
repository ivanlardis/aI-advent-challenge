package mcp

/**
 * Простой MCP сервер для git-операций
 * В текущей реализации используется напрямую из CLI
 */
class McpServer(private val gitTools: GitTools) {
    /**
     * Получить информацию о git-репозитории
     */
    fun getGitInfo(): String {
        val branch = gitTools.getCurrentBranch()
        val lastCommit = gitTools.getLastCommit()
        val status = gitTools.getStatus()

        return buildString {
            appendLine("=== Git Info ===")
            appendLine("Branch: $branch")
            appendLine("Last commit: $lastCommit")
            appendLine("\nStatus:")
            status.forEach { appendLine("  $it") }
        }
    }
}

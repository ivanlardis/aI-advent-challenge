package mcp

/**
 * Простой MCP сервер для git-операций и CRM данных
 * В текущей реализации используется напрямую из CLI
 */
class McpServer(
    private val gitTools: GitTools,
    private val crmTools: CrmTools
) {
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

    /**
     * Получить список не закоммиченных/неотслеживаемых файлов.
     */
    fun getUncommittedFiles(): String {
        val status = gitTools.getStatus().filterNot { it == "Нет изменений" || it.startsWith("Не является") }
        return buildString {
            appendLine("=== Uncommitted files ===")
            if (status.isEmpty()) {
                appendLine("Нет изменений")
            } else {
                status.forEach { appendLine(it) }
            }
        }
    }

    // CRM методы
    fun getUser(emailOrId: String) = crmTools.getUser(emailOrId)
    fun listUsers() = crmTools.listUsers()
    fun getUserTickets(userId: String) = crmTools.getUserTickets(userId)
    fun getTicket(ticketId: String) = crmTools.getTicket(ticketId)
    fun getUserSubscriptions(userId: String) = crmTools.getUserSubscriptions(userId)
}

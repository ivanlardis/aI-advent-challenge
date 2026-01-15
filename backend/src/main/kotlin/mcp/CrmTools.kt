package mcp

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File

/**
 * CRM инструменты для работы с JSON данными пользователей, тикетов, подписок
 */
class CrmTools(private val crmDataDir: String) {
    private val json = Json { ignoreUnknownKeys = true }

    private val usersFile = File(crmDataDir, "users.json")
    private val ticketsFile = File(crmDataDir, "tickets.json")
    private val subscriptionsFile = File(crmDataDir, "subscriptions.json")

    /**
     * Поиск пользователя по email или ID
     */
    fun getUser(emailOrId: String): String {
        if (!usersFile.exists()) return "Файл users.json не найден"

        try {
            val content = usersFile.readText()
            val jsonElement = json.parseToJsonElement(content)
            val users = jsonElement.jsonObject["users"]?.jsonArray ?: return "Нет пользователей"

            val user = users.firstOrNull { userObj ->
                val obj = userObj.jsonObject
                val id = obj["id"]?.jsonPrimitive?.content
                val email = obj["email"]?.jsonPrimitive?.content
                id == emailOrId || email == emailOrId
            }

            return if (user != null) {
                formatUser(user.jsonObject)
            } else {
                "Пользователь не найден: $emailOrId"
            }
        } catch (e: Exception) {
            return "Ошибка чтения users.json: ${e.message}"
        }
    }

    /**
     * Список всех пользователей
     */
    fun listUsers(): String {
        if (!usersFile.exists()) return "Файл users.json не найден"

        try {
            val content = usersFile.readText()
            val jsonElement = json.parseToJsonElement(content)
            val users = jsonElement.jsonObject["users"]?.jsonArray ?: return "Нет пользователей"

            return buildString {
                appendLine("=== Пользователи (${users.size}) ===")
                users.forEach { user ->
                    val obj = user.jsonObject
                    val id = obj["id"]?.jsonPrimitive?.content ?: "?"
                    val name = obj["name"]?.jsonPrimitive?.content ?: "?"
                    val email = obj["email"]?.jsonPrimitive?.content ?: "?"
                    val status = obj["status"]?.jsonPrimitive?.content ?: "?"
                    appendLine("ID: $id | $name | $email | Status: $status")
                }
            }
        } catch (e: Exception) {
            return "Ошибка чтения users.json: ${e.message}"
        }
    }

    /**
     * Получить тикеты пользователя
     */
    fun getUserTickets(userId: String): String {
        if (!ticketsFile.exists()) return "Файл tickets.json не найден"

        try {
            val content = ticketsFile.readText()
            val jsonElement = json.parseToJsonElement(content)
            val tickets = jsonElement.jsonObject["tickets"]?.jsonArray ?: return "Нет тикетов"

            val userTickets = tickets.filter { ticket ->
                ticket.jsonObject["userId"]?.jsonPrimitive?.content == userId
            }

            if (userTickets.isEmpty()) return "У пользователя $userId нет тикетов"

            return buildString {
                appendLine("=== Тикеты пользователя $userId (${userTickets.size}) ===")
                userTickets.forEach { ticket ->
                    val obj = ticket.jsonObject
                    appendLine(formatTicket(obj))
                    appendLine()
                }
            }
        } catch (e: Exception) {
            return "Ошибка чтения tickets.json: ${e.message}"
        }
    }

    /**
     * Получить информацию о тикете
     */
    fun getTicket(ticketId: String): String {
        if (!ticketsFile.exists()) return "Файл tickets.json не найден"

        try {
            val content = ticketsFile.readText()
            val jsonElement = json.parseToJsonElement(content)
            val tickets = jsonElement.jsonObject["tickets"]?.jsonArray ?: return "Нет тикетов"

            val ticket = tickets.firstOrNull { t ->
                t.jsonObject["id"]?.jsonPrimitive?.content == ticketId
            }

            return if (ticket != null) {
                formatTicket(ticket.jsonObject)
            } else {
                "Тикет не найден: $ticketId"
            }
        } catch (e: Exception) {
            return "Ошибка чтения tickets.json: ${e.message}"
        }
    }

    /**
     * Получить подписки пользователя
     */
    fun getUserSubscriptions(userId: String): String {
        if (!subscriptionsFile.exists()) return "Файл subscriptions.json не найден"

        try {
            val content = subscriptionsFile.readText()
            val jsonElement = json.parseToJsonElement(content)
            val subscriptions = jsonElement.jsonObject["subscriptions"]?.jsonArray ?: return "Нет подписок"

            val userSubs = subscriptions.filter { sub ->
                sub.jsonObject["userId"]?.jsonPrimitive?.content == userId
            }

            if (userSubs.isEmpty()) return "У пользователя $userId нет подписок"

            return buildString {
                appendLine("=== Подписки пользователя $userId (${userSubs.size}) ===")
                userSubs.forEach { sub ->
                    val obj = sub.jsonObject
                    appendLine(formatSubscription(obj))
                    appendLine()
                }
            }
        } catch (e: Exception) {
            return "Ошибка чтения subscriptions.json: ${e.message}"
        }
    }

    private fun formatUser(obj: kotlinx.serialization.json.JsonObject): String {
        val id = obj["id"]?.jsonPrimitive?.content ?: "?"
        val name = obj["name"]?.jsonPrimitive?.content ?: "?"
        val email = obj["email"]?.jsonPrimitive?.content ?: "?"
        val status = obj["status"]?.jsonPrimitive?.content ?: "?"
        val registered = obj["registeredAt"]?.jsonPrimitive?.content ?: "?"

        return """
            User ID: $id
            Name: $name
            Email: $email
            Status: $status
            Registered: $registered
        """.trimIndent()
    }

    private fun formatTicket(obj: kotlinx.serialization.json.JsonObject): String {
        val id = obj["id"]?.jsonPrimitive?.content ?: "?"
        val userId = obj["userId"]?.jsonPrimitive?.content ?: "?"
        val subject = obj["subject"]?.jsonPrimitive?.content ?: "?"
        val status = obj["status"]?.jsonPrimitive?.content ?: "?"
        val priority = obj["priority"]?.jsonPrimitive?.content ?: "?"
        val created = obj["createdAt"]?.jsonPrimitive?.content ?: "?"
        val description = obj["description"]?.jsonPrimitive?.content ?: "?"

        return """
            Ticket #$id (User: $userId)
            Subject: $subject
            Status: $status | Priority: $priority
            Created: $created
            Description: $description
        """.trimIndent()
    }

    private fun formatSubscription(obj: kotlinx.serialization.json.JsonObject): String {
        val id = obj["id"]?.jsonPrimitive?.content ?: "?"
        val userId = obj["userId"]?.jsonPrimitive?.content ?: "?"
        val plan = obj["plan"]?.jsonPrimitive?.content ?: "?"
        val status = obj["status"]?.jsonPrimitive?.content ?: "?"
        val start = obj["startDate"]?.jsonPrimitive?.content ?: "?"
        val end = obj["endDate"]?.jsonPrimitive?.content ?: "?"
        val price = obj["price"]?.jsonPrimitive?.content ?: "?"

        return """
            Subscription #$id (User: $userId)
            Plan: $plan | Status: $status
            Period: $start - $end
            Price: $price ₽
        """.trimIndent()
    }
}

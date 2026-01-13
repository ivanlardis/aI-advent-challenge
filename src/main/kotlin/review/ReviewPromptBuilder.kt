package review

import llm.Message

/**
 * Формирование промптов для LLM для code review
 */
object ReviewPromptBuilder {

    /**
     * Создать промпт для анализа PR
     */
    fun buildPrompt(diffResult: DiffResult): List<Message> {
        val systemPrompt = """
            Ты - эксперт по code review. Твоя задача проанализировать Pull Request и дать конструктивный фидбек.

            Критерии оценки (фокус на качестве кода):
            1. Стиль кода - соответствие Kotlin/Java conventions
            2. Читаемость - понятность кода, качество naming
            3. Сложность - цикломатическая сложность, длина функций/классов
            4. Дублирование - повторяющиеся паттерны кода
            5. Архитектура - соответствие SOLID, разделение ответственности
            6. Потенциальные баги - логические ошибки, edge cases

            Формат ответа (Markdown):
            ## 📊 Общая оценка
            [Краткая оценка PR: ✅ Хорошо / ⚠️ Требует доработки / ❌ Критические проблемы]

            ## ✅ Что хорошо
            - [Перечисли позитивные аспекты кода]

            ## ⚠️ Замечания
            - **[путь/к/файлу.kt]**: [Описание проблемы и рекомендация по исправлению]

            ## 💡 Рекомендации
            - [Общие советы по улучшению]

            Правила:
            - Будь конструктивным и дружелюбным
            - Не упоминай очевидные вещи
            - Если нет замечаний - так и скажи
            - Приводи конкретные примеры из кода
        """.trimIndent()

        val filesContext = buildFilesContext(diffResult)

        return listOf(
            Message("system", systemPrompt),
            Message("user", "Проанализируй следующий Pull Request:\n\n$filesContext")
        )
    }

    /**
     * Построить контекст файлов для промпта
     */
    private fun buildFilesContext(diffResult: DiffResult): String {
        val sb = StringBuilder()

        sb.appendLine("### Статистика изменений")
        sb.appendLine("- Файлов изменено: ${diffResult.files.size}")
        sb.appendLine("- Строк добавлено (примерно): ${diffResult.additionsCount}")
        sb.appendLine("- Файлов удалено: ${diffResult.deletionsCount}")
        sb.appendLine()

        diffResult.files
            .filter { it.changeType != ChangeType.DELETE }
            .forEachIndexed { index, file ->
                sb.appendLine("---")
                sb.appendLine()
                sb.appendLine("### Файл ${index + 1}: ${file.path}")
                sb.appendLine("**Тип изменения**: ${changeTypeToRussian(file.changeType)}")
                sb.appendLine("**Размер**: ${file.content.lines().size} строк")
                sb.appendLine()
                sb.appendLine("**Содержимое:**")
                sb.appendLine("```")

                // Ограничить количество строк для каждого файла
                val lines = file.content.lines()
                val maxLines = 300
                if (lines.size > maxLines) {
                    sb.appendLine(lines.take(maxLines).joinToString("\n"))
                    sb.appendLine()
                    sb.appendLine("... [показаны первые $maxLines строк из ${lines.size}]")
                } else {
                    sb.appendLine(file.content)
                }

                sb.appendLine("```")
                sb.appendLine()
            }

        if (diffResult.deletionsCount > 0) {
            sb.appendLine("---")
            sb.appendLine()
            sb.appendLine("**Примечание:** ${diffResult.deletionsCount} файл(ов) удалено.")
        }

        return sb.toString()
    }

    private fun changeTypeToRussian(type: ChangeType): String = when (type) {
        ChangeType.ADD -> "Новый файл"
        ChangeType.MODIFY -> "Изменен"
        ChangeType.DELETE -> "Удален"
    }
}

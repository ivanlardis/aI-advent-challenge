package teamassistant.chat

/**
 * Simple rule-based intent recognizer.
 * Analyzes user messages to determine what action to take.
 */
object IntentRecognizer {

    /**
     * Recognize the intent from a user message.
     */
    fun recognize(message: String): Intent {
        val lower = message.lowercase()

        return when {
            // Create issue
            lower.contains("создай задач") ||
            lower.contains("создать задач") ||
            lower.contains("новая задач") ||
            lower.contains("добавь задач") ||
            lower.contains("создай issue") ||
            lower.contains("create issue") ||
            lower.contains("new issue") -> Intent.CREATE_ISSUE

            // Analyze issues
            lower.contains("какие задач") ||
            lower.contains("список задач") ||
            lower.contains("покажи задач") ||
            lower.contains("какие issue") ||
            lower.contains("приоритет") ||
            lower.contains("priority") ||
            lower.contains("статус задач") -> Intent.ANALYZE_ISSUES

            // Recommendations
            lower.contains("что след") ||
            lower.contains("что дальше") ||
            lower.contains("рекоменд") ||
            lower.contains("что делать") ||
            lower.contains("что next") ||
            lower.contains("what's next") -> Intent.RECOMMEND

            // Project questions
            lower.contains("как работ") ||
            lower.contains("как работает") ||
            lower.contains("объясни") ||
            lower.contains("где наход") ||
            lower.contains("расскажи о") ||
            lower.contains("что такое") ||
            lower.contains("how does") ||
            lower.contains("explain") ||
            lower.contains("where is") -> Intent.QUESTION

            else -> Intent.QUESTION  // Default to question
        }
    }
}

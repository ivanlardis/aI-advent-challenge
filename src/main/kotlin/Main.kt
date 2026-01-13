import cli.AssistantCommand
import cli.ReviewCommand

/**
 * Точка входа в приложение
 */
fun main(args: Array<String>) {
    // Если первый аргумент - "review-pr", используем ReviewCommand
    if (args.isNotEmpty() && args[0] == "review-pr") {
        ReviewCommand().main(args.drop(1).toTypedArray())
    } else {
        // Иначе используем стандартный AssistantCommand
        AssistantCommand().main(args)
    }
}

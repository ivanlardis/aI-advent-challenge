import cli.AssistantCommand
import cli.ReviewCommand
import cli.TeamAssistantCommand

/**
 * Точка входа в приложение
 */
fun main(args: Array<String>) {
    when (val command = args.firstOrNull()) {
        "review-pr" -> ReviewCommand().main(args.drop(1).toTypedArray())
        "team-assistant" -> TeamAssistantCommand().execute(args.drop(1).toTypedArray())
        else -> AssistantCommand().main(args)
    }
}

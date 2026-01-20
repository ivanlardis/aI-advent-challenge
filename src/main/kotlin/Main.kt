import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlin.system.exitProcess

const val OLLAMA_HOST = "http://localhost:11434"

val json = Json { ignoreUnknownKeys = true }

@Serializable
data class GenerateRequest(val model: String, val prompt: String, val stream: Boolean = false)

fun main(args: Array<String>) = runBlocking {
    val client = HttpClient(CIO)

    try {
        if (args.isEmpty()) {
            printHelp()
            return@runBlocking
        }

        val parsedArgs = parseArgs(args)

        when {
            parsedArgs.containsKey("help") -> {
                printHelp()
            }
            parsedArgs.containsKey("list") -> {
                listModels(client)
            }
            !parsedArgs.containsKey("prompt") -> {
                println("Ошибка: не указан prompt")
                printHelp()
                exitProcess(1)
            }
            else -> {
                val prompt = parsedArgs["prompt"]!!
                val model = parsedArgs["model"] ?: getFirstModel(client)
                generateResponse(client, model, prompt)
            }
        }
    } finally {
        client.close()
    }
}

fun parseArgs(args: Array<String>): Map<String, String> {
    val result = mutableMapOf<String, String>()
    var i = 0

    while (i < args.size) {
        when (args[i]) {
            "-h", "--help" -> result["help"] = "true"
            "-l", "--list" -> result["list"] = "true"
            "-m", "--model" -> {
                if (i + 1 < args.size) {
                    result["model"] = args[++i]
                }
            }
            else -> {
                if (!args[i].startsWith("-")) {
                    result["prompt"] = args[i]
                }
            }
        }
        i++
    }

    return result
}

fun printHelp() {
    println("""
        local-llm-cli - CLI клиент для Ollama

        Использование:
          java -jar local-llm-cli.jar [prompt] [опции]

        Аргументы:
          prompt        Текст запроса к LLM

        Опции:
          -m, --model   Модель (по умолчанию - первая доступная)
          -l, --list    Показать список моделей
          -h, --help    Справка

        Примеры:
          java -jar local-llm-cli.jar "Составь список из 5 идей для ужина."
          java -jar local-llm-cli.jar "Кто написал Войну и мир?" -m gemma3:1b
          java -jar local-llm-cli.jar -l
    """.trimIndent())
}

suspend fun listModels(client: HttpClient) {
    try {
        val response = client.get("$OLLAMA_HOST/api/tags").bodyAsText()
        val jsonBody = json.parseToJsonElement(response)
        val models = jsonBody.jsonObject["models"]?.jsonArray ?: emptyList()

        println("Доступные модели:")
        models.forEach { model ->
            val name = model.jsonObject["name"]?.jsonPrimitive?.content ?: "unknown"
            println("  - $name")
        }
    } catch (e: Exception) {
        println("Ошибка: ${e.message}")
        exitProcess(1)
    }
}

suspend fun getFirstModel(client: HttpClient): String {
    try {
        val response = client.get("$OLLAMA_HOST/api/tags").bodyAsText()
        val jsonBody = json.parseToJsonElement(response)
        val models = jsonBody.jsonObject["models"]?.jsonArray ?: emptyList()

        if (models.isEmpty()) {
            println("Ошибка: нет доступных моделей")
            exitProcess(1)
        }

        return models.first().jsonObject["name"]?.jsonPrimitive?.content ?: "gemma3:1b"
    } catch (e: Exception) {
        println("Ошибка подключения к Ollama: ${e.message}")
        exitProcess(1)
    }
}

suspend fun generateResponse(client: HttpClient, model: String, prompt: String) {
    try {
        val requestBody = json.encodeToString(GenerateRequest.serializer(), GenerateRequest(model, prompt, stream = false))

        val response = client.post("$OLLAMA_HOST/api/generate") {
            contentType(ContentType.Application.Json)
            setBody(requestBody)
        }.bodyAsText()

        // Ollama возвращает ответ по частям, собираем все response фрагменты
        val jsonObjects = response.split("\n").filter { it.isNotBlank() }
        val fullResponse = StringBuilder()

        for (jsonStr in jsonObjects) {
            val jsonResponse = json.parseToJsonElement(jsonStr)
            val part = jsonResponse.jsonObject["response"]?.jsonPrimitive?.content
            if (part != null) {
                fullResponse.append(part)
            }
        }

        if (fullResponse.isNotEmpty()) {
            print(fullResponse.toString().trim())
            System.out.flush()
        } else {
            System.err.println("Ошибка: пустой ответ от модели")
            exitProcess(1)
        }
    } catch (e: Exception) {
        System.err.println("Ошибка генерации: ${e.message}")
        e.printStackTrace()
        exitProcess(1)
    }
}

package io.github.projectstarter.template

import java.io.File
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption
import kotlin.io.path.createTempDirectory
import kotlin.io.path.copyToRecursively

class TemplateGenerator {

    suspend fun extractTemplate(): String {
        val tempDir = createTempDirectory("project-starter-template")
        val targetDir = File(tempDir.toFile(), "project-template")
        targetDir.mkdirs()

        // Копируем ресурсы из JAR
        copyResourcesFromJar("templates/project-template", targetDir)

        // Копируем gradle-wrapper.jar напрямую из проекта (Gradle не включает .jar в resources)
        val wrapperJar = File("gradle/wrapper/gradle-wrapper.jar")
        if (wrapperJar.exists()) {
            val targetWrapperDir = File(targetDir, "gradle/wrapper")
            targetWrapperDir.mkdirs()
            wrapperJar.copyTo(File(targetWrapperDir, "gradle-wrapper.jar"), overwrite = true)
        }

        return targetDir.absolutePath
    }

    private fun copyResourcesFromJar(resourcePath: String, targetDir: File) {
        val loader = javaClass.classLoader
        val resourceUrl = loader.getResource(resourcePath)
            ?: throw IllegalStateException("Resource not found: $resourcePath")

        // Получаем все файлы в директории ресурсов
        val resourceFiles = getResourceFiles(resourcePath)

        resourceFiles.forEach { relativePath ->
            val resource = loader.getResource("$resourcePath/$relativePath")
                ?: return@forEach

            val targetFile = File(targetDir, relativePath)
            targetFile.parentFile?.mkdirs()

            resource.openStream().use { input ->
                targetFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
    }

    private fun getResourceFiles(path: String): List<String> {
        // Для MVP - возвращаем известную структуру
        // В реальном проекте нужно сканировать ресурсы
        return listOf(
            ".github/workflows/deploy.yml",
            ".gitignore",
            "Dockerfile",
            "README.md",
            "build.gradle.kts",
            "docker-compose.yml",
            "gradle/wrapper/gradle-wrapper.jar",
            "gradle/wrapper/gradle-wrapper.properties",
            "gradlew",
            "gradlew.bat",
            "nginx.conf",
            "settings.gradle.kts",
            "src/main/kotlin/Application.kt"
        )
    }

    fun generateProject(
        templatePath: String,
        outputPath: String,
        placeholders: Map<String, String>
    ): Result<Unit> {
        return try {
            val templateDir = File(templatePath)
            val outputDir = File(outputPath)

            // Создаём выходную директорию
            outputDir.mkdirs()

            // Бинарные файлы - копируем без обработки
            val binaryExtensions = setOf("jar", "png", "jpg", "jpeg", "gif", "ico", "woff", "woff2", "ttf", "eot")

            // Копируем все файлы из шаблона
            templateDir.walkTopDown().forEach { sourceFile ->
                if (sourceFile.isDirectory) {
                    return@forEach
                }

                val relativePath = templateDir.toPath().relativize(sourceFile.toPath())
                val destFile = outputDir.resolve(relativePath.toString())

                // Создаём родительские директории
                destFile.parentFile?.mkdirs()

                // Проверяем если файл бинарный
                val extension = sourceFile.extension.lowercase()
                val isBinary = extension in binaryExtensions || sourceFile.name.endsWith(".jar")

                if (isBinary) {
                    // Копируем бинарный файл без изменений
                    sourceFile.copyTo(destFile, overwrite = true)
                    println("  ✓ ${relativePath}")
                } else {
                    // Текстовый файл - заменяем плейсхолдеры
                    val content = sourceFile.readText()

                    // Заменяем плейсхолдеры
                    var processedContent = content
                    placeholders.forEach { (key, value) ->
                        processedContent = processedContent.replace(key, value)
                    }

                    // Записываем обработанный файл
                    destFile.writeText(processedContent)
                    println("  ✓ ${relativePath}")
                }
            }

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun generatePlaceholders(
        projectName: String,
        description: String,
        username: String,
        githubRepo: String
    ): Map<String, String> {
        val projectSlug = projectName.lowercase()
            .replace(" ", "-")
            .replace("[^a-z0-9-]".toRegex(), "")

        val projectPackage = projectName.lowercase()
            .replace(" ", "")
            .replace("[^a-z0-9]".toRegex(), "")

        return mapOf(
            "{{PROJECT_NAME}}" to projectName,
            "{{PROJECT_SLUG}}" to projectSlug,
            "{{PROJECT_PACKAGE}}" to projectPackage,
            "{{DESCRIPTION}}" to description,
            "{{USERNAME}}" to username,
            "{{GITHUB_REPO}}" to githubRepo
        )
    }
}

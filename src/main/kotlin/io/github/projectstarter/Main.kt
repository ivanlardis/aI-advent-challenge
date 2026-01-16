package io.github.projectstarter

import io.github.projectstarter.cli.CreateCommand
import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.core.subcommands
import com.github.ajalt.clikt.parameters.options.versionOption

class Main : CliktCommand(name = "project-starter", help = """
    Project Starter CLI — быстрый развёртывание Kotlin проектов с автоматическим CI/CD и деплоем на VPS
    """.trimIndent()) {

    init {
        versionOption("1.0.0")
    }

    override fun run() {
        // По умолчанию запускаем create
    }
}

fun main(args: Array<String>) = Main().subcommands(CreateCommand()).main(args)

package io.github.{{USERNAME}}.{{PROJECT_PACKAGE}}

import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.html.*
import io.ktor.server.netty.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.html.*

fun main() {
    embeddedServer(Netty, port = 8080, host = "0.0.0.0", module = Application::module)
        .start(wait = true)
}

fun Application.module() {
    routing {
        get("/") {
            call.respondHtml {
                head {
                    title { +"{{PROJECT_NAME}}" }
                }
                body {
                    h1 { +"Welcome to {{PROJECT_NAME}}!" }
                    p { +"{{DESCRIPTION}}" }
                    p {
                        +"Stack: Ktor + Exposed + PostgreSQL + Nginx"
                    }
                }
            }
        }
    }
}

import com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar
import org.gradle.jvm.application.tasks.CreateStartScripts

plugins {
    kotlin("jvm")
    kotlin("plugin.serialization")
    id("com.github.johnrengelman.shadow")
    application
}

dependencies {
    implementation(project(":shared"))

    // CLI
    implementation("com.github.ajalt.clikt:clikt:4.2.2")

    // HTTP клиент (Ktor для GitHub API)
    implementation("io.ktor:ktor-client-core:2.3.7")
    implementation("io.ktor:ktor-client-cio:2.3.7")
    implementation("io.ktor:ktor-client-content-negotiation:2.3.7")
    implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.7")

    // Ktor Server для Team Assistant
    implementation("io.ktor:ktor-server-core:2.3.7")
    implementation("io.ktor:ktor-server-netty:2.3.7")
    implementation("io.ktor:ktor-server-content-negotiation:2.3.7")
    implementation("io.ktor:ktor-server-cors:2.3.7")
    implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.7")

    // JSON
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.2")

    // DateTime
    implementation("org.jetbrains.kotlinx:kotlinx-datetime:0.5.0")

    // Git
    implementation("org.eclipse.jgit:org.eclipse.jgit:6.8.0.202311291450-r")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.9")
    implementation("ch.qos.logback:logback-classic:1.4.14")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")

    // ONNX Runtime + DJL tokenizers for embeddings
    implementation("com.microsoft.onnxruntime:onnxruntime:1.23.2")
    implementation("ai.djl:api:0.28.0")
    implementation("ai.djl.huggingface:tokenizers:0.28.0")

    // Testing
    testImplementation("org.jetbrains.kotlin:kotlin-test")
    testImplementation("io.kotest:kotest-runner-junit5:5.8.0")
    testImplementation("io.kotest:kotest-assertions-core:5.8.0")
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(17)
}

application {
    mainClass.set("MainKt")
}

tasks {
    val shadowJarTask = named<ShadowJar>("shadowJar") {
        archiveBaseName.set("project-assistant")
        archiveClassifier.set("")
        archiveVersion.set("1.0.0")
        manifest {
            attributes["Main-Class"] = "MainKt"
        }
    }

    jar {
        archiveClassifier.set("plain")
    }

    named<CreateStartScripts>("startShadowScripts") {
        dependsOn(shadowJarTask)
        classpath = files(shadowJarTask.flatMap { it.archiveFile })
    }

    build {
        dependsOn(shadowJarTask)
    }

    // Избегаем конфликтов с application plugin
    named("distZip") {
        dependsOn(shadowJarTask)
    }
    named("distTar") {
        dependsOn(shadowJarTask)
    }
    named<CreateStartScripts>("startScripts") {
        dependsOn(shadowJarTask)
    }
}

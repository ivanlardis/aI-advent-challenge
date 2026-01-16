plugins {
    kotlin("jvm") version "1.9.20"
    kotlin("plugin.serialization") version "1.9.20"
    application
    id("com.github.johnrengelman.shadow") version "8.1.1"
}

group = "io.github.projectstarter"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    // CLI
    implementation("com.github.ajalt.clikt:clikt:4.2.0")

    // Environment variables
    implementation("io.github.cdimascio:dotenv-kotlin:6.4.1")

    // GitHub API
    implementation("io.ktor:ktor-client-core:2.3.4")
    implementation("io.ktor:ktor-client-cio:2.3.4")
    implementation("io.ktor:ktor-client-content-negotiation:2.3.4")
    implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.4")

    // SSH
    implementation("com.hierynomus:sshj:0.38.0")

    // Encryption для GitHub Secrets
    implementation("com.goterl:lazysodium-java:5.1.4")
    implementation("net.java.dev.jna:jna:5.13.0")

    // SSH Key Generation
    implementation("org.bouncycastle:bcprov-jdk18on:1.77")
    implementation("org.bouncycastle:bcpkix-jdk18on:1.77")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")

    // Logging
    implementation("org.slf4j:slf4j-simple:2.0.9")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testImplementation("io.mockk:mockk:1.13.5")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
}

application {
    mainClass.set("io.github.projectstarter.MainKt")
}

tasks {
    compileKotlin {
        kotlinOptions.jvmTarget = "17"
    }
    compileTestKotlin {
        kotlinOptions.jvmTarget = "17"
    }
    test {
        useJUnitPlatform()
    }
    shadowJar {
        dependsOn("copyGradleWrapper")
        manifest {
            attributes("Main-Class" to "io.github.projectstarter.MainKt")
        }
        // Явно включаем gradle-wrapper.jar в shadowJar
        from("build/resources/main/templates/project-template/gradle/wrapper/gradle-wrapper.jar") {
            into("templates/project-template/gradle/wrapper/")
        }
    }

    // Явно копируем gradle-wrapper.jar в build/resources (Gradle игнорирует .jar в src/main/resources)
    register("copyGradleWrapper") {
        group = "build"
        description = "Copy gradle-wrapper.jar to resources"

        doLast {
            val wrapperFile = file("gradle/wrapper/gradle-wrapper.jar")
            val targetDir = file("build/resources/main/templates/project-template/gradle/wrapper")
            targetDir.mkdirs()
            copy {
                from(wrapperFile)
                into(targetDir)
            }
        }
    }

    // Запускаем копирование перед processResources
    processResources {
        dependsOn("copyGradleWrapper")
    }
}

kotlin {
    jvmToolchain(17)
}

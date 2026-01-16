plugins {
    kotlin("jvm") version "1.9.20"
    application
    id("com.github.johnrengelman.shadow") version "8.1.1"
}

group = "io.github.{{USERNAME}}"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.ktor:ktor-server-core:2.3.4")
    implementation("io.ktor:ktor-server-netty:2.3.4")
    implementation("io.ktor:ktor-server-html-builder:2.3.4")
    implementation("org.jetbrains.exposed:exposed-core:0.44.1")
    implementation("org.jetbrains.exposed:exposed-dao:0.44.1")
    implementation("org.jetbrains.exposed:exposed-jdbc:0.44.1")
    implementation("org.postgresql:postgresql:42.6.0")
    implementation("ch.qos.logback:logback-classic:1.4.11")
}

application {
    mainClass.set("io.github.{{USERNAME}}.{{PROJECT_PACKAGE}}.ApplicationKt")
}

tasks {
    compileKotlin {
        kotlinOptions.jvmTarget = "17"
    }

    shadowJar {
        archiveBaseName.set("{{PROJECT_SLUG}}")
        archiveVersion.set("1.0.0")
        manifest {
            attributes("Main-Class" to "io.github.{{USERNAME}}.{{PROJECT_PACKAGE}}.ApplicationKt")
        }
    }
}

kotlin {
    jvmToolchain(17)
}

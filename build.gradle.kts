plugins {
    kotlin("multiplatform") version "1.9.22" apply false
    kotlin("jvm") version "1.9.22" apply false
    kotlin("js") version "1.9.22" apply false
    kotlin("plugin.serialization") version "1.9.22" apply false
    id("com.github.johnrengelman.shadow") version "8.1.1" apply false
}

allprojects {
    group = "com.lardis"
    version = "1.0.0"

    repositories {
        mavenCentral()
    }
}

plugins {
    kotlin("js")
}

dependencies {
    implementation(project(":shared"))
    implementation("org.jetbrains.kotlin-wrappers:kotlin-browser:1.0.0-pre.667")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
}

kotlin {
    js(IR) {
        browser {
            commonWebpackConfig {
                outputFileName = "team-assistant.js"
            }
            binaries.executable()
        }
    }
}

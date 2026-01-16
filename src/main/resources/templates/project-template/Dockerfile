FROM eclipse-temurin:17-jdk-jammy

WORKDIR /app

# Копируем Gradle wrapper
COPY gradlew .
COPY gradle gradle

# Копируем build файлы
COPY build.gradle.kts .
COPY settings.gradle.kts .

# Копируем исходники
COPY src src

# Даем права на выполнение gradlew
RUN chmod +x gradlew

# Собираем проект
RUN ./gradlew shadowJar --no-daemon

# Запускаем (используем shell форму для раскрытия wildcard)
CMD java -jar build/libs/{{PROJECT_SLUG}}-1.0.0-all.jar

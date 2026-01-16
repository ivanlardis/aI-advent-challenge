package io.github.projectstarter.ssh

import io.github.projectstarter.config.Config
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.transport.verification.PromiscuousVerifier
import java.io.File
import java.security.KeyPairGenerator

class VPSService(
    private val host: String,
    private val user: String,
    privateKeyPath: String? = null
) {

    private val sshClient = SSHClient()
    private var isConnected = false
    private var isAuthenticated = false

    init {
        // Trust all hosts (для MVP)
        sshClient.addHostKeyVerifier(PromiscuousVerifier())
        // Добавляем таймаут
        sshClient.timeout = 30 * 1000 // 30 секунд на операции
    }

    suspend fun connect(): Boolean {
        return try {
            sshClient.connect(host, 22)
            isConnected = true
            true
        } catch (e: Exception) {
            false
        }
    }

    suspend fun authenticateWithPassword(password: String): Boolean {
        if (!isConnected) {
            return false
        }

        return try {
            sshClient.authPassword(user, password)
            isAuthenticated = true
            true
        } catch (e: Exception) {
            false
        }
    }

    suspend fun executeCommand(command: String): SSHCommandResult {
        if (!isAuthenticated) {
            return SSHCommandResult(
                exitCode = -1,
                output = "",
                error = "Not authenticated"
            )
        }

        return try {
            val session = sshClient.startSession()
            val cmd = session.exec(command)

            val output = cmd.inputStream.bufferedReader().use { it.readText() }
            val error = cmd.errorStream.bufferedReader().use { it.readText() }
            cmd.join()

            val exitCode = cmd.exitStatus

            session.close()

            SSHCommandResult(
                exitCode = exitCode,
                output = output,
                error = error
            )
        } catch (e: Exception) {
            SSHCommandResult(
                exitCode = -1,
                output = "",
                error = e.message ?: "Unknown error"
            )
        }
    }

    suspend fun checkDockerInstalled(): Boolean {
        val result = executeCommand("docker --version")
        return result.exitCode == 0
    }

    suspend fun installDocker(): Boolean {
        val result = executeCommand(
            """
            curl -fsSL https://get.docker.com | sh 2>&1 &&
            systemctl enable docker 2>&1 &&
            systemctl start docker 2>&1
            """.trimIndent()
        )
        return result.exitCode == 0
    }

    suspend fun checkDockerComposeInstalled(): Boolean {
        val result = executeCommand("docker compose version")
        return result.exitCode == 0
    }

    suspend fun installDockerCompose(): Boolean {
        val result = executeCommand(
            """
            # Проверяем, есть ли уже docker compose
            if docker compose version &>/dev/null; then
                echo "Docker Compose already installed"
                exit 0
            fi

            # Устанавливаем Docker Compose V2 (плагин)
            DOCKER_CONFIG=${'$'}{DOCKER_CONFIG:-${'$'}HOME/.docker}
            mkdir -p ${'$'}DOCKER_CONFIG/cli-plugins
            curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
              -o ${'$'}DOCKER_CONFIG/cli-plugins/docker-compose
            chmod +x ${'$'}DOCKER_CONFIG/cli-plugins/docker-compose

            # Проверяем установку
            docker compose version
            """.trimIndent()
        )
        return result.exitCode == 0
    }

    suspend fun addSSHPublicKey(publicKey: String): Boolean {
        val result = executeCommand(
            """
            mkdir -p ~/.ssh 2>&1 &&
            echo "$publicKey" >> ~/.ssh/authorized_keys 2>&1 &&
            chmod 700 ~/.ssh 2>&1 &&
            chmod 600 ~/.ssh/authorized_keys 2>&1
            """.trimIndent()
        )
        return result.exitCode == 0
    }

    suspend fun close() {
        try {
            if (isConnected) {
                sshClient.disconnect()
                isConnected = false
                isAuthenticated = false
            }
        } catch (e: Exception) {
            // Игнорируем ошибки при закрытии
        }
    }

    companion object {
        init {
            // Регистрируем BouncyCastle provider
            java.security.Security.addProvider(org.bouncycastle.jce.provider.BouncyCastleProvider())
        }

        fun generateSSHKeyPair(): SSHKeyPair {
            return try {
                // Используем RSA ключ для лучшей совместимости с GitHub Actions
                val privateKeyFile = java.io.File("/tmp/project_starter_rsa")
                val publicKeyFile = java.io.File("/tmp/project_starter_rsa.pub")

                if (privateKeyFile.exists() && publicKeyFile.exists()) {
                    // Читаем RSA ключи
                    val privateKey = privateKeyFile.readText()
                    val publicKey = publicKeyFile.readText().trim()

                    SSHKeyPair(
                        privateKey = privateKey,
                        publicKey = publicKey
                    )
                } else {
                    // Фоллбэк: генерируем новые ключи (для тестов)
                    val keyPairGenerator = KeyPairGenerator.getInstance("Ed25519", "BC")
                    val keyPair = keyPairGenerator.generateKeyPair()

                    val privateKeyPem = convertToOpenSSHPrivateKey(keyPair.private, keyPair.public)
                    val publicKeySSH = convertToOpenSSHPublicKey(keyPair.public)

                    SSHKeyPair(
                        privateKey = privateKeyPem,
                        publicKey = publicKeySSH
                    )
                }
            } catch (e: Exception) {
                throw Exception("Failed to generate SSH key pair: ${e.message}", e)
            }
        }

        private fun convertToOpenSSHPrivateKey(privateKey: java.security.PrivateKey, publicKey: java.security.PublicKey): String {
            // Используем BouncyCastle для генерации OpenSSH формата
            val keyInfo = org.bouncycastle.asn1.pkcs.PrivateKeyInfo.getInstance(privateKey.encoded)

            // Для ED25519 используем стандартный OpenSSH формат
            val stringWriter = java.io.StringWriter()
            val pemWriter = org.bouncycastle.util.io.pem.PemWriter(stringWriter)

            pemWriter.writeObject(
                org.bouncycastle.util.io.pem.PemObject(
                    "OPENSSH PRIVATE KEY",
                    encodeOpenSSHPrivateKey(privateKey, publicKey)
                )
            )
            pemWriter.close()

            return stringWriter.toString()
        }

        private fun encodeOpenSSHPrivateKey(privateKey: java.security.PrivateKey, publicKey: java.security.PublicKey): ByteArray {
            // OpenSSH формат для ED25519 приватного ключа
            // Формат: "openssh-key-v1" + null byte + header + private key data
            val baos = java.io.ByteArrayOutputStream()
            val dos = java.io.DataOutputStream(baos)

            // Magic header
            dos.write("openssh-key-v1\u0000".toByteArray(Charsets.US_ASCII))

            // Cipher name (none - без шифрования)
            writeString(dos, "none")
            // KDF name
            writeString(dos, "none")
            // KDF data (empty)
            writeString(dos, "")

            // Number of keys
            dos.writeInt(1)

            // Public key
            val publicKeyBytes = encodePublicKeyBytes(publicKey)
            writeBytes(dos, publicKeyBytes)

            // Private key section
            val privateKeySection = encodePrivateKeySection(privateKey, publicKey, publicKeyBytes)
            writeBytes(dos, privateKeySection)

            dos.close()
            return baos.toByteArray()
        }

        private fun encodePublicKeyBytes(publicKey: java.security.PublicKey): ByteArray {
            val baos = java.io.ByteArrayOutputStream()
            val dos = java.io.DataOutputStream(baos)

            writeString(dos, "ssh-ed25519")

            // ED25519 публичный ключ - 32 байта
            val pubKeyBytes = publicKey.encoded
            writeBytes(dos, pubKeyBytes.copyOfRange(pubKeyBytes.size - 32, pubKeyBytes.size))

            dos.close()
            return baos.toByteArray()
        }

        private fun encodePrivateKeySection(privateKey: java.security.PrivateKey, publicKey: java.security.PublicKey, publicKeyBytes: ByteArray): ByteArray {
            val baos = java.io.ByteArrayOutputStream()
            val dos = java.io.DataOutputStream(baos)

            // Check bytes (random, для проверки расшифровки)
            val checkBytes = java.security.SecureRandom().nextInt()
            dos.writeInt(checkBytes)
            dos.writeInt(checkBytes)

            // Копируем публичный ключ
            dos.write(publicKeyBytes)

            // Приватный ключ (64 байта для ED25519)
            val privKeyBytes = privateKey.encoded
            writeBytes(dos, privKeyBytes.copyOfRange(privKeyBytes.size - 64, privKeyBytes.size))

            // Comment
            writeString(dos, "project-starter-cli")

            // Padding
            val padding = 8 - (baos.size() % 8)
            for (i in 1..padding) {
                dos.writeByte(i)
            }

            dos.close()
            return baos.toByteArray()
        }

        private fun convertToOpenSSHPublicKey(publicKey: java.security.PublicKey): String {
            // OpenSSH формат: ssh-ed25519 <base64-encoded-key> comment
            val baos = java.io.ByteArrayOutputStream()
            val dos = java.io.DataOutputStream(baos)

            // Тип ключа
            writeString(dos, "ssh-ed25519")

            // Публичный ключ (32 байта для ED25519)
            val pubKeyBytes = publicKey.encoded
            val ed25519Key = pubKeyBytes.copyOfRange(pubKeyBytes.size - 32, pubKeyBytes.size)
            writeBytes(dos, ed25519Key)

            dos.close()

            val keyBase64 = java.util.Base64.getEncoder().encodeToString(baos.toByteArray())
            return "ssh-ed25519 $keyBase64 project-starter-cli"
        }

        private fun writeString(dos: java.io.DataOutputStream, str: String) {
            val bytes = str.toByteArray(Charsets.UTF_8)
            dos.writeInt(bytes.size)
            dos.write(bytes)
        }

        private fun writeBytes(dos: java.io.DataOutputStream, bytes: ByteArray) {
            dos.writeInt(bytes.size)
            dos.write(bytes)
        }
    }
}

data class SSHCommandResult(
    val exitCode: Int,
    val output: String,
    val error: String
) {
    val isSuccess: Boolean
        get() = exitCode == 0
}

data class SSHKeyPair(
    val privateKey: String,
    val publicKey: String
)

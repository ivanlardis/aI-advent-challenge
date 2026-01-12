package rag.embeddings

import ai.djl.huggingface.tokenizers.HuggingFaceTokenizer
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import java.nio.LongBuffer
import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.outputStream

/**
 * ONNX embeddings векторизатор на базе Sentence Transformers.
 * Модель и токенизатор загружаются из ресурсов, запакованных в JAR.
 */
class OnnxEmbeddingVectorizer(
    private val modelResourcePath: String = "/models/model.onnx",
    private val tokenizerResourcePath: String = "/models/tokenizer.json",
    private val maxLength: Int = 256
) : Vectorizer {

    private val environment: OrtEnvironment = OrtEnvironment.getEnvironment()
    private val session: OrtSession
    private val tokenizer: HuggingFaceTokenizer

    override val dimension: Int

    init {
        val modelFile = extractResource(modelResourcePath, "onnx-model", ".onnx")
        val tokenizerFile = extractResource(tokenizerResourcePath, "onnx-tokenizer", ".json")

        session = OrtSession.SessionOptions().use { options ->
            environment.createSession(modelFile.toString(), options)
        }

        tokenizer = HuggingFaceTokenizer.newInstance(
            tokenizerFile,
            mapOf(
                "padding" to "max_length",
                "truncation" to "true",
                "maxLength" to maxLength.toString()
            )
        )

        val outputShape = (session.outputInfo.values.first().info as TensorInfo).shape
        dimension = outputShape.last().toInt()

        println("[ONNX] Model loaded: dimension=$dimension")
    }

    override fun vectorize(text: String): FloatArray {
        val encoding = tokenizer.encode(text)
        val inputIds = encoding.ids.map { it.toLong() }.toLongArray()
        val attentionMask = encoding.attentionMask.map { it.toLong() }.toLongArray()
        val typeIds = encoding.typeIds?.map { it.toLong() }?.toLongArray()

        val shape = longArrayOf(1, inputIds.size.toLong())
        val tensors = mutableMapOf<String, OnnxTensor>()
        tensors["input_ids"] = OnnxTensor.createTensor(environment, LongBuffer.wrap(inputIds), shape)
        tensors["attention_mask"] = OnnxTensor.createTensor(environment, LongBuffer.wrap(attentionMask), shape)
        if (session.inputNames.contains("token_type_ids") && typeIds != null && typeIds.isNotEmpty()) {
            tensors["token_type_ids"] = OnnxTensor.createTensor(environment, LongBuffer.wrap(typeIds), shape)
        }

        val results = session.run(tensors)
        tensors.values.forEach { it.close() }

        val value = results[0].value
        val embedding = when (value) {
            is Array<*> -> extractEmbedding(value, attentionMask)
            else -> throw IllegalStateException("Unsupported ONNX output type: ${value?.javaClass}")
        }

        results.close()
        return embedding
    }

    @Suppress("UNCHECKED_CAST")
    private fun extractEmbedding(output: Array<*>, attentionMask: LongArray): FloatArray {
        val first = output.firstOrNull()
            ?: throw IllegalStateException("Empty ONNX output")

        return when (first) {
            is FloatArray -> first // [batch, dim] -> берем первую строку
            is Array<*> -> {
                val tokenEmbeddings = (first as Array<*>).filterIsInstance<FloatArray>()
                require(tokenEmbeddings.isNotEmpty()) { "Unexpected ONNX output shape" }
                meanPool(tokenEmbeddings, attentionMask)
            }
            else -> throw IllegalStateException("Unexpected ONNX output element: ${first.javaClass}")
        }
    }

    private fun meanPool(tokenEmbeddings: List<FloatArray>, attentionMask: LongArray): FloatArray {
        val dim = tokenEmbeddings.firstOrNull()?.size ?: 0
        val pooled = FloatArray(dim)
        var count = 0

        val limit = minOf(tokenEmbeddings.size, attentionMask.size)
        for (i in 0 until limit) {
            if (attentionMask[i] == 0L) continue
            val tokenVec = tokenEmbeddings[i]
            for (j in 0 until dim) {
                pooled[j] += tokenVec[j]
            }
            count++
        }

        if (count == 0) return pooled
        val scale = 1.0f / count
        for (j in 0 until dim) {
            pooled[j] *= scale
        }
        return pooled
    }

    private fun extractResource(resourcePath: String, prefix: String, suffix: String): Path {
        val stream = javaClass.getResourceAsStream(resourcePath)
            ?: throw IllegalArgumentException("Model not found: $resourcePath")

        val tempFile = Files.createTempFile(prefix, suffix).also { it.toFile().deleteOnExit() }
        stream.use { input ->
            tempFile.outputStream().use { output ->
                input.copyTo(output)
            }
        }
        return tempFile
    }

    override fun close() {
        session.close()
        tokenizer.close()
    }
}

package teamassistant.cache

import config.CachedIssue
import config.CachedIssuesData
import config.toScoredIssue
import dto.ScoredIssue
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import org.slf4j.LoggerFactory
import java.nio.file.Files
import java.nio.file.Paths
import java.nio.file.StandardOpenOption
import kotlin.time.Duration
import kotlin.time.Duration.Companion.minutes
import kotlin.time.ExperimentalTime

/**
 * Кэш для GitHub Issues в JSON файле
 * Используется для быстрой загрузки между запусками
 */
@OptIn(ExperimentalTime::class)
class IssueCache(
    private val cacheFilePath: String = ".team-assistant/cache.json",
    private val ttl: Duration = 60.minutes
) {
    private val logger = LoggerFactory.getLogger(IssueCache::class.java)
    private val json = Json { prettyPrint = true; ignoreUnknownKeys = true }

    @Volatile
    private var cachedData: CachedIssuesData? = null

    /**
     * Загрузить данные из кэша
     * Возвращает null если кэш не существует или устарел
     */
    suspend fun load(): CachedIssuesData? = withContext(Dispatchers.IO) {
        try {
            val path = Paths.get(cacheFilePath)

            if (!Files.exists(path)) {
                logger.debug("Cache file does not exist: $cacheFilePath")
                return@withContext null
            }

            val content = Files.readString(path)
            val data = json.decodeFromString<CachedIssuesData>(content)

            // Check TTL
            val lastUpdated = kotlinx.datetime.Instant.parse(data.lastUpdated)
            val now = kotlinx.datetime.Clock.System.now()
            val age = now - lastUpdated

            if (age > ttl) {
                logger.info("Cache is expired (age=$age, ttl=$ttl)")
                return@withContext null
            }

            logger.info("Loaded ${data.issues.size} issues from cache (age=$age)")
            cachedData = data
            data
        } catch (e: Exception) {
            logger.error("Failed to load cache from $cacheFilePath", e)
            null
        }
    }

    /**
     * Сохранить данные в кэш
     */
    suspend fun save(issues: List<ScoredIssue>) = withContext(Dispatchers.IO) {
        try {
            val path = Paths.get(cacheFilePath)
            Files.createDirectories(path.parent)

            val now = kotlinx.datetime.Clock.System.now()
            val cachedIssues = issues.map { issue ->
                CachedIssue(
                    number = issue.issue.number,
                    title = issue.issue.title,
                    state = issue.issue.state,
                    createdAt = issue.issue.createdAt,
                    updatedAt = issue.issue.updatedAt,
                    priorityScore = issue.priorityScore,
                    commitCount = issue.commitCount,
                    ragRelevance = issue.ragScore
                )
            }

            val data = CachedIssuesData(
                issues = cachedIssues,
                lastUpdated = now.toString()
            )

            val content = json.encodeToString(CachedIssuesData.serializer(), data)
            Files.writeString(
                path,
                content,
                StandardOpenOption.CREATE,
                StandardOpenOption.TRUNCATE_EXISTING
            )

            cachedData = data
            logger.info("Saved ${issues.size} issues to cache at $cacheFilePath")
        } catch (e: Exception) {
            logger.error("Failed to save cache to $cacheFilePath", e)
        }
    }

    /**
     * Конвертировать кэшированные данные в ScoredIssue
     */
    fun fromCache(cachedData: CachedIssuesData): List<ScoredIssue> {
        return cachedData.issues.map { it.toScoredIssue() }
    }

    /**
     * Очистить кэш
     */
    suspend fun clear() = withContext(Dispatchers.IO) {
        try {
            val path = Paths.get(cacheFilePath)
            if (Files.exists(path)) {
                Files.delete(path)
                cachedData = null
                logger.info("Cleared cache at $cacheFilePath")
            }
        } catch (e: Exception) {
            logger.error("Failed to clear cache", e)
        }
    }

    /**
     * Получить информацию о кэше
     */
    suspend fun getCacheInfo(): CacheInfo = withContext(Dispatchers.IO) {
        try {
            val path = Paths.get(cacheFilePath)

            if (!Files.exists(path)) {
                return@withContext CacheInfo(exists = false, size = 0, lastUpdated = null)
            }

            val data = cachedData ?: load()
            val size = Files.size(path)

            CacheInfo(
                exists = true,
                size = size,
                lastUpdated = data?.lastUpdated,
                issuesCount = data?.issues?.size ?: 0
            )
        } catch (e: Exception) {
            logger.error("Failed to get cache info", e)
            CacheInfo(exists = false, size = 0, lastUpdated = null)
        }
    }
}

data class CacheInfo(
    val exists: Boolean,
    val size: Long,
    val lastUpdated: String?,
    val issuesCount: Int = 0
)

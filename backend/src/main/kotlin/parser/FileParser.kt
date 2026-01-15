package parser

import java.io.File

/**
 * Интерфейс для парсинга файлов
 */
interface FileParser {
    /**
     * Парсит файл и возвращает документ
     */
    fun parse(file: File): Document

    /**
     * Проверяет, поддерживается ли файл этим парсером
     */
    fun supports(file: File): Boolean
}

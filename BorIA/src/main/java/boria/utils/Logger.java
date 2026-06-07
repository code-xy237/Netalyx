package boria.utils;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Utilitaire de journalisation simple pour BorIA.
 *
 * Niveaux disponibles : INFO, WARN, ERROR, DEBUG
 * Format : [YYYY-MM-DD HH:mm:ss] [NIVEAU] message
 *
 * Extension possible : écriture dans un fichier de log,
 *                      intégration SLF4J / Logback.
 */
public class Logger {

    private static final DateTimeFormatter FMT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static boolean debugEnabled = false;

    // ── API publique ────────────────────────────────────────────────────────

    public static void info(String message) {
        log("INFO ", message);
    }

    public static void warn(String message) {
        log("WARN ", message);
    }

    public static void error(String message) {
        log("ERROR", message);
    }

    public static void debug(String message) {
        if (debugEnabled) log("DEBUG", message);
    }

    // ── Interne ────────────────────────────────────────────────────────────

    private static void log(String level, String message) {
        String timestamp = LocalDateTime.now().format(FMT);
        String caller    = getCallerClass();
        System.out.printf("[%s] [%s] [%s] %s%n", timestamp, level, caller, message);
    }

    /**
     * Remonte la pile d'appel pour identifier la classe appelante.
     * Ignore les cadres internes à Logger lui-même.
     */
    private static String getCallerClass() {
        StackTraceElement[] stack = Thread.currentThread().getStackTrace();
        for (StackTraceElement frame : stack) {
            String cls = frame.getClassName();
            if (!cls.equals(Logger.class.getName()) &&
                !cls.equals(Thread.class.getName())) {
                // Retourne seulement le nom simple de la classe
                int dot = cls.lastIndexOf('.');
                return dot >= 0 ? cls.substring(dot + 1) : cls;
            }
        }
        return "Unknown";
    }

    // ── Configuration ──────────────────────────────────────────────────────

    public static void enableDebug()  { debugEnabled = true; }
    public static void disableDebug() { debugEnabled = false; }
    public static boolean isDebugEnabled() { return debugEnabled; }
}

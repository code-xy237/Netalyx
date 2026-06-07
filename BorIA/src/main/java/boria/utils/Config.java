package boria.utils;

import java.io.*;
import java.nio.file.*;
import java.util.Properties;

/**
 * Chargeur de configuration pour BorIA.
 *
 * Lit le fichier resources/boria.properties au démarrage.
 * Toutes les valeurs ont des défauts intégrés pour fonctionner
 * sans fichier de config.
 *
 * Exemple de fichier boria.properties :
 *   bot.name=BorIA
 *   nn.maxIterations=10000
 *   nn.targetError=0.001
 *   nlp.modelPath=resources/models/en-sent.bin
 *   aiml.path=resources/aiml
 *   debug=false
 */
public class Config {

    private static final String CONFIG_FILE = "resources/boria.properties";
    private static final Properties props   = new Properties();
    private static boolean         loaded   = false;

    // ── Chargement ─────────────────────────────────────────────────────────

    public static void load() {
        File file = new File(CONFIG_FILE);
        if (!file.exists()) {
            Logger.warn("Fichier de config introuvable (" + CONFIG_FILE + "). Valeurs par défaut utilisées.");
            applyDefaults();
            loaded = true;
            return;
        }
        try (InputStream in = new FileInputStream(file)) {
            props.load(in);
            applyDefaults(); // complète les clés manquantes
            loaded = true;
            Logger.info("Configuration chargée depuis " + CONFIG_FILE);
        } catch (IOException e) {
            Logger.error("Impossible de lire " + CONFIG_FILE + " : " + e.getMessage());
            applyDefaults();
            loaded = true;
        }
    }

    private static void applyDefaults() {
        props.putIfAbsent("bot.name",         "BorIA");
        props.putIfAbsent("nn.maxIterations", "10000");
        props.putIfAbsent("nn.targetError",   "0.001");
        props.putIfAbsent("nlp.modelPath",    "resources/models/en-sent.bin");
        props.putIfAbsent("aiml.path",        "resources");
        props.putIfAbsent("debug",            "false");
    }

    // ── Accesseurs ─────────────────────────────────────────────────────────

    public static String get(String key) {
        ensureLoaded();
        return props.getProperty(key);
    }

    public static String get(String key, String defaultValue) {
        ensureLoaded();
        return props.getProperty(key, defaultValue);
    }

    public static int getInt(String key, int defaultValue) {
        String val = get(key);
        if (val == null) return defaultValue;
        try { return Integer.parseInt(val.trim()); }
        catch (NumberFormatException e) { return defaultValue; }
    }

    public static double getDouble(String key, double defaultValue) {
        String val = get(key);
        if (val == null) return defaultValue;
        try { return Double.parseDouble(val.trim()); }
        catch (NumberFormatException e) { return defaultValue; }
    }

    public static boolean getBoolean(String key, boolean defaultValue) {
        String val = get(key);
        if (val == null) return defaultValue;
        return Boolean.parseBoolean(val.trim());
    }

    // ── Persistance ────────────────────────────────────────────────────────

    /**
     * Sauvegarde la configuration actuelle dans le fichier.
     */
    public static void save() {
        try {
            Files.createDirectories(Paths.get("resources"));
            try (OutputStream out = new FileOutputStream(CONFIG_FILE)) {
                props.store(out, "BorIA Configuration");
                Logger.info("Configuration sauvegardée.");
            }
        } catch (IOException e) {
            Logger.error("Impossible de sauvegarder la config : " + e.getMessage());
        }
    }

    public static void set(String key, String value) {
        ensureLoaded();
        props.setProperty(key, value);
    }

    // ── Interne ────────────────────────────────────────────────────────────

    private static void ensureLoaded() {
        if (!loaded) load();
    }
}

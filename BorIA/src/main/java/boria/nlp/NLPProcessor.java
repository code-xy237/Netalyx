package boria.nlp;

import boria.utils.Logger;
import opennlp.tools.sentdetect.SentenceDetectorME;
import opennlp.tools.sentdetect.SentenceModel;
import opennlp.tools.tokenize.SimpleTokenizer;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;

/**
 * Module de traitement du langage naturel (NLP).
 *
 * Fonctionnalités :
 *  - Tokenisation du texte
 *  - Détection de phrases (Apache OpenNLP)
 *  - Nettoyage et normalisation de l'entrée utilisateur
 *
 * Si le modèle OpenNLP n'est pas disponible, bascule sur
 * un traitement basique sans dépendance externe.
 */
public class NLPProcessor {

    private static final String SENTENCE_MODEL_PATH = "resources/models/en-sent.bin";

    private SentenceDetectorME sentenceDetector;
    private boolean            nlpAvailable = false;

    // ── Chargement ─────────────────────────────────────────────────────────

    public void load() {
        Logger.info("Chargement du module NLP...");
        try (InputStream modelIn = new FileInputStream(SENTENCE_MODEL_PATH)) {
            SentenceModel model = new SentenceModel(modelIn);
            sentenceDetector = new SentenceDetectorME(model);
            nlpAvailable = true;
            Logger.info("Modèle OpenNLP chargé avec succès.");
        } catch (IOException e) {
            Logger.warn("Modèle OpenNLP introuvable. Traitement NLP basique activé.");
            nlpAvailable = false;
        }
    }

    // ── Traitement principal ────────────────────────────────────────────────

    /**
     * Nettoie et normalise l'entrée utilisateur.
     *
     * @param rawInput texte brut
     * @return texte normalisé prêt pour la génération de réponse
     */
    public String process(String rawInput) {
        if (rawInput == null) return "";

        String cleaned = normalize(rawInput);

        if (nlpAvailable) {
            String[] sentences = detectSentences(cleaned);
            Logger.info("Phrases détectées : " + Arrays.toString(sentences));
        }

        return cleaned;
    }

    /**
     * Détecte les phrases dans un texte (nécessite le modèle OpenNLP).
     */
    public String[] detectSentences(String text) {
        if (!nlpAvailable) return new String[]{text};
        return sentenceDetector.sentDetect(text);
    }

    /**
     * Tokenise un texte en mots individuels.
     */
    public String[] tokenize(String text) {
        return SimpleTokenizer.INSTANCE.tokenize(text);
    }

    // ── Normalisation ──────────────────────────────────────────────────────

    /**
     * Normalise le texte : trim, espaces multiples, etc.
     */
    private String normalize(String text) {
        return text
            .trim()
            .replaceAll("\\s+", " ")         // espaces multiples → un seul
            .replaceAll("[^\\p{L}\\p{N}\\p{P}\\s]", ""); // supprime les caractères spéciaux non utiles
    }

    // ── Getters ────────────────────────────────────────────────────────────
    public boolean isNlpAvailable() { return nlpAvailable; }
}

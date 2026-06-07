package boria.core;

import boria.learning.NeuralNetworkManager;
import boria.nlp.NLPProcessor;
import boria.nlp.ChatbotResponder;
import boria.vision.VisionProcessor;
import boria.utils.Logger;

/**
 * Moteur central de BorIA.
 * Orchestre tous les modules IA : NLP, réseau de neurones, vision.
 * Utilise le pattern Singleton pour garantir une instance unique.
 */
public class BorIAEngine {

    private static BorIAEngine instance;

    private NLPProcessor       nlpProcessor;
    private NeuralNetworkManager nnManager;
    private ChatbotResponder   chatbotResponder;
    private VisionProcessor    visionProcessor;

    private boolean initialized = false;

    // ── Singleton ──────────────────────────────────────────────────────────
    private BorIAEngine() {}

    public static synchronized BorIAEngine getInstance() {
        if (instance == null) {
            instance = new BorIAEngine();
        }
        return instance;
    }

    // ── Initialisation ─────────────────────────────────────────────────────
    public void initialize() {
        if (initialized) return;

        Logger.info("Initialisation du moteur BorIA...");

        try {
            nlpProcessor      = new NLPProcessor();
            nnManager         = new NeuralNetworkManager();
            chatbotResponder  = new ChatbotResponder();
            visionProcessor   = new VisionProcessor();

            nlpProcessor.load();
            nnManager.buildAndTrainXOR();
            chatbotResponder.load();

            initialized = true;
            Logger.info("Moteur BorIA initialisé avec succès.");

        } catch (Exception e) {
            Logger.error("Échec de l'initialisation du moteur BorIA : " + e.getMessage());
            throw new RuntimeException("Impossible d'initialiser BorIA", e);
        }
    }

    // ── API publique ────────────────────────────────────────────────────────

    /**
     * Traite une entrée textuelle et retourne une réponse.
     *
     * @param userInput texte saisi par l'utilisateur
     * @return réponse générée par BorIA
     */
    public String respond(String userInput) {
        if (!initialized) {
            return "[BorIA] Moteur non initialisé.";
        }
        if (userInput == null || userInput.isBlank()) {
            return "[BorIA] Veuillez saisir un message.";
        }

        Logger.info("Entrée reçue : " + userInput);

        // 1. Analyse NLP
        String processedInput = nlpProcessor.process(userInput);

        // 2. Génération de la réponse via le chatbot AIML/règles
        String response = chatbotResponder.respond(processedInput);

        Logger.info("Réponse générée : " + response);
        return response;
    }

    /**
     * Prédit la sortie XOR via le réseau de neurones.
     *
     * @param a première entrée (0 ou 1)
     * @param b deuxième entrée (0 ou 1)
     * @return valeur prédite entre 0 et 1
     */
    public double predictXOR(double a, double b) {
        if (!initialized) throw new IllegalStateException("Moteur non initialisé");
        return nnManager.predict(a, b);
    }

    /**
     * Traite une image à partir d'un chemin de fichier.
     *
     * @param imagePath chemin absolu de l'image
     * @return description ou résultat de la vision
     */
    public String analyzeImage(String imagePath) {
        if (!initialized) throw new IllegalStateException("Moteur non initialisé");
        return visionProcessor.process(imagePath);
    }

    // ── Arrêt propre ───────────────────────────────────────────────────────
    public void shutdown() {
        Logger.info("Arrêt du moteur BorIA...");
        if (nnManager != null) nnManager.shutdown();
        initialized = false;
    }

    // ── Getters ────────────────────────────────────────────────────────────
    public boolean isInitialized()       { return initialized; }
    public NeuralNetworkManager getNNManager() { return nnManager; }
    public NLPProcessor getNLPProcessor()     { return nlpProcessor; }
}

package boria.nlp;

import boria.utils.Logger;
import org.alicebot.ab.Bot;
import org.alicebot.ab.Chat;
import org.alicebot.ab.MagicStrings;

import java.util.HashMap;
import java.util.Map;

/**
 * Génère des réponses conversationnelles.
 *
 * Stratégie en deux niveaux :
 *  1. Moteur AIML via Program AB (org.alicebot.ab)
 *     — charge les fichiers *.aiml du dossier resources/aiml/
 *  2. Fallback par règles Java si AIML non disponible
 *
 * Pour ajouter des réponses : éditer resources/aiml/boria.aiml
 * ou enrichir la map RULES ci-dessous.
 */
public class ChatbotResponder {

    private static final String BOT_NAME  = "BorIA";
    private static final String BOT_PATH  = "resources";

    private Chat    aimlChat;
    private boolean aimlAvailable = false;

    /** Règles de secours (mots-clés → réponses). */
    private static final Map<String, String> RULES = new HashMap<>();

    static {
        RULES.put("bonjour",   "Bonjour ! Je suis BorIA, votre assistant IA. Comment puis-je vous aider ?");
        RULES.put("salut",     "Salut ! Ravi de vous parler. Qu'est-ce que je peux faire pour vous ?");
        RULES.put("hello",     "Hello! I'm BorIA. How can I assist you?");
        RULES.put("aide",      "Je peux répondre à vos questions, analyser des images et effectuer des prédictions. Que voulez-vous faire ?");
        RULES.put("help",      "I can answer questions, analyze images, and make predictions. What would you like to do?");
        RULES.put("xor",       "Le XOR est un problème classique en IA : 0⊕0=0, 0⊕1=1, 1⊕0=1, 1⊕1=0. Mon réseau de neurones l'a appris !");
        RULES.put("merci",     "De rien ! C'est avec plaisir que je vous aide.");
        RULES.put("au revoir", "Au revoir ! À bientôt.");
        RULES.put("bye",       "Goodbye! See you next time.");
        RULES.put("qui es-tu", "Je suis BorIA, une intelligence artificielle développée en Java. Je combine NLP, réseaux de neurones et vision par ordinateur.");
        RULES.put("capabilities", "Mes capacités : traitement NLP, réseau de neurones (Encog), vision OpenCV, et apprentissage automatique (Weka/Spark).");
    }

    // ── Chargement ─────────────────────────────────────────────────────────

    public void load() {
        Logger.info("Chargement du module Chatbot...");
        try {
            MagicStrings.root_path = BOT_PATH;
            Bot bot = new Bot(BOT_NAME, BOT_PATH);
            aimlChat = new Chat(bot);
            aimlAvailable = true;
            Logger.info("Moteur AIML chargé avec succès.");
        } catch (Exception e) {
            Logger.warn("AIML indisponible (" + e.getMessage() + "). Utilisation du moteur de règles.");
            aimlAvailable = false;
        }
    }

    // ── Génération de réponse ──────────────────────────────────────────────

    /**
     * Génère une réponse à partir de l'entrée utilisateur normalisée.
     *
     * @param input texte normalisé par NLPProcessor
     * @return réponse textuelle
     */
    public String respond(String input) {
        if (input == null || input.isBlank()) {
            return "Je n'ai pas compris votre message. Pouvez-vous reformuler ?";
        }

        // Niveau 1 : AIML
        if (aimlAvailable) {
            try {
                String aimlResponse = aimlChat.multisentenceRespond(input);
                if (aimlResponse != null && !aimlResponse.isBlank()) {
                    return aimlResponse;
                }
            } catch (Exception e) {
                Logger.warn("Erreur AIML : " + e.getMessage());
            }
        }

        // Niveau 2 : Règles Java (fallback)
        return respondByRules(input.toLowerCase());
    }

    // ── Moteur de règles ───────────────────────────────────────────────────

    private String respondByRules(String input) {
        for (Map.Entry<String, String> entry : RULES.entrySet()) {
            if (input.contains(entry.getKey())) {
                return entry.getValue();
            }
        }
        return defaultResponse(input);
    }

    private String defaultResponse(String input) {
        return String.format(
            "Vous avez dit : \"%s\". Je suis encore en apprentissage et je ne " +
            "comprends pas encore tout. Essayez de me demander de l'aide !",
            input
        );
    }

    // ── Getters ────────────────────────────────────────────────────────────
    public boolean isAimlAvailable() { return aimlAvailable; }
}

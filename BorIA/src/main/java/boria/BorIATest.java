package boria;

import boria.learning.NeuralNetworkManager;
import boria.nlp.NLPProcessor;
import boria.nlp.ChatbotResponder;
import org.junit.jupiter.api.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires pour les modules principaux de BorIA.
 *
 * Exécution :  mvn test
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class BorIATest {

    // ── Réseau de neurones ─────────────────────────────────────────────────

    static NeuralNetworkManager nnManager;

    @BeforeAll
    static void setUpNN() {
        nnManager = new NeuralNetworkManager();
        nnManager.buildAndTrainXOR();
    }

    @Test
    @Order(1)
    @DisplayName("Le réseau doit être entraîné après buildAndTrainXOR()")
    void testNetworkTrained() {
        assertTrue(nnManager.isTrained(), "Le réseau devrait être marqué comme entraîné.");
    }

    @Test
    @Order(2)
    @DisplayName("XOR(0,0) ≈ 0")
    void testXOR_00() {
        double result = nnManager.predict(0, 0);
        assertTrue(result < 0.1,
            "XOR(0,0) devrait être proche de 0, obtenu : " + result);
    }

    @Test
    @Order(3)
    @DisplayName("XOR(0,1) ≈ 1")
    void testXOR_01() {
        double result = nnManager.predict(0, 1);
        assertTrue(result > 0.9,
            "XOR(0,1) devrait être proche de 1, obtenu : " + result);
    }

    @Test
    @Order(4)
    @DisplayName("XOR(1,0) ≈ 1")
    void testXOR_10() {
        double result = nnManager.predict(1, 0);
        assertTrue(result > 0.9,
            "XOR(1,0) devrait être proche de 1, obtenu : " + result);
    }

    @Test
    @Order(5)
    @DisplayName("XOR(1,1) ≈ 0")
    void testXOR_11() {
        double result = nnManager.predict(1, 1);
        assertTrue(result < 0.1,
            "XOR(1,1) devrait être proche de 0, obtenu : " + result);
    }

    @Test
    @Order(6)
    @DisplayName("predict() sans entraînement doit lancer une exception")
    void testPredictWithoutTraining() {
        NeuralNetworkManager fresh = new NeuralNetworkManager();
        assertThrows(IllegalStateException.class,
            () -> fresh.predict(0, 1),
            "Une exception doit être levée si le réseau n'est pas entraîné."
        );
    }

    // ── NLP ────────────────────────────────────────────────────────────────

    static NLPProcessor nlp;

    @BeforeAll
    static void setUpNLP() {
        nlp = new NLPProcessor();
        nlp.load(); // peut échouer si le modèle est absent (mode basique)
    }

    @Test
    @Order(10)
    @DisplayName("process() ne doit pas retourner null")
    void testProcessNotNull() {
        assertNotNull(nlp.process("Bonjour BorIA !"));
    }

    @Test
    @Order(11)
    @DisplayName("process() doit normaliser les espaces multiples")
    void testProcessNormalizesSpaces() {
        String result = nlp.process("  Bonjour   monde  ");
        assertEquals("Bonjour monde", result);
    }

    @Test
    @Order(12)
    @DisplayName("process(null) doit retourner une chaîne vide")
    void testProcessNull() {
        assertEquals("", nlp.process(null));
    }

    @Test
    @Order(13)
    @DisplayName("tokenize() doit retourner les mots séparément")
    void testTokenize() {
        String[] tokens = nlp.tokenize("Bonjour monde");
        assertEquals(2, tokens.length);
        assertEquals("Bonjour", tokens[0]);
        assertEquals("monde",   tokens[1]);
    }

    // ── Chatbot Responder ──────────────────────────────────────────────────

    static ChatbotResponder chatbot;

    @BeforeAll
    static void setUpChatbot() {
        chatbot = new ChatbotResponder();
        chatbot.load(); // AIML ou fallback règles
    }

    @Test
    @Order(20)
    @DisplayName("respond() ne doit jamais retourner null")
    void testRespondNotNull() {
        assertNotNull(chatbot.respond("bonjour"));
    }

    @Test
    @Order(21)
    @DisplayName("respond() sur entrée vide doit retourner un message utile")
    void testRespondEmpty() {
        String result = chatbot.respond("  ");
        assertFalse(result.isBlank(), "La réponse à une entrée vide ne doit pas être vide.");
    }

    @Test
    @Order(22)
    @DisplayName("respond('merci') doit contenir une réponse de politesse")
    void testRespondMerci() {
        String result = chatbot.respond("merci").toLowerCase();
        assertTrue(
            result.contains("plaisir") || result.contains("rien") || result.contains("welcome"),
            "La réponse à 'merci' devrait être polie. Obtenu : " + result
        );
    }

    @Test
    @Order(23)
    @DisplayName("respond() sur texte inconnu doit retourner un message de secours")
    void testRespondUnknown() {
        String result = chatbot.respond("azerty12345xyzblabla");
        assertNotNull(result);
        assertFalse(result.isBlank());
    }

    // ── Nettoyage ──────────────────────────────────────────────────────────

    @AfterAll
    static void tearDown() {
        if (nnManager != null) nnManager.shutdown();
    }
}

package boria;

import boria.core.BorIAEngine;
import boria.ui.ChatbotUI;
import javafx.application.Application;

/**
 * Point d'entrée principal de l'application BorIA.
 * Lance l'interface graphique JavaFX.
 */
public class Main {

    public static void main(String[] args) {
        System.out.println("=== BorIA - Intelligence Artificielle ===");
        System.out.println("Démarrage de l'application...");

        // Initialiser le moteur IA en arrière-plan
        BorIAEngine.getInstance().initialize();

        // Lancer l'interface graphique
        Application.launch(ChatbotUI.class, args);
    }
}

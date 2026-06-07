package boria.ui;

import boria.core.BorIAEngine;
import boria.utils.Logger;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.concurrent.Task;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.scene.text.Font;
import javafx.scene.text.FontWeight;
import javafx.stage.FileChooser;
import javafx.stage.Stage;

import java.io.File;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

/**
 * Interface graphique JavaFX de BorIA.
 *
 * Composants :
 *  - Fenêtre principale avec barre de titre
 *  - Zone de conversation (ScrollPane + VBox)
 *  - Champ de saisie + bouton Envoyer
 *  - Bouton d'analyse d'image
 *  - Panneau d'état (moteur IA, NLP, réseau de neurones)
 */
public class ChatbotUI extends Application {

    // ── Constantes de style ────────────────────────────────────────────────
    private static final String COLOR_BG         = "#1A1A2E";
    private static final String COLOR_PANEL      = "#16213E";
    private static final String COLOR_ACCENT     = "#0F3460";
    private static final String COLOR_HIGHLIGHT  = "#E94560";
    private static final String COLOR_TEXT       = "#EAEAEA";
    private static final String COLOR_MSG_USER   = "#0F3460";
    private static final String COLOR_MSG_BOT    = "#16213E";

    private static final DateTimeFormatter TIME_FMT =
        DateTimeFormatter.ofPattern("HH:mm");

    // ── Composants UI ──────────────────────────────────────────────────────
    private VBox      messageContainer;
    private ScrollPane scrollPane;
    private TextField  inputField;
    private Button     sendButton;
    private Label      statusLabel;

    @Override
    public void start(Stage primaryStage) {
        primaryStage.setTitle("BorIA — Intelligence Artificielle");
        primaryStage.setMinWidth(600);
        primaryStage.setMinHeight(500);

        BorderPane root = new BorderPane();
        root.setStyle("-fx-background-color: " + COLOR_BG + ";");

        root.setTop(buildHeader());
        root.setCenter(buildChatArea());
        root.setBottom(buildInputArea(primaryStage));
        root.setRight(buildStatusPanel());

        Scene scene = new Scene(root, 800, 600);
        primaryStage.setScene(scene);
        primaryStage.setOnCloseRequest(e -> {
            BorIAEngine.getInstance().shutdown();
            Platform.exit();
        });
        primaryStage.show();

        // Message de bienvenue
        appendBotMessage("Bonjour ! Je suis BorIA, votre assistant IA.\n" +
                         "Je suis prêt à discuter, analyser des images et faire des prédictions.\n" +
                         "Tapez 'aide' pour voir ce que je peux faire.");
    }

    // ── Construction des sections ──────────────────────────────────────────

    private HBox buildHeader() {
        Label title = new Label("🤖 BorIA");
        title.setFont(Font.font("Monospace", FontWeight.BOLD, 22));
        title.setStyle("-fx-text-fill: " + COLOR_HIGHLIGHT + ";");

        Label subtitle = new Label("Intelligence Artificielle Java");
        subtitle.setFont(Font.font("Monospace", 12));
        subtitle.setStyle("-fx-text-fill: #888888;");

        VBox titleBox = new VBox(2, title, subtitle);

        HBox header = new HBox(titleBox);
        header.setAlignment(Pos.CENTER_LEFT);
        header.setPadding(new Insets(16, 20, 16, 20));
        header.setStyle("-fx-background-color: " + COLOR_PANEL + ";" +
                        "-fx-border-color: " + COLOR_HIGHLIGHT + ";" +
                        "-fx-border-width: 0 0 2 0;");
        return header;
    }

    private ScrollPane buildChatArea() {
        messageContainer = new VBox(10);
        messageContainer.setPadding(new Insets(16));
        messageContainer.setFillWidth(true);

        scrollPane = new ScrollPane(messageContainer);
        scrollPane.setFitToWidth(true);
        scrollPane.setVbarPolicy(ScrollPane.ScrollBarPolicy.AS_NEEDED);
        scrollPane.setHbarPolicy(ScrollPane.ScrollBarPolicy.NEVER);
        scrollPane.setStyle("-fx-background: " + COLOR_BG + ";" +
                            "-fx-background-color: " + COLOR_BG + ";");

        // Auto-scroll vers le bas
        messageContainer.heightProperty().addListener(
            (obs, oldVal, newVal) -> scrollPane.setVvalue(1.0)
        );
        return scrollPane;
    }

    private VBox buildInputArea(Stage stage) {
        inputField = new TextField();
        inputField.setPromptText("Tapez votre message...");
        inputField.setStyle(
            "-fx-background-color: " + COLOR_PANEL + ";" +
            "-fx-text-fill: " + COLOR_TEXT + ";" +
            "-fx-border-color: " + COLOR_ACCENT + ";" +
            "-fx-border-radius: 4;" +
            "-fx-background-radius: 4;" +
            "-fx-font-size: 14px;" +
            "-fx-padding: 10;"
        );
        HBox.setHgrow(inputField, Priority.ALWAYS);

        sendButton = buildButton("Envoyer", COLOR_HIGHLIGHT);
        sendButton.setOnAction(e -> handleSend());
        inputField.setOnAction(e -> handleSend());

        Button imageButton = buildButton("📷 Image", COLOR_ACCENT);
        imageButton.setOnAction(e -> handleImageUpload(stage));

        Button xorButton = buildButton("⚡ XOR", COLOR_ACCENT);
        xorButton.setOnAction(e -> handleXORDemo());

        HBox inputRow = new HBox(10, inputField, imageButton, xorButton, sendButton);
        inputRow.setPadding(new Insets(12, 16, 16, 16));
        inputRow.setAlignment(Pos.CENTER);
        inputRow.setStyle("-fx-background-color: " + COLOR_PANEL + ";" +
                          "-fx-border-color: " + COLOR_HIGHLIGHT + ";" +
                          "-fx-border-width: 2 0 0 0;");
        return new VBox(inputRow);
    }

    private VBox buildStatusPanel() {
        Label title = new Label("ÉTAT DU SYSTÈME");
        title.setFont(Font.font("Monospace", FontWeight.BOLD, 11));
        title.setStyle("-fx-text-fill: " + COLOR_HIGHLIGHT + ";");

        statusLabel = new Label();
        statusLabel.setWrapText(true);
        statusLabel.setMaxWidth(160);
        statusLabel.setFont(Font.font("Monospace", 11));
        statusLabel.setStyle("-fx-text-fill: #AAAAAA;");
        refreshStatus();

        VBox panel = new VBox(10, title, new Separator(), statusLabel);
        panel.setPadding(new Insets(16, 12, 16, 12));
        panel.setPrefWidth(180);
        panel.setStyle("-fx-background-color: " + COLOR_PANEL + ";" +
                       "-fx-border-color: " + COLOR_ACCENT + ";" +
                       "-fx-border-width: 0 0 0 1;");
        return panel;
    }

    // ── Gestion des actions ────────────────────────────────────────────────

    private void handleSend() {
        String text = inputField.getText().trim();
        if (text.isEmpty()) return;

        appendUserMessage(text);
        inputField.clear();
        setInputEnabled(false);

        // Réponse asynchrone pour ne pas bloquer l'UI
        Task<String> task = new Task<>() {
            @Override protected String call() {
                return BorIAEngine.getInstance().respond(text);
            }
        };
        task.setOnSucceeded(e -> {
            appendBotMessage(task.getValue());
            setInputEnabled(true);
        });
        task.setOnFailed(e -> {
            appendBotMessage("[Erreur] " + task.getException().getMessage());
            setInputEnabled(true);
        });
        new Thread(task, "boria-respond").start();
    }

    private void handleImageUpload(Stage stage) {
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Choisir une image");
        chooser.getExtensionFilters().add(
            new FileChooser.ExtensionFilter("Images", "*.jpg", "*.jpeg", "*.png", "*.bmp")
        );
        File file = chooser.showOpenDialog(stage);
        if (file == null) return;

        appendUserMessage("[Image sélectionnée] " + file.getName());
        setInputEnabled(false);

        Task<String> task = new Task<>() {
            @Override protected String call() {
                return BorIAEngine.getInstance().analyzeImage(file.getAbsolutePath());
            }
        };
        task.setOnSucceeded(e -> { appendBotMessage(task.getValue()); setInputEnabled(true); });
        task.setOnFailed(e -> { appendBotMessage("[Erreur vision] " + task.getException().getMessage()); setInputEnabled(true); });
        new Thread(task, "boria-vision").start();
    }

    private void handleXORDemo() {
        appendBotMessage("Démonstration XOR avec le réseau de neurones :");
        double[][] tests = {{0,0},{0,1},{1,0},{1,1}};
        StringBuilder sb = new StringBuilder();
        for (double[] t : tests) {
            double result = BorIAEngine.getInstance().predictXOR(t[0], t[1]);
            sb.append(String.format("  %.0f ⊕ %.0f = %.4f (attendu: %.0f)\n",
                t[0], t[1], result, t[0] != t[1] ? 1.0 : 0.0));
        }
        appendBotMessage(sb.toString().trim());
    }

    // ── Construction des bulles de message ─────────────────────────────────

    private void appendUserMessage(String text) {
        Platform.runLater(() -> {
            Label bubble = buildBubble("Vous  " + now(), text, COLOR_MSG_USER, Pos.CENTER_RIGHT);
            messageContainer.getChildren().add(bubble);
        });
    }

    private void appendBotMessage(String text) {
        Platform.runLater(() -> {
            Label bubble = buildBubble("BorIA  " + now(), text, COLOR_MSG_BOT, Pos.CENTER_LEFT);
            messageContainer.getChildren().add(bubble);
        });
    }

    private Label buildBubble(String header, String body, String bgColor, Pos alignment) {
        Label label = new Label(header + "\n" + body);
        label.setWrapText(true);
        label.setMaxWidth(520);
        label.setFont(Font.font("Monospace", 13));
        label.setStyle(
            "-fx-background-color: " + bgColor + ";" +
            "-fx-text-fill: " + COLOR_TEXT + ";" +
            "-fx-padding: 10 14 10 14;" +
            "-fx-background-radius: 8;" +
            "-fx-border-radius: 8;"
        );

        HBox wrapper = new HBox(label);
        wrapper.setAlignment(alignment);
        wrapper.setMaxWidth(Double.MAX_VALUE);
        HBox.setHgrow(wrapper, Priority.ALWAYS);

        // Hack : label wrapper dans HBox n'est pas un Label — retour simplifié
        return label; // pour simplifier, on ajoute directement le label centré
    }

    // ── Utilitaires ────────────────────────────────────────────────────────

    private Button buildButton(String text, String color) {
        Button btn = new Button(text);
        btn.setStyle(
            "-fx-background-color: " + color + ";" +
            "-fx-text-fill: " + COLOR_TEXT + ";" +
            "-fx-font-family: Monospace;" +
            "-fx-font-size: 13px;" +
            "-fx-padding: 9 16 9 16;" +
            "-fx-background-radius: 4;" +
            "-fx-cursor: hand;"
        );
        return btn;
    }

    private void refreshStatus() {
        BorIAEngine engine = BorIAEngine.getInstance();
        String status =
            "Moteur : " + (engine.isInitialized() ? "✅ OK" : "❌ OFF") + "\n\n" +
            "Réseau\nneuronal : " + (engine.getNNManager() != null && engine.getNNManager().isTrained() ? "✅ Entraîné" : "⏳ ...") + "\n\n" +
            "NLP : " + (engine.getNLPProcessor() != null && engine.getNLPProcessor().isNlpAvailable() ? "✅ OpenNLP" : "⚠️ Basique") + "\n\n" +
            "Vision : OpenCV";
        if (statusLabel != null) statusLabel.setText(status);
    }

    private void setInputEnabled(boolean enabled) {
        Platform.runLater(() -> {
            inputField.setDisable(!enabled);
            sendButton.setDisable(!enabled);
            refreshStatus();
        });
    }

    private String now() {
        return LocalTime.now().format(TIME_FMT);
    }
}

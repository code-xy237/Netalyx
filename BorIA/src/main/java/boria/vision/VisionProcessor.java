package boria.vision;

import boria.utils.Logger;
import org.opencv.core.Core;
import org.opencv.core.Mat;
import org.opencv.highgui.HighGui;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;

import java.io.File;

/**
 * Module de vision par ordinateur (OpenCV).
 *
 * Fonctionnalités actuelles :
 *  - Chargement et validation d'image
 *  - Conversion en niveaux de gris
 *  - Affichage via HighGui
 *  - Retour d'informations sur l'image (dimensions, canaux)
 *
 * Extension possible : détection de visages (Haar Cascade),
 *                      détection d'objets (YOLO), OCR (Tesseract).
 *
 * IMPORTANT : OpenCV nécessite le chargement de la bibliothèque native.
 *             Sur Windows : opencv_javaXXX.dll
 *             Sur Linux   : libopencv_javaXXX.so
 *             Sur macOS   : libopencv_javaXXX.dylib
 */
public class VisionProcessor {

    private boolean opencvAvailable = false;

    // ── Initialisation ─────────────────────────────────────────────────────

    public VisionProcessor() {
        try {
            System.loadLibrary(Core.NATIVE_LIBRARY_NAME);
            opencvAvailable = true;
            Logger.info("OpenCV chargé : " + Core.VERSION);
        } catch (UnsatisfiedLinkError e) {
            Logger.warn("Bibliothèque native OpenCV introuvable. Module vision désactivé.");
            opencvAvailable = false;
        }
    }

    // ── Traitement principal ────────────────────────────────────────────────

    /**
     * Charge et analyse une image.
     *
     * @param imagePath chemin absolu ou relatif de l'image
     * @return description textuelle de l'image analysée
     */
    public String process(String imagePath) {
        if (!opencvAvailable) {
            return "[Vision] OpenCV non disponible. Installez les bibliothèques natives.";
        }

        // Validation du fichier
        File file = new File(imagePath);
        if (!file.exists() || !file.isFile()) {
            Logger.error("Image introuvable : " + imagePath);
            return "[Vision] Fichier introuvable : " + imagePath;
        }

        try {
            return analyzeImage(imagePath);
        } catch (Exception e) {
            Logger.error("Erreur lors de l'analyse de l'image : " + e.getMessage());
            return "[Vision] Erreur d'analyse : " + e.getMessage();
        }
    }

    // ── Analyse d'image ─────────────────────────────────────────────────────

    private String analyzeImage(String imagePath) {
        // Chargement de l'image
        Mat original = Imgcodecs.imread(imagePath);
        if (original.empty()) {
            return "[Vision] Impossible de lire l'image (format non supporté ou fichier corrompu).";
        }

        // Informations de base
        int width    = original.cols();
        int height   = original.rows();
        int channels = original.channels();
        String colorSpace = channels == 1 ? "Niveaux de gris" :
                            channels == 3 ? "BGR (couleur)"   : "BGRA (avec transparence)";

        // Conversion en niveaux de gris
        Mat grayImage = new Mat();
        Imgproc.cvtColor(original, grayImage, Imgproc.COLOR_BGR2GRAY);

        // Affichage (optionnel — commenter si pas d'interface graphique)
        HighGui.imshow("BorIA Vision - " + new File(imagePath).getName(), grayImage);
        HighGui.waitKey(1000); // affiche 1 seconde puis continue
        HighGui.destroyAllWindows();

        // Libération mémoire
        original.release();
        grayImage.release();

        return String.format(
            "[Vision] Image analysée avec succès.\n" +
            "  Fichier     : %s\n" +
            "  Dimensions  : %d × %d pixels\n" +
            "  Canaux      : %d (%s)\n" +
            "  Traitement  : Conversion en niveaux de gris appliquée.",
            new File(imagePath).getName(), width, height, channels, colorSpace
        );
    }

    // ── Getters ────────────────────────────────────────────────────────────
    public boolean isOpencvAvailable() { return opencvAvailable; }
}

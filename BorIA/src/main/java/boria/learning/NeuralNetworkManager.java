package boria.learning;

import boria.utils.Logger;
import org.encog.Encog;
import org.encog.engine.network.activation.ActivationSigmoid;
import org.encog.ml.data.MLData;
import org.encog.ml.data.MLDataPair;
import org.encog.ml.data.basic.BasicMLData;
import org.encog.ml.data.basic.BasicMLDataSet;
import org.encog.neural.networks.BasicNetwork;
import org.encog.neural.networks.layers.BasicLayer;
import org.encog.neural.networks.training.propagation.resilient.ResilientPropagation;

/**
 * Gestionnaire du réseau de neurones (Encog).
 *
 * Architecture : 2 → 3 → 1
 *   - Couche d'entrée  : 2 neurones (sans activation)
 *   - Couche cachée    : 3 neurones (Sigmoïde)
 *   - Couche de sortie : 1 neurone  (Sigmoïde)
 *
 * Problème d'entraînement par défaut : XOR
 *   Entrée  → Sortie attendue
 *   [0, 0]  → 0
 *   [0, 1]  → 1
 *   [1, 0]  → 1
 *   [1, 1]  → 0
 */
public class NeuralNetworkManager {

    // ── Données XOR ────────────────────────────────────────────────────────
    private static final double[][] XOR_INPUT  = {{0, 0}, {0, 1}, {1, 0}, {1, 1}};
    private static final double[][] XOR_OUTPUT = {{0},    {1},    {1},    {0}};

    private static final int    MAX_ITERATIONS  = 10_000;
    private static final double TARGET_ERROR    = 0.001;

    // ── État interne ───────────────────────────────────────────────────────
    private BasicNetwork network;
    private boolean      trained = false;

    // ── Construction du réseau ─────────────────────────────────────────────

    /**
     * Construit, entraîne et valide le réseau sur le problème XOR.
     */
    public void buildAndTrainXOR() {
        Logger.info("Construction du réseau de neurones (2-3-1)...");

        network = new BasicNetwork();
        network.addLayer(new BasicLayer(null,                  true, 2));  // entrée
        network.addLayer(new BasicLayer(new ActivationSigmoid(), true, 3));  // cachée
        network.addLayer(new BasicLayer(new ActivationSigmoid(), false, 1)); // sortie
        network.getStructure().finalizeStructure();
        network.reset(); // initialisation aléatoire des poids

        // Jeu d'entraînement
        BasicMLDataSet trainingSet = new BasicMLDataSet(XOR_INPUT, XOR_OUTPUT);

        // Algorithme : Resilient Propagation (RPROP) — plus stable que backprop simple
        ResilientPropagation trainer = new ResilientPropagation(network, trainingSet);

        Logger.info("Entraînement en cours...");
        int iteration = 0;
        do {
            trainer.iteration();
            iteration++;
        } while (trainer.getError() > TARGET_ERROR && iteration < MAX_ITERATIONS);

        trainer.finishTraining();
        trained = true;

        Logger.info(String.format(
            "Entraînement terminé en %d itérations. Erreur finale : %.6f",
            iteration, trainer.getError()
        ));

        validateXOR(trainingSet);
    }

    // ── Prédiction ─────────────────────────────────────────────────────────

    /**
     * Prédit la sortie du réseau pour deux entrées données.
     *
     * @param a première entrée (0.0 ou 1.0)
     * @param b deuxième entrée (0.0 ou 1.0)
     * @return valeur de sortie entre 0 et 1
     */
    public double predict(double a, double b) {
        if (!trained) throw new IllegalStateException("Réseau non entraîné.");

        MLData input  = new BasicMLData(new double[]{a, b});
        MLData output = network.compute(input);
        return output.getData(0);
    }

    // ── Validation ─────────────────────────────────────────────────────────

    private void validateXOR(BasicMLDataSet trainingSet) {
        Logger.info("--- Validation XOR ---");
        for (MLDataPair pair : trainingSet) {
            MLData output = network.compute(pair.getInput());
            Logger.info(String.format(
                "  [%.0f, %.0f] → attendu: %.0f | prédit: %.4f",
                pair.getInput().getData(0),
                pair.getInput().getData(1),
                pair.getIdeal().getData(0),
                output.getData(0)
            ));
        }
        Logger.info("--- Fin validation ---");
    }

    // ── Arrêt propre ───────────────────────────────────────────────────────
    public void shutdown() {
        Encog.getInstance().shutdown();
        Logger.info("Encog arrêté proprement.");
    }

    // ── Getters ────────────────────────────────────────────────────────────
    public boolean isTrained()       { return trained; }
    public BasicNetwork getNetwork() { return network; }
}

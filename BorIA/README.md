# BorIA — Intelligence Artificielle Java

Application IA modulaire développée en Java, combinant NLP, réseaux de neurones, chatbot AIML et vision par ordinateur.

---

## Architecture du projet

```
BorIA/
├── src/main/java/boria/
│   ├── Main.java                     ← Point d'entrée
│   ├── core/
│   │   └── BorIAEngine.java          ← Moteur central (Singleton)
│   ├── nlp/
│   │   ├── NLPProcessor.java         ← Tokenisation, détection de phrases
│   │   └── ChatbotResponder.java     ← AIML + règles de secours
│   ├── learning/
│   │   └── NeuralNetworkManager.java ← Réseau de neurones Encog (2-3-1)
│   ├── vision/
│   │   └── VisionProcessor.java      ← Traitement d'images OpenCV
│   ├── ui/
│   │   └── ChatbotUI.java            ← Interface graphique JavaFX
│   └── utils/
│       ├── Logger.java               ← Journalisation
│       └── Config.java               ← Chargeur de configuration
├── resources/
│   ├── boria.properties              ← Configuration
│   ├── aiml/
│   │   └── boria.aiml                ← Base de connaissances AIML 2.0
│   └── models/
│       └── en-sent.bin               ← (à télécharger) Modèle OpenNLP
└── pom.xml                           ← Build Maven
```

---

## Prérequis

| Outil       | Version minimum |
|-------------|----------------|
| Java JDK    | 17             |
| Maven       | 3.8+           |
| JavaFX SDK  | 21             |

---

## Installation

### 1. Cloner le projet
```bash
git clone https://github.com/votre-repo/BorIA.git
cd BorIA
```

### 2. Modèle OpenNLP (optionnel)
Téléchargez `en-sent.bin` depuis https://opennlp.apache.org/models.html
et placez-le dans `resources/models/`.

Sans ce fichier, BorIA bascule automatiquement sur le traitement NLP basique.

### 3. Program AB / AIML (optionnel)
Téléchargez `programab.jar` et placez-le dans `libs/`.
Sans ce JAR, BorIA utilise le moteur de règles Java intégré.

### 4. OpenCV (optionnel)
- Téléchargez OpenCV depuis https://opencv.org/releases/
- Ajoutez `opencv-490.jar` au classpath
- Ajoutez le dossier `native/` (contenant `.dll`/`.so`/`.dylib`) à `java.library.path`

Sans OpenCV, le module vision est désactivé avec un message d'avertissement.

---

## Compilation et lancement

```bash
# Compiler
mvn clean compile

# Lancer avec JavaFX
mvn javafx:run

# Créer un JAR exécutable
mvn clean package
java -jar target/boria-ai-1.0.0.jar

# Lancer les tests
mvn test
```

---

## Modules

### `BorIAEngine` — Moteur central
Singleton qui orchestre tous les modules. Point d'entrée unique pour :
- `respond(String)` → réponse textuelle
- `predictXOR(double, double)` → prédiction du réseau
- `analyzeImage(String)` → analyse d'image

### `NeuralNetworkManager` — Réseau de neurones
- Bibliothèque : **Encog 3.4**
- Architecture : 2 entrées → 3 neurones cachés (sigmoïde) → 1 sortie
- Algorithme d'entraînement : **Resilient Propagation (RPROP)**
- Problème démontré : **XOR**

### `NLPProcessor` — Traitement du langage
- Bibliothèque : **Apache OpenNLP 2.3**
- Fonctions : tokenisation, détection de phrases, normalisation
- Dégradation gracieuse si le modèle est absent

### `ChatbotResponder` — Chatbot
- Moteur primaire : **AIML 2.0** via Program AB
- Moteur de secours : règles Java (HashMap mot-clé → réponse)
- Base de connaissances : `resources/aiml/boria.aiml`

### `VisionProcessor` — Vision
- Bibliothèque : **OpenCV 4.9**
- Fonctions : chargement d'image, conversion niveaux de gris, analyse
- Dégradation gracieuse si les bibliothèques natives sont absentes

### `ChatbotUI` — Interface graphique
- Framework : **JavaFX 21**
- Design sombre avec palette personnalisée
- Traitement asynchrone (threads dédiés) pour ne pas bloquer l'UI
- Fonctionnalités : chat, analyse d'image (FileChooser), démo XOR

---

## Étendre BorIA

### Ajouter des réponses AIML
Éditez `resources/aiml/boria.aiml` :
```xml
<category>
  <pattern>VOTRE PATTERN</pattern>
  <template>Votre réponse ici.</template>
</category>
```

### Ajouter des règles de secours
Dans `ChatbotResponder.java`, ajoutez une entrée à la map `RULES` :
```java
RULES.put("nouveau mot-clé", "Réponse associée.");
```

### Changer la topologie du réseau
Dans `NeuralNetworkManager.java`, modifiez les couches :
```java
network.addLayer(new BasicLayer(new ActivationSigmoid(), true, 5)); // 5 neurones cachés
```

---

## Licence

Projet développé à des fins éducatives.

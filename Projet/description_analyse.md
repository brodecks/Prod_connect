# Documentation de `analyse.py`

> **Périmètre.** Cette documentation décrit le contenu actuel de `Projet/analyse.py` et les colonnes du fichier préparé `Projet/donnees/capteurs_prepares.csv`. Le PDF `SUJET_PRODCONNECT.pdf` n’a pas pu être exploité ici ; les raisons propres au sujet qui auraient conduit aux seuils ne peuvent donc pas être confirmées. Les explications ci-dessous distinguent le fonctionnement du code de toute justification métier non présente dans ces fichiers.

## Rôle du programme

`analyse.py` fournit au moteur du projet quatre fonctions de calcul ainsi qu’un seuil d’alerte. Le commentaire du script indique que le moteur évalue les données de septembre et d’octobre, à partir de capteurs déjà préparés, puis produit des fichiers CSV utilisés par Streamlit. Le prétraitement n’est donc pas effectué dans les fonctions décrites ici.

Le CSV présente des mesures datées par machine : température (°C), vibration (mm/s), pression (bar), courant (A) et taux de rebut (%). Il contient également des variables préparées, notamment des moyennes mobiles sur trois observations (`*_moy3`), un delta de température et un segment. Ces colonnes supplémentaires ne sont pas directement utilisées par les fonctions de `analyse.py`.

## Fonctions

### `calculer_risque(temperature, vibration, pression, courant, rebut)`

Calcule un score heuristique de risque compris entre **0 et 1**. Le calcul commence à `0.0`, puis ajoute une contribution pour chaque condition remplie :

| Condition | Contribution au score |
|---|---:|
| Température `>= 78.0 °C` | `0.35` |
| Vibration `>= 5.0 mm/s` | `0.35` |
| Taux de rebut `>= 4.2 %` | `0.30` |

Les conditions sont indépendantes et cumulatives. Le résultat est borné entre 0 et 1 avec `max` et `min`, puis converti en `float`. Comme les trois contributions totalisent exactement 1, le score maximal prévu est 1.0.

**Remarque sur les paramètres :** `pression` et `courant` font partie de la signature demandée par le moteur, mais ne sont pas consultés dans le corps actuel de la fonction. Ils n’influencent donc pas le score. De même, la fonction utilise les valeurs instantanées reçues et non les moyennes ou deltas disponibles dans le CSV.

### `cout_arret(duree_heures, cout_horaire)`

Calcule le coût d’un arrêt en euros en multipliant sa durée par le coût horaire :

```text
coût d’arrêt = durée (heures) × coût horaire (€/heure)
```

### `gain_panne_anticipee(duree_heures, cout_horaire, cout_preventif)`

Estime le gain associé à une panne entièrement évitée grâce à une intervention préventive. La fonction calcule d’abord le coût d’arrêt avec `cout_arret`, puis en retranche le coût préventif :

```text
gain = coût d’arrêt évité − coût préventif
```

Un résultat positif correspond à une économie nette selon cette hypothèse ; un résultat négatif signifie que le coût préventif dépasse le coût d’arrêt évité.

### `gain_fausse_alerte(cout_inspection)`

Renvoie le gain d’une inspection déclenchée par une alerte injustifiée, sous forme de coût négatif :

```text
gain = − coût d’inspection
```

Le signe négatif permet de représenter cette inspection comme une perte dans un calcul de gains.

## Constante `SEUIL_ALERTE`

`SEUIL_ALERTE` vaut actuellement **0.5**. Elle est transmise au moteur avec les fonctions de risque et de coûts. Elle sert de seuil de décision pour les alertes ; la convention exacte de comparaison (par exemple `>=` ou `>`) dépend de l’implémentation du moteur, non incluse dans cette description.

## Lecture de l’algorithme de risque et des valeurs choisies

Les trois poids forment une pondération simple et lisible : température et vibration pèsent chacune 35 % du score maximal, et le taux de rebut 30 %. En termes de score, chaque signal seul donne respectivement **0.35**, **0.35** ou **0.30**. Plusieurs signaux peuvent se cumuler :

| Signaux détectés | Score |
|---|---:|
| Aucun | `0.00` |
| Rebut seul | `0.30` |
| Température seule ou vibration seule | `0.35` |
| Rebut + température ou rebut + vibration | `0.65` |
| Température + vibration | `0.70` |
| Les trois signaux | `1.00` |

Avec un seuil d’alerte de 0.5, chacune des conditions isolées reste sous le seuil, tandis que toute combinaison de deux conditions dépasse ce niveau (si le moteur compare le score au seuil avec `>=`). Il s’agit de la conséquence arithmétique des valeurs codées, pas d’une validation statistique de leur performance.

Les limites retenues sont `78.0 °C`, `5.0 mm/s` et `4.2 %` de rebut. Le CSV préparé montre que les valeurs de ces mesures varient autour de ces zones d’alerte et peuvent les dépasser. Toutefois, le code ne précise pas l’origine de ces seuils : ils doivent être considérés comme des paramètres heuristiques à valider avec le sujet, les seuils opérationnels réels ou des résultats historiques.

## Lancement

Lorsqu’il est exécuté directement, le fichier importe `lancer` depuis `outils.moteur` et lui transmet les quatre fonctions ainsi que `SEUIL_ALERTE`. La logique de lecture des données et de génération des sorties est déléguée à cet outil.

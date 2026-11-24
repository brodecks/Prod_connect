"""BONUS ML FACULTATIF (20-30 min) - ProdConnect.

Une foret aleatoire (Random Forest) apprend a predire une panne corrective dans les 1 a 3
jours qui suivent une mesure. Contrairement a la fonction calculer_risque d'analyse.py, il apprend
ses regles a partir des exemples historiques.

Lancer depuis le dossier ProdConnect :
    python bonus_ml.py

A essayer : changer PROFONDEUR_MAX (5 puis 3), ajuster SEUIL, ou supprimer un capteur.
Le modele affiche les risques de chaque machine pour les 7 derniers jours dans le terminal. Vous pouvez programmer un export CSV si vous souhaitez
les exploiter ensuite dans Streamlit.
Ce bonus n'est pas requis pour le projet. Aucun fichier obligatoire n'est modifie.
"""
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, confusion_matrix
from outils.moteur import convertir_date_excel

RACINE = Path(__file__).resolve().parent
DONNEES = RACINE / "donnees/capteurs_prepares.csv"
CLASSEUR = RACINE / "donnees/ProdConnect_2026.xlsx"
PROFONDEUR_MAX = 5
NOMBRE_ARBRES = 100
SEUIL = 0.50  # Seuil initial d'exploration, a verifier avec les metriques
CAPTEURS = ["Temperature_C", "Vibration_mm_s", "Pression_bar",
            "Courant_A", "Taux_rebut_pct"]

if not DONNEES.exists():
    raise SystemExit("Donnees manquantes : donnees/capteurs_prepares.csv")

mesures = pd.read_csv(DONNEES, sep=";")
mesures["Date"] = pd.to_datetime(mesures["Date"], format="%Y-%m-%d", errors="raise")
interventions = pd.read_excel(CLASSEUR, sheet_name="Interventions")
# Les dates Excel sont des dates classiques sauf une valeur numerique (M99).
# On exclut M99 et les autres machines non referencees de cette evaluation.
interventions = interventions[interventions["ID_machine"].isin(mesures["ID_machine"].unique())].copy()
interventions["Date"] = pd.to_datetime(interventions["Date"].map(convertir_date_excel), errors="raise")
pannes = interventions[interventions["Type_panne"] != "Preventive"]

# Etiquette : 1 si panne corrective de la meme machine entre J+1 et J+3.
# Les informations du FUTUR servent seulement a fabriquer la reponse attendue
# pour l'apprentissage et l'evaluation, jamais comme variables d'entree.
# Pour M12, une panne apres remplacement ne doit pas etiqueter l'ancienne machine.
mesures["panne_j1_j3"] = 0
for id_machine, groupe in mesures.groupby("ID_machine"):
    dates_pannes = pannes.loc[pannes["ID_machine"] == id_machine, "Date"]
    for date_panne in dates_pannes:
        voisins = (mesures["ID_machine"] == id_machine) & (
            mesures["Date"] >= date_panne - pd.Timedelta(days=3)) & (
            mesures["Date"] < date_panne)
        if id_machine == "M12":
            voisins &= (mesures["Date"] >= pd.Timestamp("2026-03-10")) == (
                date_panne >= pd.Timestamp("2026-03-10"))
        mesures.loc[voisins, "panne_j1_j3"] = 1

# Ne retenir que les jours avec trois jours futurs observables.
# Entrainer avant septembre, regarder septembre pour experimenter,
# puis tester octobre sans ajuster le modele apres lecture des resultats.
entrainement = mesures[mesures["Date"] <= "2026-08-28"].copy()
validation = mesures[mesures["Date"].between("2026-09-01", "2026-09-27")].copy()
test = mesures[mesures["Date"].between("2026-10-01", "2026-10-28")].copy()

if not CAPTEURS or not set(CAPTEURS).issubset(mesures.columns):
    raise ValueError("Verifier les noms des capteurs dans CAPTEURS.")
if any(part[CAPTEURS].isna().any().any() for part in (entrainement, validation, test)):
    raise ValueError("Les capteurs contiennent des valeurs manquantes.")

modele = RandomForestClassifier(n_estimators=NOMBRE_ARBRES,
                                max_depth=PROFONDEUR_MAX,
                                min_samples_leaf=5,
                                class_weight="balanced", random_state=42)
modele.fit(entrainement[CAPTEURS], entrainement["panne_j1_j3"])

print("BONUS : Random Forest, panne dans les 1 a 3 jours")
print("Capteurs :", ", ".join(CAPTEURS))
print("Arbres :", NOMBRE_ARBRES, "| Profondeur :", PROFONDEUR_MAX, "| Seuil :", SEUIL)
print("Attention : seuil initial de demonstration, a discuter selon precision et rappel")
print("Entrainement :", len(entrainement), "jours-machine ;",
      int(entrainement["panne_j1_j3"].sum()), "jours positifs")

for nom, donnees in (("Validation (septembre)", validation),
                     ("Test (octobre)", test)):
    scores = modele.predict_proba(donnees[CAPTEURS])[:, 1]
    pred = (scores >= SEUIL).astype(int)
    vrai = donnees["panne_j1_j3"]
    tn, fp, fn, tp = confusion_matrix(vrai, pred, labels=[0, 1]).ravel()
    print("\n", nom, ":", len(donnees), "jours-machine", sep="")
    print("  VP :", tp, "| FP :", fp, "| FN :", fn, "| VN :", tn)
    print("  Precision :", f"{precision_score(vrai, pred, zero_division=0):.2f}",
          "| Rappel :", f"{recall_score(vrai, pred, zero_division=0):.2f}")

print("\nImportant : ces chiffres concernent des JOURS-MACHINE, pas des")
print("evenements de panne dedoublonnes comme dans analyse.py.")
print("Ils ne sont donc pas directement comparables aux bilans economiques.")
# Les sept derniers jours du jeu de donnees ne servent pas a evaluer le modele :
# on produit des PREDICTIONS, y compris lorsque les pannes futures sont inconnues.
# A chaque date, le modele utilise uniquement les mesures disponibles ce jour-la.
derniere_date = mesures["Date"].max()
debut_semaine = derniere_date - pd.Timedelta(days=6)
semaine = mesures.loc[
    mesures["Date"].between(debut_semaine, derniere_date),
    ["ID_machine", "Date"] + CAPTEURS
].copy()
semaine["score_ml"] = modele.predict_proba(semaine[CAPTEURS])[:, 1]
semaine["alerte_ml"] = (semaine["score_ml"] >= SEUIL).astype(int)
semaine = semaine.sort_values(["ID_machine", "Date"])

print("\n=== RISQUE ML PAR MACHINE : 7 DERNIERS JOURS ===")
print(f"Periode : {debut_semaine:%d/%m/%Y} au {derniere_date:%d/%m/%Y}")
print("Score de risque de panne corrective dans les 1 a 3 jours suivants.")
print("Ce score n'est pas une probabilite calibree.")
jours = sorted(semaine["Date"].unique())
print("Machine  " + "  ".join(pd.Timestamp(j).strftime("%d/%m") for j in jours) + "  Alerte le dernier jour")
for id_machine, groupe in semaine.groupby("ID_machine", sort=True):
    jour_scores = groupe.set_index("Date")["score_ml"]
    scores = [f"{jour_scores.get(pd.Timestamp(j), float('nan')):.2f}" for j in jours]
    dernier = groupe.iloc[-1]
    alerte = "OUI" if dernier["alerte_ml"] else "non"
    print(f"{id_machine:<8} " + "  ".join(scores) + f"  {alerte}")
print("Alertes le dernier jour :", int(semaine.loc[semaine["Date"] == derniere_date, "alerte_ml"].sum()), "sur", len(semaine.loc[semaine["Date"] == derniere_date]))
print("Attention : un seuil bas peut provoquer beaucoup de fausses alertes ;")
print("il doit etre evalue avec la precision et le rappel sur les periodes passees.")
print("Attention : les pannes apres la fin du jeu de donnees sont inconnues ;")
print("on ne peut pas mesurer la justesse des predictions des derniers jours.")

print("A essayer : modifier SEUIL, PROFONDEUR_MAX ou CAPTEURS, puis relancer.")
print("Pour aller plus loin : programmer un export CSV des predictions.")

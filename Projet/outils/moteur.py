"""OUTIL FOURNI. Pas besoin de modifier pour le minimum.
Pour aller plus loin, vous pouvez explorer et adapter ce fichier en gardant
une copie fonctionnelle.

Role : lire les capteurs prets, appeler les fonctions de analyse.py,
identifier les alertes et pannes, totaliser et exporter les resultats.
M07 reste un cout estime pour la simulation ; M99 reste dans le registre
financier historique mais ne figure pas dans la comparaison predictive.
"""
from pathlib import Path
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
COLONNES = ["ID_machine", "Date", "resultat", "ID_intervention",
            "Duree_arret_h", "Cout_horaire_utilise", "Cout_preventif",
            "Cout_inspection", "Statut_cout"]


def evaluer(donnees, chemin_excel):
    machines = pd.read_excel(chemin_excel, sheet_name="Machines").set_index("ID_machine")
    interventions = pd.read_excel(chemin_excel, sheet_name="Interventions")
    interventions = interventions[interventions["ID_machine"].isin(machines.index)].copy()
    interventions["Date"] = pd.to_datetime(interventions["Date"].map(convertir_date_excel), errors="raise")
    pannes = interventions[interventions["Type_panne"] != "Preventive"].copy()
    pannes = pannes.sort_values(["ID_machine", "Date"])

    # Estimation explicite M07 pour rendre possible la simulation economique.
    mediane_type = machines.groupby("Type")["Cout_horaire_arret"].median()
    mediane_parc = machines["Cout_horaire_arret"].median()
    machines["Statut_cout"] = "Connu"
    for identifiant in machines.index[machines["Cout_horaire_arret"].isna()]:
        typ = machines.loc[identifiant, "Type"]
        valeur = mediane_type.get(typ, mediane_parc)
        if pd.isna(valeur):
            valeur = mediane_parc
        machines.loc[identifiant, "Cout_horaire_arret"] = valeur
        machines.loc[identifiant, "Statut_cout"] = "Estime"

    # Les intervalles fournis incluent les 3 jours futurs observables.
    debut = donnees["Date"].min() + pd.Timedelta(days=1)
    fin = donnees["Date"].max() + pd.Timedelta(days=3)
    periode_pannes = pannes[pannes["Date"].between(debut, fin)].copy()
    utilisees = set()
    derniere_alerte = {}
    lignes = []
    vraies = fausses = 0

    for _, ligne in donnees.sort_values(["ID_machine", "Date"]).iterrows():
        if int(ligne["alerte"]) != 1:
            continue
        machine, date = ligne["ID_machine"], ligne["Date"]
        if machine not in machines.index:
            continue
        if machine in derniere_alerte and (date - derniere_alerte[machine]).days <= 3:
            continue
        derniere_alerte[machine] = date
        candidates = periode_pannes[
            (periode_pannes["ID_machine"] == machine) &
            (periode_pannes["Date"] > date) &
            (periode_pannes["Date"] <= date + pd.Timedelta(days=3)) &
            (~periode_pannes["ID_intervention"].isin(utilisees))
        ]
        info = machines.loc[machine]
        if len(candidates):
            panne = candidates.iloc[0]
            utilisees.add(panne["ID_intervention"])
            vraies += 1
            lignes.append({
                "ID_machine": machine, "Date": date, "resultat": "panne_anticipee",
                "ID_intervention": panne["ID_intervention"],
                "Duree_arret_h": panne["Duree_arret_h"],
                "Cout_horaire_utilise": info["Cout_horaire_arret"],
                "Cout_preventif": info["Cout_preventif"],
                "Cout_inspection": info["Cout_inspection"],
                "Statut_cout": info["Statut_cout"]})
        else:
            fausses += 1
            lignes.append({
                "ID_machine": machine, "Date": date, "resultat": "fausse_alerte",
                "ID_intervention": "", "Duree_arret_h": 0,
                "Cout_horaire_utilise": info["Cout_horaire_arret"],
                "Cout_preventif": info["Cout_preventif"],
                "Cout_inspection": info["Cout_inspection"],
                "Statut_cout": info["Statut_cout"]})

    # Lister aussi les pannes manquees, utiles pour analyser les limites.
    for _, panne in periode_pannes.iterrows():
        if panne["ID_intervention"] in utilisees:
            continue
        info = machines.loc[panne["ID_machine"]]
        lignes.append({
            "ID_machine": panne["ID_machine"], "Date": panne["Date"],
            "resultat": "panne_manquee", "ID_intervention": panne["ID_intervention"],
            "Duree_arret_h": panne["Duree_arret_h"],
            "Cout_horaire_utilise": info["Cout_horaire_arret"],
            "Cout_preventif": info["Cout_preventif"],
            "Cout_inspection": info["Cout_inspection"],
            "Statut_cout": info["Statut_cout"]})

    bilan = {"alertes": vraies + fausses, "pannes_anticipees": vraies,
             "fausses_alertes": fausses,
             "pannes_manquees": len(periode_pannes) - len(utilisees)}
    return bilan, pd.DataFrame(lignes, columns=COLONNES)


def convertir_date_excel(valeur):
    if pd.isna(valeur):
        return pd.NaT
    if isinstance(valeur, (int, float)) and not isinstance(valeur, bool):
        return pd.to_datetime(valeur, unit="D", origin="1899-12-30")
    return pd.to_datetime(valeur, errors="coerce")


def bilan_historique(excel, sorties):
    """Conserver toutes les interventions, M99 comprise, et signaler les couts estimes."""
    machines = pd.read_excel(excel, sheet_name="Machines")
    interventions = pd.read_excel(excel, sheet_name="Interventions")
    interventions["Date"] = interventions["Date"].map(convertir_date_excel)
    if interventions["Date"].isna().any():
        raise ValueError("Date d'intervention invalide")
    resultat = interventions.merge(machines[["ID_machine", "Type", "Cout_horaire_arret"]],
                                   on="ID_machine", how="left")
    mediane_parc = machines["Cout_horaire_arret"].median()
    mediane_type = machines.groupby("Type")["Cout_horaire_arret"].median()
    resultat["Statut_cout"] = "Connu"
    resultat["Cout_horaire_utilise"] = resultat["Cout_horaire_arret"]
    for i, row in resultat.iterrows():
        if pd.isna(row["Cout_horaire_utilise"]):
            val = mediane_type.get(row["Type"], mediane_parc) if pd.notna(row["Type"]) else mediane_parc
            if pd.isna(val): val = mediane_parc
            resultat.loc[i, "Cout_horaire_utilise"] = val
            resultat.loc[i, "Statut_cout"] = "Estime"
    resultat["Machine_referencee"] = resultat["Type"].notna()
    cols = ["ID_intervention", "ID_machine", "Date", "Type_panne",
            "Duree_arret_h", "Machine_referencee", "Statut_cout", "Cout_horaire_utilise"]
    resultat[cols].to_csv(sorties / "bilan_financier.csv", sep=";", index=False)
    return resultat


def appliquer_calculs(evenements, cout_arret, gain_panne_anticipee, gain_fausse_alerte):
    copie = evenements.copy()
    gains, couts = [], []
    for ligne in copie.itertuples(index=False):
        cout = float(cout_arret(ligne.Duree_arret_h, ligne.Cout_horaire_utilise)) \
            if ligne.resultat in ("panne_anticipee", "panne_manquee") else 0.0
        if ligne.resultat == "panne_anticipee":
            gain = float(gain_panne_anticipee(ligne.Duree_arret_h,
                                            ligne.Cout_horaire_utilise, ligne.Cout_preventif))
        elif ligne.resultat == "fausse_alerte":
            gain = float(gain_fausse_alerte(ligne.Cout_inspection))
        elif ligne.resultat == "panne_manquee":
            gain = 0.0
        else:
            raise ValueError(f"Resultat inconnu : {ligne.resultat}")
        if not pd.notna(gain) or not pd.notna(cout):
            raise ValueError("Fonctions economiques : nombres invalides")
        gains.append(round(gain, 2))
        couts.append(round(cout, 2))
    copie["Cout_panne_reference_eur"] = couts
    copie["Gain_eur"] = gains
    return copie, round(sum(gains), 2)


def lancer(calculer_risque, cout_arret, gain_panne_anticipee, gain_fausse_alerte, seuil):
    if not 0 <= seuil <= 1:
        raise ValueError("SEUIL_ALERTE doit etre entre 0 et 1")
    sorties = RACINE / "sorties"
    sorties.mkdir(exist_ok=True)
    excel = RACINE / "donnees/ProdConnect_2026.xlsx"
    donnees = RACINE / "donnees/capteurs_prepares.csv"
    if not donnees.exists():
        raise FileNotFoundError("Fichier manquant : donnees/capteurs_prepares.csv")
    df = pd.read_csv(donnees, sep=";")
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="raise")
    colonnes = ["Temperature_C", "Vibration_mm_s", "Pression_bar", "Courant_A", "Taux_rebut_pct"]
    if df[colonnes].isna().any().any():
        raise ValueError("Capteurs prepares incomplets")
    scores = []
    for mesures in df[colonnes].itertuples(index=False, name=None):
        score = float(calculer_risque(*mesures))
        if not 0 <= score <= 1:
            raise ValueError("Le score doit etre entre 0 et 1")
        scores.append(score)
    df["score_risque"] = scores
    df["alerte"] = (df["score_risque"] >= seuil).astype(int)
    bilans, evenements_tous = [], []
    for nom, debut, fin in [
        ("septembre", "2026-09-01", "2026-09-27"),
        ("octobre", "2026-10-01", "2026-10-28")]:
        periode = df[df["Date"].between(debut, fin)].copy()
        bilan, evenements = evaluer(periode, excel)
        try:
            evenements, total = appliquer_calculs(
                evenements, cout_arret, gain_panne_anticipee, gain_fausse_alerte)
        except NotImplementedError as e:
            raise SystemExit(f"Completer les fonctions economiques dans analyse.py : {e}") from e
        bilan["periode"] = nom
        bilan["gain_net_eur"] = total
        evenements["periode"] = nom
        bilans.append(bilan)
        evenements_tous.append(evenements)
    df[df["Date"].between("2026-10-01", "2026-10-28")][
        ["ID_machine", "Date", "score_risque", "alerte"]
    ].to_csv(sorties / "alertes.csv", sep=";", index=False)
    tab = pd.DataFrame(bilans)
    tab.to_csv(sorties / "bilan.csv", sep=";", index=False)
    pd.concat(evenements_tous, ignore_index=True).to_csv(
        sorties / "evenements_evalues.csv", sep=";", index=False)
    historique = bilan_historique(excel, sorties)
    print(tab[["periode", "alertes", "pannes_anticipees", "fausses_alertes",
               "pannes_manquees", "gain_net_eur"]].to_string(index=False))
    print(f"Registre historique : {len(historique)} interventions ; "
          f"{(~historique['Machine_referencee']).sum()} non referencee(s) ; "
          f"{(historique['Statut_cout']=='Estime').sum()} cout(s) estime(s)")
    print("Resultats disponibles dans sorties/ et dans app.py")

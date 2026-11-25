"""PRODCONNECT | VOTRE PROGRAMME PYTHON

Pour commencer, completez les quatre fonctions ci-dessous (et SEUIL_ALERTE
si vous le souhaitez). En exploration libre, vous pouvez aussi lire ou adapter
outils/moteur.py, apres avoir sauvegarde une version fonctionnelle. Lancer :
    python analyse.py

Le script charge des capteurs DEJA PREPARES, evalue septembre et octobre,
puis produit des CSV pour Streamlit. Pas de nettoyage a realiser.
"""

SEUIL_ALERTE = 0.5

# 1. VOTRE ALGORITHME DE RISQUE, entre 0 et 1.
def calculer_risque(temperature, vibration, pression, courant, rebut):
    """Score heuristique basé sur 3 capteurs, borné entre 0 et 1."""
    risque = 0.0
    if temperature >= 78.0:
        risque += 0.35
    if vibration >= 5.0:
        risque += 0.35
    if rebut >= 4.5:
        risque += 0.30
    return float(max(0.0, min(1.0, risque)))


# 2. VOS TROIS FONCTIONS ECONOMIQUES.
def cout_arret(duree_heures, cout_horaire):
    """Cout d'un arret en euros."""
    return duree_heures * cout_horaire


def gain_panne_anticipee(duree_heures, cout_horaire, cout_preventif):
    """Gain versus une panne non anticipee (panne entierement evitee)."""
    return cout_arret(duree_heures, cout_horaire) - cout_preventif


def gain_fausse_alerte(cout_inspection):
    """Gain negatif d'une inspection inutile."""
    return -cout_inspection


if __name__ == "__main__":
    # Outil fourni. Vous n'avez pas besoin de lire ni de modifier son code.
    from outils.moteur import lancer
    lancer(calculer_risque, cout_arret, gain_panne_anticipee,
           gain_fausse_alerte, SEUIL_ALERTE)
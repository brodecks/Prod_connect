"""Streamlit V13 : application de depart fonctionnelle.
Lancer : python -m streamlit run app.py

Le tableau de bord fonctionne deja. Vous pouvez librement l'adapter
au besoin metier et faire apparaitre les resultats de votre score Python.
"""
from pathlib import Path
import pandas as pd
import streamlit as st

racine = Path(__file__).parent
excel = racine / "donnees/ProdConnect_2026.xlsx"
machines = pd.read_excel(excel, sheet_name="Machines")
interventions = pd.read_excel(excel, sheet_name="Interventions")

st.title("ProdConnect | Maintenance")
st.caption("Exemple de depart : les donnees proviennent du classeur Excel.")

# Exemples de DataFrame pandas, comme dans le TD :
# machines.head()                   -> premieres lignes
# len(machines)                    -> nombre de machines
# machines[machines['Ligne'] == 'Ligne A'] -> machines de la ligne A

col1, col2 = st.columns(2)
with col1:
    st.metric("Machines suivies", len(machines))
with col2:
    cout_moyen_connu = machines["Cout_horaire_arret"].mean()
    st.metric("Cout horaire moyen connu", f"{cout_moyen_connu:.0f} €/h")
st.caption("M07 a un cout manquant : la moyenne ne porte que sur les couts connus.")

st.subheader("Nombre de machines par ligne")
par_ligne = machines["Ligne"].value_counts().sort_index()
st.bar_chart(par_ligne)

st.subheader("Exemple de manipulation d'un DataFrame")
st.dataframe(machines.head(), hide_index=True)

# Resultat du programme Python, sans connexion automatique compliquee.
fichier = racine / "sorties/alertes.csv"
if fichier.exists():
    alertes = pd.read_csv(fichier, sep=";")
    st.subheader("Scores de risque calcules en Python")
    st.dataframe(alertes.head(), hide_index=True)
else:
    st.info("Pour les scores : completer les fonctions dans analyse.py, puis lancer python analyse.py.")

# POUR ALLER PLUS LOIN (facultatif) : ajouter une interaction (selectbox,
# filtre...), commenter les scores Python, ou recommander une machine.
# Vous pouvez conserver les deux indicateurs et le graphique de depart.

"""
Étape 1.1 — Le rerun Streamlit et pourquoi une variable ordinaire ne survit pas.

Lancer avec : streamlit run demo_rerun.py

Observez :
- le compteur "naïf" (variable Python ordinaire) reste bloqué à 1 après N clics,
  car il est réinitialisé à 0 à chaque rerun, juste avant d'être incrémenté ;
- le compteur stocké dans st.session_state s'incrémente correctement, car
  session_state persiste entre les reruns (il est propre à un onglet/session) ;
- l'horodatage en haut de page change à CHAQUE interaction, y compris une
  simple frappe dans le champ prénom qui ne déclenche pourtant aucun clic sur
  le bouton — preuve que Streamlit ré-exécute tout le script à chaque widget
  qui change d'état, pas seulement au clic sur "Incrémenter".
"""
import datetime as dt

import streamlit as st

st.title("Démo — le rerun Streamlit")

# Preuve visuelle du rerun : cette ligne s'affiche à CHAQUE exécution du script.
st.write(f"Exécution du script à {dt.datetime.now().strftime('%H:%M:%S.%f')}")

prenom = st.text_input("Votre prénom")

st.divider()
st.subheader("Compteur naïf (variable Python ordinaire)")

# BUG VOLONTAIRE : cette variable est réinitialisée à 0 à chaque rerun,
# donc quel que soit le nombre de clics, elle affichera toujours 1.
compteur_naif = 0
if st.button("Incrémenter (naïf)"):
    compteur_naif += 1
st.write(f"Valeur du compteur naïf : {compteur_naif}")

st.divider()
st.subheader("Compteur corrigé (st.session_state)")

# Initialisation : la clé n'est créée QUE si elle n'existe pas déjà,
# sinon on la remettrait à zéro à chaque rerun (même bug que ci-dessus).
if "compteur" not in st.session_state:
    st.session_state.compteur = 0

col1, col2 = st.columns(2)
with col1:
    if st.button("Incrémenter (session_state)"):
        st.session_state.compteur += 1
with col2:
    if st.button("Réinitialiser"):
        st.session_state.compteur = 0

st.write(f"Valeur du compteur en session_state : {st.session_state.compteur}")

if prenom:
    st.caption(f"Bonjour {prenom}, tape du texte ici pour déclencher un rerun sans cliquer sur aucun bouton.")

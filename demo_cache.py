"""
Étape 1.2 — Mesurer le coût du cache sur un pipeline de sentiment français.

Lancer avec : streamlit run demo_cache.py

Protocole de mesure (voir rapport pour les chiffres retenus) :
  1. Choisir une version dans la barre latérale (naïve / cache_resource / cache_data).
  2. Saisir un texte, cliquer "Analyser" 20 fois de suite (N = 20 interactions).
  3. Relever à chaque clic : temps de chargement, temps d'inférence.
  4. Reporter temps total, temps moyen par interaction et facteur d'accélération
     par rapport à la version naïve dans le tableau du rapport.

Modèle utilisé : cmarkea/distilcamembert-base-sentiment (léger, adapté au CPU
gratuit d'un Space).
"""
import time

import streamlit as st
from transformers import pipeline

MODELE = "cmarkea/distilcamembert-base-sentiment"

st.set_page_config(page_title="Démo cache", layout="centered")
st.title("Démo — coût du cache sur un pipeline de sentiment")

version = st.radio(
    "Version à tester",
    ["(a) naïve — sans cache", "(b) @st.cache_resource", "(c) @st.cache_resource + @st.cache_data"],
)

if "log" not in st.session_state:
    st.session_state.log = []


# --- (b) et (c) : le pipeline n'est chargé qu'une seule fois, partagé entre
#     tous les utilisateurs de la session serveur -----------------------------
@st.cache_resource(show_spinner=False)
def charger_modele():
    return pipeline("sentiment-analysis", model=MODELE, tokenizer=MODELE)


# --- (c) uniquement : le RÉSULTAT (une valeur sérialisable : dict) est mis en
#     cache pour un même texte -> deuxième appel quasi instantané -------------
@st.cache_data(show_spinner=False)
def analyser_cache(texte: str):
    modele = charger_modele()
    return modele(texte)[0]


texte = st.text_area("Avis à analyser", "Le réseau est catastrophique depuis trois jours.")

if st.button("Analyser"):
    t0 = time.perf_counter()

    if version.startswith("(a)"):
        # (a) naïve : le pipeline est recréé (donc rechargé) à CHAQUE clic.
        t_charge_debut = time.perf_counter()
        modele = pipeline("sentiment-analysis", model=MODELE, tokenizer=MODELE)
        t_chargement = time.perf_counter() - t_charge_debut

        t_inf_debut = time.perf_counter()
        resultat = modele(texte)[0]
        t_inference = time.perf_counter() - t_inf_debut

    elif version.startswith("(b)"):
        t_charge_debut = time.perf_counter()
        modele = charger_modele()  # quasi nul après le 1er appel (mis en cache_resource)
        t_chargement = time.perf_counter() - t_charge_debut

        t_inf_debut = time.perf_counter()
        resultat = modele(texte)[0]
        t_inference = time.perf_counter() - t_inf_debut

    else:
        t_charge_debut = time.perf_counter()
        charger_modele()
        t_chargement = time.perf_counter() - t_charge_debut

        t_inf_debut = time.perf_counter()
        resultat = analyser_cache(texte)  # quasi nul si texte déjà vu (cache_data)
        t_inference = time.perf_counter() - t_inf_debut

    total = time.perf_counter() - t0
    st.session_state.log.append(
        {
            "version": version,
            "chargement_s": round(t_chargement, 4),
            "inference_s": round(t_inference, 4),
            "total_s": round(total, 4),
        }
    )
    st.write(resultat)

if st.session_state.log:
    st.subheader("Journal des interactions")
    st.dataframe(st.session_state.log, width="stretch")
    if st.button("Vider le journal"):
        st.session_state.log = []

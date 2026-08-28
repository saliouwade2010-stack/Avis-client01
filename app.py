"""
Radar d'avis clients — TP13.

Point d'entrée Streamlit. st.set_page_config DOIT être le premier appel
Streamlit du script (sinon Streamlit lève une erreur).
"""
import datetime as dt
import io

import pandas as pd
import streamlit as st

from moteur import (
    TAILLE_LOT,
    analyser_sentiments,
    charger_moteur,
    detecter_themes,
    evaluer_contre_verite_terrain,
    resumer_avis_negatifs,
)

st.set_page_config(page_title="Radar d'avis clients", page_icon="📡", layout="wide")

COLONNES_OBLIGATOIRES = {"id", "date", "avis"}
CHEMIN_EXEMPLE = "exemple_avis.csv"
THEMES_DISPONIBLES = ["réseau", "facturation", "service client", "application mobile", "prix"]


# -----------------------------------------------------------------------------
# Ingestion et nettoyage (étape 2.1) — mise en cache_data sur le CONTENU en
# octets du fichier, jamais sur l'objet UploadedFile (qui n'est pas hashable
# de façon stable d'un rerun à l'autre : la clé de cache changerait à chaque
# exécution et le cache ne servirait jamais).
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def charger_et_nettoyer(contenu_octets: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(contenu_octets), encoding="utf-8")
    colonnes_manquantes = COLONNES_OBLIGATOIRES - set(df.columns)
    if colonnes_manquantes:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(colonnes_manquantes))}")

    df = df.dropna(subset=["avis"])
    df["avis"] = df["avis"].astype(str).str.strip()
    df = df[df["avis"] != ""]

    n_avant = len(df)
    doublons = df.duplicated(subset=["avis"]).sum()
    df = df.drop_duplicates(subset=["avis"]).reset_index(drop=True)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df.attrs["doublons_ecartes"] = int(doublons)
    df.attrs["lignes_avant_nettoyage"] = n_avant
    return df


# -----------------------------------------------------------------------------
# Barre latérale
# -----------------------------------------------------------------------------
st.sidebar.header("Paramètres")

fichier_depose = st.sidebar.file_uploader("Déposer un CSV d'avis", type=["csv"])

modele_sentiment_choisi = st.sidebar.selectbox(
    "Modèle de sentiment",
    ["cmarkea/distilcamembert-base-sentiment (par défaut)", "tblard/tf-allocine"],
    help="Le second modèle n'est câblé qu'à titre d'exemple de choix dans moteur.py.",
)

themes_selectionnes = st.sidebar.multiselect(
    "Thèmes à détecter", THEMES_DISPONIBLES, default=THEMES_DISPONIBLES
)

inclure_resume = st.sidebar.checkbox("Inclure le résumé (tête la plus lente)", value=False)

# -----------------------------------------------------------------------------
# Chargement du fichier (déposé ou exemple par défaut)
# -----------------------------------------------------------------------------
if fichier_depose is not None:
    contenu = fichier_depose.getvalue()
    nom_source = fichier_depose.name
else:
    with open(CHEMIN_EXEMPLE, "rb") as f:
        contenu = f.read()
    nom_source = CHEMIN_EXEMPLE
    st.sidebar.info("Aucun fichier déposé — jeu de démonstration chargé automatiquement.")

try:
    df = charger_et_nettoyer(contenu)
except ValueError as e:
    st.error(f"Fichier invalide : {e}")
    st.stop()
except Exception as e:
    st.error(f"Impossible de lire le fichier (encodage ou format incorrect) : {e}")
    st.stop()

if df.attrs.get("doublons_ecartes"):
    st.sidebar.warning(f"{df.attrs['doublons_ecartes']} doublon(s) écarté(s).")

nb_max = st.sidebar.slider("Nombre d'avis à analyser", 10, len(df), min(len(df), 100))

st.title("📡 Radar d'avis clients")
st.caption(f"Source : {nom_source} — {len(df)} avis valides après nettoyage")
st.dataframe(df.head(10), width='stretch')

lancer = st.sidebar.button("Lancer l'analyse", type="primary")

if "historique" not in st.session_state:
    st.session_state.historique = []
if "resultats" not in st.session_state:
    st.session_state.resultats = None

# -----------------------------------------------------------------------------
# Analyse (étape 2.2) — ne s'exécute qu'au clic sur "Lancer l'analyse", jamais
# à chaque rerun déclenché par un simple changement de filtre d'affichage.
# -----------------------------------------------------------------------------
if lancer:
    sous_df = df.head(nb_max).copy()
    moteur = charger_moteur()

    barre = st.progress(0.0, text="Analyse des sentiments...")
    sentiments, n_tronques = analyser_sentiments(
        moteur, sous_df["avis"].tolist(), progress_callback=lambda p: barre.progress(p, text="Analyse des sentiments...")
    )
    sous_df["sentiment"] = [r["label"] for r in sentiments]
    sous_df["score"] = [round(r["score"], 3) for r in sentiments]

    barre2 = st.progress(0.0, text="Détection des thèmes...")
    if themes_selectionnes:
        themes_resultats = detecter_themes(
            moteur, sous_df["avis"].tolist(), themes_selectionnes,
            progress_callback=lambda p: barre2.progress(p, text="Détection des thèmes..."),
        )
        sous_df["themes_detectes"] = [
            ", ".join(l for l, s in zip(r["labels"], r["scores"]) if s >= 0.5) or "aucun"
            for r in themes_resultats
        ]
    else:
        sous_df["themes_detectes"] = "—"

    resume_negatifs = ""
    if inclure_resume:
        with st.spinner("Génération du résumé des avis négatifs..."):
            negatifs = sous_df.loc[sous_df["sentiment"] == "négatif", "avis"].tolist()
            resume_negatifs = resumer_avis_negatifs(moteur, negatifs)

    st.session_state.resultats = {
        "df": sous_df,
        "n_tronques": n_tronques,
        "resume_negatifs": resume_negatifs,
    }
    st.session_state.historique.append(
        {
            "horodatage": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fichier": nom_source,
            "n_avis": len(sous_df),
            "part_positifs": round((sous_df["sentiment"] == "positif").mean() * 100, 1),
        }
    )

# -----------------------------------------------------------------------------
# Tableau de bord (étape 2.3)
# -----------------------------------------------------------------------------
if st.session_state.resultats is None:
    st.info("Configurez les paramètres dans la barre latérale puis cliquez sur « Lancer l'analyse ».")
    st.stop()

res = st.session_state.resultats
res_df = res["df"]

a_verite_terrain = "note" in res_df.columns and res_df["note"].notna().any()
noms_onglets = ["Synthèse", "Détail", "Historique"]
if a_verite_terrain:
    noms_onglets.insert(2, "Évaluation")
onglets = st.tabs(noms_onglets)
onglet_synthese, onglet_detail = onglets[0], onglets[1]
if a_verite_terrain:
    onglet_evaluation, onglet_historique = onglets[2], onglets[3]
else:
    onglet_historique = onglets[2]

with onglet_synthese:
    part_positifs = (res_df["sentiment"] == "positif").mean() * 100
    score_moyen = res_df["score"].mean()
    tous_themes = ", ".join(res_df["themes_detectes"]).split(", ")
    tous_themes = [t for t in tous_themes if t not in ("aucun", "—", "")]
    theme_dominant = pd.Series(tous_themes).mode().iat[0] if tous_themes else "N/A"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avis analysés", len(res_df), help="Nombre d'avis pris en compte dans cette analyse")
    c2.metric("Part de positifs", f"{part_positifs:.1f} %", help="Proportion d'avis classés positifs")
    c3.metric("Confiance moyenne", f"{score_moyen:.2f}", help="Score moyen du modèle de sentiment")
    c4.metric("Thème dominant", theme_dominant, help="Thème le plus fréquemment détecté")

    colg1, colg2 = st.columns(2)
    with colg1:
        st.subheader("Répartition des sentiments")
        st.bar_chart(res_df["sentiment"].value_counts())
    with colg2:
        st.subheader("Thèmes les plus fréquents")
        if tous_themes:
            st.bar_chart(pd.Series(tous_themes).value_counts())
        else:
            st.caption("Aucun thème sélectionné.")

    if "date" in res_df.columns and res_df["date"].notna().any():
        st.subheader("Évolution hebdomadaire de la part d'avis négatifs")
        tmp = res_df.dropna(subset=["date"]).set_index("date")
        tmp["negatif"] = (tmp["sentiment"] == "négatif").astype(int)
        hebdo = tmp["negatif"].resample("W").mean() * 100
        st.line_chart(hebdo)

    if res["resume_negatifs"]:
        with st.expander("Résumé des avis négatifs"):
            st.write(res["resume_negatifs"])

with onglet_detail:
    st.subheader("Détail des avis (trié par négativité)")
    filtre_sentiment = st.multiselect("Filtrer par sentiment", res_df["sentiment"].unique().tolist())
    filtre_theme = st.text_input("Filtrer par thème (contient)")

    affiche = res_df.copy()
    # Tri par score de négativité : on force les négatifs en tête via un score signé.
    affiche["score_negativite"] = affiche.apply(
        lambda r: r["score"] if r["sentiment"] == "négatif" else (0.5 if r["sentiment"] == "neutre" else 1 - r["score"]), axis=1
    )
    affiche = affiche.sort_values("score_negativite", ascending=False)

    if filtre_sentiment:
        affiche = affiche[affiche["sentiment"].isin(filtre_sentiment)]
    if filtre_theme:
        affiche = affiche[affiche["themes_detectes"].str.contains(filtre_theme, case=False, na=False)]

    st.dataframe(
        affiche[["avis", "sentiment", "score", "themes_detectes"]],
        width='stretch',
    )
    st.download_button(
        "Exporter le CSV enrichi",
        data=affiche.to_csv(index=False).encode("utf-8"),
        file_name="avis_enrichis.csv",
        mime="text/csv",
    )

if a_verite_terrain:
    with onglet_evaluation:
        st.subheader("Accord avec la note client (question 7)")
        st.caption("Binarisation : note ≤ 2 → négatif, note ≥ 4 → positif, note = 3 exclue (zone neutre ambiguë).")
        evaluation = evaluer_contre_verite_terrain(res_df)
        if evaluation is None:
            st.info("Pas assez d'avis avec une note exploitable (hors note = 3) pour évaluer le modèle.")
        else:
            accuracy, f1, matrice = evaluation
            c1, c2 = st.columns(2)
            c1.metric("Accuracy", f"{accuracy:.2%}", help="Calculée avec evaluate.load('accuracy')")
            c2.metric("F1-score", f"{f1:.2%}", help="Calculée avec evaluate.load('f1')")
            st.subheader("Matrice de confusion")
            st.dataframe(matrice, width="stretch")
            st.caption(
                "Erreurs les plus fréquentes attendues : avis ironiques (polarité lexicale positive, "
                "sens réel négatif) et avis très courts (peu de signal, score proche de 0,5)."
            )

with onglet_historique:
    st.subheader("Historique des analyses de cette session")
    if st.session_state.historique:
        st.dataframe(pd.DataFrame(st.session_state.historique), width='stretch')
    else:
        st.caption("Aucune analyse encore enregistrée.")

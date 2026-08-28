"""
Moteur d'analyse du Radar d'avis clients : trois têtes de modèle chargées
une seule fois (via @st.cache_resource) et appelées par lots.

Séparé de app.py pour que l'interface reste lisible et que le chargement
des modèles soit testable indépendamment.
"""
import time

import streamlit as st
from transformers import pipeline

MODELE_SENTIMENT = "cmarkea/distilcamembert-base-sentiment"
MODELE_THEMES = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
MODELE_RESUME = "plguillou/t5-base-fr-sum-cnndm"

LONGUEUR_MAX_SENTIMENT = 512
LONGUEUR_MAX_THEMES = 256
TAILLE_LOT = 16


@st.cache_resource(show_spinner="Chargement des modèles (une seule fois)...")
def charger_moteur():
    """Instancie les trois pipelines et les renvoie ensemble.

    Objet non sérialisable -> @st.cache_resource (partagé, pas copié),
    jamais @st.cache_data qui tenterait de sérialiser le modèle à chaque appel.
    """
    sentiment = pipeline(
        "sentiment-analysis",
        model=MODELE_SENTIMENT,
        tokenizer=MODELE_SENTIMENT,
        truncation=True,
        max_length=LONGUEUR_MAX_SENTIMENT,
    )
    themes = pipeline("zero-shot-classification", model=MODELE_THEMES)
    resume = pipeline("summarization", model=MODELE_RESUME, tokenizer=MODELE_RESUME)
    return {"sentiment": sentiment, "themes": themes, "resume": resume}


def _compter_tokens_tronques(textes, tokenizer, longueur_max):
    """Renvoie le nombre de textes dont la tokenisation dépasse longueur_max
    (donc effectivement tronqués par le pipeline)."""
    n_tronques = 0
    for t in textes:
        ids = tokenizer(t, truncation=False)["input_ids"]
        if len(ids) > longueur_max:
            n_tronques += 1
    return n_tronques


def normaliser_sentiment(label_brut: str) -> str:
    """cmarkea/distilcamembert-base-sentiment renvoie des labels du type
    '1 star' .. '5 stars' (notation à la Amazon), pas directement
    positif/négatif. On les ramène à trois classes, avec le même seuil que
    la binarisation de la question 7 (<=2 négatif, ==3 neutre, >=4 positif).
    """
    n = int(label_brut.strip().split()[0])
    if n <= 2:
        return "négatif"
    if n == 3:
        return "neutre"
    return "positif"


def analyser_sentiments(moteur, avis, progress_callback=None):
    """Classification de séquence par lots ; renvoie label + score de confiance."""
    pipe = moteur["sentiment"]
    n_tronques = _compter_tokens_tronques(avis, pipe.tokenizer, LONGUEUR_MAX_SENTIMENT)

    resultats = []
    n = len(avis)
    for debut in range(0, n, TAILLE_LOT):
        lot = avis[debut : debut + TAILLE_LOT]
        sorties = pipe(lot, truncation=True, max_length=LONGUEUR_MAX_SENTIMENT, batch_size=TAILLE_LOT)
        for s in sorties:
            s["label_brut"] = s["label"]
            s["label"] = normaliser_sentiment(s["label"])
        resultats.extend(sorties)
        if progress_callback:
            progress_callback(min(debut + TAILLE_LOT, n) / n)
    return resultats, n_tronques


def detecter_themes(moteur, avis, themes_cibles, progress_callback=None):
    """Zero-shot multi-étiquettes : un avis peut relever de plusieurs thèmes."""
    pipe = moteur["themes"]
    resultats = []
    n = len(avis)
    for debut in range(0, n, TAILLE_LOT):
        lot = avis[debut : debut + TAILLE_LOT]
        sorties = pipe(
            lot,
            candidate_labels=themes_cibles,
            multi_label=True,
            truncation=True,
            max_length=LONGUEUR_MAX_THEMES,
        )
        # pipeline() renvoie un seul dict (pas une liste) si len(lot) == 1
        if isinstance(sorties, dict):
            sorties = [sorties]
        resultats.extend(sorties)
        if progress_callback:
            progress_callback(min(debut + TAILLE_LOT, n) / n)
    return resultats


def resumer_avis_negatifs(moteur, avis_negatifs, longueur_max_source=800):
    """Concatène les avis négatifs et produit un résumé en 3 lignes environ.
    Tête la plus lente : à n'appeler que si la case "résumé" est cochée.
    """
    if not avis_negatifs:
        return "Aucun avis négatif à résumer."
    texte = " ".join(avis_negatifs)[:longueur_max_source]
    pipe = moteur["resume"]
    sortie = pipe(texte, truncation=True, max_length=120, min_length=30)
    return sortie[0]["summary_text"]


def chronometrer_sequentiel_vs_lots(moteur, avis):
    """Utilitaire pour la question 6 : compare un traitement avis par avis
    (boucle Python) à un traitement par lots de TAILLE_LOT."""
    pipe = moteur["sentiment"]

    t0 = time.perf_counter()
    for a in avis:
        pipe(a, truncation=True, max_length=LONGUEUR_MAX_SENTIMENT)
    t_sequentiel = time.perf_counter() - t0

    t0 = time.perf_counter()
    for debut in range(0, len(avis), TAILLE_LOT):
        lot = avis[debut : debut + TAILLE_LOT]
        pipe(lot, truncation=True, max_length=LONGUEUR_MAX_SENTIMENT, batch_size=TAILLE_LOT)
    t_lots = time.perf_counter() - t0

    return t_sequentiel, t_lots


def evaluer_contre_verite_terrain(df_resultats):
    """Question 7 : binarise la colonne `note` (<=2 négatif, >=4 positif, 3
    exclu) et calcule accuracy/F1 avec la bibliothèque `evaluate` (chapitre 5),
    plutôt qu'un calcul manuel — API unifiée, cohérente avec le reste du cours.

    Renvoie (accuracy, f1, matrice_confusion_dataframe) ou None si la colonne
    `note` est absente ou si aucune ligne n'est exploitable après binarisation.
    """
    import evaluate
    import pandas as pd

    if "note" not in df_resultats.columns:
        return None

    df = df_resultats.dropna(subset=["note"]).copy()
    df = df[df["note"] != 3]  # zone neutre ambiguë exclue de l'évaluation
    if df.empty:
        return None

    df["reference"] = (df["note"] >= 4).astype(int)  # 1 = positif, 0 = négatif
    df["prediction"] = (df["sentiment"] == "positif").astype(int)

    metric_accuracy = evaluate.load("accuracy")
    metric_f1 = evaluate.load("f1")
    acc = metric_accuracy.compute(predictions=df["prediction"], references=df["reference"])["accuracy"]
    f1 = metric_f1.compute(predictions=df["prediction"], references=df["reference"])["f1"]

    matrice = pd.crosstab(
        df["reference"].map({0: "Réel négatif", 1: "Réel positif"}),
        df["prediction"].map({0: "Prédit négatif", 1: "Prédit positif"}),
    )
    return round(acc, 4), round(f1, 4), matrice

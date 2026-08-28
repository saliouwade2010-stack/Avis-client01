---
title: Radar Avis Clients
emoji: 📡
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.62.0
app_file: app.py
pinned: false
license: mit
hardware: cpu-basic
---

# 📡 Radar d'avis clients — Waaw Telecom (démo)

Application Streamlit qui ingère un CSV d'avis clients en français et répond
en moins d'une minute à trois questions : les clients sont-ils satisfaits ?
De quoi parlent-ils ? Que faut-il retenir en trois lignes ?

TP13 — Module 5 (Déploiement), Master IA.

## Capture d'écran

*(à ajouter après le premier lancement local — onglet Synthèse du tableau de bord)*

## Format du CSV attendu

| Colonne | Obligatoire | Description |
|---|---|---|
| `id` | oui | identifiant unique de l'avis |
| `date` | oui | date de l'avis (`AAAA-MM-JJ`) |
| `avis` | oui | texte de l'avis, en français |
| `note` | non | note client de 1 à 5, sert de vérité terrain pour évaluer le modèle |

Un jeu de démonstration de 200 avis synthétiques est fourni dans
`data/exemple_avis.csv` et se charge automatiquement si aucun fichier n'est
déposé.

## Modèles utilisés

| Tête | Modèle | Rôle |
|---|---|---|
| Sentiment | [cmarkea/distilcamembert-base-sentiment](https://huggingface.co/cmarkea/distilcamembert-base-sentiment) | classification positif / neutre / négatif + score de confiance |
| Thèmes | [MoritzLaurer/mDeBERTa-v3-base-mnli-xnli](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli) | zero-shot multi-étiquettes sur les thèmes choisis |
| Résumé | [plguillou/t5-base-fr-sum-cnndm](https://huggingface.co/plguillou/t5-base-fr-sum-cnndm) | synthèse des avis négatifs (activable, tête la plus lente) |

## Évaluation contre la vérité terrain

Quand la colonne `note` est présente, un onglet **Évaluation** calcule
l'accuracy et le F1-score du modèle de sentiment contre la note client
binarisée (≤2 négatif, ≥4 positif, 3 exclu), via la bibliothèque
[`evaluate`](https://huggingface.co/docs/evaluate) (`evaluate.load("accuracy")`,
`evaluate.load("f1")`) plutôt qu'un calcul manuel, et affiche la matrice de
confusion correspondante.

## Architecture du dépôt

```
radar-avis-clients/
├── app.py                 # point d'entrée Streamlit (interface + tableau de bord)
├── moteur.py               # chargement (cache_resource) et analyse par lots
├── requirements.txt        # dépendances épinglées
├── README.md                # ce fichier (en-tête YAML du Space)
├── .streamlit/config.toml   # thème de l'application
├── data/exemple_avis.csv    # jeu de démonstration (200 avis)
├── data/generer_donnees.py  # script ayant généré le jeu de démonstration
├── demo_rerun.py             # étape 1.1 — démo du rerun Streamlit
└── demo_cache.py             # étape 1.2 — mesure du coût du cache
```

## Lancer en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Coût d'exécution observé

*(à compléter après déploiement — voir rapport, questions 3, 6 et 11 : temps
de build, temps de premier affichage, facteur d'accélération mesuré)*

## Limites et biais

À éprouver explicitement et documenter (voir rapport) :
- **ironie** : « bravo pour les trois jours sans réseau, du grand art » — le
  modèle de sentiment n'est pas entraîné pour détecter le second degré et
  risque de classer ce type d'avis comme positif ou neutre.
- **français mêlé de wolof** : « réseau bi dafa bon, merci beaucoup » — le
  modèle traite le texte comme du français bruit ; les segments en wolof sont
  ignorés ou mal tokenisés, ce qui peut dégrader le score de confiance.
- **avis très courts** (« ok », « bof ») : peu de signal lexical, le modèle
  est souvent moins confiant (score proche de 0,5) sur ces cas.

## Comparaison avec le Space Gradio (TP9)

Voir le rapport pour la comparaison argumentée sur les cinq axes : modèle
d'exécution, gestion de l'état, mise en page, latence perçue, facilité de
mise en production.

## Secrets

Si un modèle privé est utilisé, ajouter un `HF_TOKEN` dans *Settings →
Variables and secrets* du Space et le lire via `os.environ["HF_TOKEN"]` —
jamais en dur dans le code ni dans un `.streamlit/secrets.toml` versionné.

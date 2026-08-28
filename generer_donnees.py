"""
Génère data/exemple_avis.csv : 200 avis clients synthétiques en français
pour un opérateur télécom sénégalais fictif ("Waaw Telecom"), couvrant
5 thèmes (réseau, facturation, service client, application mobile, prix),
avec quelques cas difficiles volontaires : ironie, mélange français/wolof,
avis très courts, et une poignée de doublons EXACTS volontaires pour
exercer la détection de doublons de l'étape 2.1. Colonnes : id, date, avis, note.
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)

QUARTIERS = ["Ouakam", "Rufisque", "Parcelles Assainies", "Yoff", "Mermoz", "Sacré-Cœur",
             "Grand Yoff", "Liberté 6", "Guédiawaye", "Pikine", "Ngor", "Almadies"]
FORFAITS = ["Illimité 20 Go", "Forfait Soir", "Pass Journalier", "Forfait Week-end", "Illimité 50 Go"]
MONTANTS = ["1 500", "2 000", "3 500", "5 000", "10 000"]
DUREES = ["deux jours", "trois jours", "une semaine", "24 heures", "cinq heures"]

# --- Modèles de phrases (avec emplacements variables) par thème et polarité --
POSITIFS = [
    "Le réseau est enfin stable à {quartier}, bravo.",
    "Facturation claire ce mois-ci sur mon {forfait}, aucune surprise.",
    "Le conseiller m'a répondu en moins de 5 minutes pour mon souci de {forfait}, très efficace.",
    "L'application mobile est devenue beaucoup plus rapide depuis la mise à jour.",
    "Bon rapport qualité-prix pour le {forfait} à {montant} F.",
    "La 4G passe très bien même à {quartier}.",
    "Service client courtois, mon problème de facturation a été réglé du premier coup.",
    "Nouvelle interface de l'appli claire et agréable à utiliser.",
    "Le {forfait} est raisonnable comparé à la concurrence.",
    "Recharge instantanée à {quartier}, aucun souci depuis {duree}.",
    "Le débit s'est nettement amélioré à {quartier} ces derniers jours.",
    "Facture détaillée et compréhensible ce mois, merci.",
    "Réponse rapide sur WhatsApp pour mon souci de solde de {montant} F.",
    "L'appli ne plante plus depuis la dernière mise à jour.",
    "Offre promotionnelle intéressante sur le {forfait} ce trimestre.",
]
NEGATIFS = [
    "Toujours aucun réseau à {quartier} depuis {duree}, c'est inadmissible.",
    "On m'a facturé deux fois le {forfait} ce mois-ci.",
    "Impossible de joindre le service client, j'attends depuis {duree}.",
    "L'application plante à chaque ouverture depuis la mise à jour, illisible.",
    "Le prix du {forfait} a encore augmenté sans aucune explication.",
    "Aucune couverture réseau à {quartier} depuis la panne d'hier.",
    "On me prélève {montant} F que je n'ai jamais demandés.",
    "Conseiller désagréable au téléphone, aucune solution proposée pour mon {forfait}.",
    "L'appli demande de se reconnecter toutes les cinq minutes à {quartier}.",
    "Le {forfait} est trop cher pour un débit aussi faible.",
    "Coupures répétées pendant les appels importants à {quartier}.",
    "Ma réclamation de facturation de {montant} F reste sans réponse depuis {duree}.",
    "Support injoignable, j'ai envoyé trois messages sans retour depuis {duree}.",
    "Mise à jour de l'appli qui a supprimé mon historique de recharge.",
    "Prix du {forfait} doublé du jour au lendemain, sans prévenir personne.",
]
NEUTRES = [
    "Le réseau fonctionne à {quartier}, sans plus.",
    "Facture du {forfait} reçue à temps ce mois.",
    "J'ai eu un conseiller pour mon {forfait}, réponse correcte.",
    "L'application fait le nécessaire, rien d'exceptionnel.",
    "Le {forfait} à {montant} F est dans la moyenne du marché.",
]
IRONIQUES = [
    "Bravo pour les trois jours sans réseau, du grand art.",
    "Merci Waaw Telecom pour cette facture surprise, quelle générosité.",
    "Un service client si réactif qu'on a le temps de vieillir en attendant.",
    "L'application plante si joliment qu'on en oublierait presque d'être énervé.",
    "Encore une augmentation de prix, on ne s'ennuie jamais avec vous.",
]
MELANGE_WOLOF = [
    "Réseau bi dafa bon ce mois-ci, merci beaucoup.",
    "Facture bi dafa bare trop, li dafa diar.",
    "Service client bi ñëpp bon, ils ont réglé mon problème rapidement.",
    "Appli bi dafa poor, dafa toujours planter.",
    "Prix yi dafa cher trop, xoolal ndax dinañu wax.",
    "Dama bëgg ni réseau bi baax na leegi, jamm rekk.",
]
COURTS = ["Ok.", "Bof.", "Nul.", "Correct.", "Top !", "Moyen.", "Décevant.", "Parfait.", "Rien à dire.", "Peut mieux faire."]

# Un avis volontairement IDENTIQUE plusieurs fois (pour tester la détection
# de doublons demandée à l'étape 2.1 : "doublons signalés").
DOUBLONS_VOLONTAIRES = "Toujours aucun réseau depuis hier, très mécontent."


def remplir(modele: str) -> str:
    return modele.format(
        quartier=random.choice(QUARTIERS),
        forfait=random.choice(FORFAITS),
        montant=random.choice(MONTANTS),
        duree=random.choice(DUREES),
    )


rows = []
start = date(2026, 4, 1)
for i in range(1, 201):
    d = start + timedelta(days=random.randint(0, 150))
    r = random.random()
    if i <= 5:
        avis = IRONIQUES[i - 1]
        note = random.choice([1, 2])
    elif i <= 11:
        avis = MELANGE_WOLOF[i - 6]
        note = random.choice([2, 3, 4, 5])
    elif i <= 21:
        avis = random.choice(COURTS)
        note = random.choice([1, 2, 3, 4, 5])
    elif i in (22, 23, 24, 25, 26, 27):
        # 6 doublons exacts volontaires, répartis dans le fichier.
        avis = DOUBLONS_VOLONTAIRES
        note = random.choice([1, 2])
    elif r < 0.45:
        avis = remplir(random.choice(NEGATIFS))
        note = random.choice([1, 2])
    elif r < 0.80:
        avis = remplir(random.choice(POSITIFS))
        note = random.choice([4, 5])
    else:
        avis = remplir(random.choice(NEUTRES))
        note = 3
    rows.append({"id": i, "date": d.isoformat(), "avis": avis, "note": note})

with open("exemple_avis.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id", "date", "avis", "note"])
    w.writeheader()
    w.writerows(rows)

n_doublons = len(rows) - len({r["avis"] for r in rows})
print(f"{len(rows)} avis générés dans exemple_avis.csv ({n_doublons} doublons exacts détectables)")

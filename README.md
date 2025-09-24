# Analyse – Popularité des villageois d’Animal Crossing

## Contexte
Projet de data science réalisé dans le cadre d’un cours.  
Entreprise fictive : ** Fictive Insights** (cabinet d’études pour l’industrie du jeu vidéo).

Une entreprise cherche à faire une mascotte type animal pour son produit (jeux vidéo, dessin animé, même céréal)...
Nous avonc donc comme tâche de trouver quelles sont les charactéristiques les plus populaire chez une mascotte, et pour ce, nous avons choisis la license "Animal Crossing".
Ce jeu donne un large éventail de personnage et personnalités différentes, idéal pour recueillir de la data et l'analyser.

## Problématique


Quels sont les villageois **les plus** et **les moins** populaires selon la **région** (Global/Europe/Amérique/Japon) ?  

Quels attributs (genre, personnalité, espèce, hobby, signe astro, couleurs) sont associés aux niveaux de popularité ?

## Données
- `DATA/acnh_popularity_ranked.csv` — indice de popularité par villageois et par région  
  *(calculé en amont à partir de Google Trends/Pytrend + [classement communautaire Animal Crossing Portal](https://www.animalcrossingportal.com/tier-lists/new-horizons/all-villagers/#/))*
- `DATA/villagers.csv` — [caractéristiques des villageois](https://www.kaggle.com/datasets/prasertk/animal-crossing-new-horizons-with-image-url?resource=download&select=villagers.csv) (genre, personnalité, espèce, hobby, anniversaire, couleurs, image)

## Outils
- **Python** : `pandas`, `numpy`, `matplotlib`  
- **Streamlit** : dashboard interactif (`app.py`)


# dépendances de l'app
pip install streamlit pandas numpy matplotlib

# lancer le dashboard
streamlit run app.py

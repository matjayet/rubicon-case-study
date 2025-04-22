## rubicon_cs : Module personnalisé

`rubicon_cs` est un module Python personnalisé que j'ai développé pour faciliter l'exécution des notebooks de ce projet. Ce module contient toutes les fonctions nécessaires pour manipuler les données géospatiales, télécharger les images satellite via **SentinelHub**, et effectuer diverses opérations sur les indices de végétation, tout en automatisant la gestion de la taille des images et la segmentation sémantique d'une image à partir d'un modèle pré entrainé

### Fonctions principales

Les fonctions principales incluent, entre autres :

- **`geotiff_for_veg_index`** : Télécharge les images satellite correspondant à un indice de végétation spécifique (par exemple **NDVI**, **EVI**, **GNDVI**) pour une zone d'intérêt (AOI) et une plage de dates données. Si l'image dépasse la taille maximale autorisée par SentinelHub (2500x2500 pixels), la résolution est automatiquement ajustée pour respecter cette limite.

- **`png_for_target_date`** : Génère une image RGB au format **PNG** choisi pour une date donnée (si non disponible le plus proche possible) et l'AOI spécifié. Cela permet d'obtenir une image prête à être visualisée ou traitée pour la segmentation sémantique.

- **`semantic_segmentation_large_image`** : Réalise une segmentation sémantique sur une grande image en la découpant en **patches** de 512x512, effectuant des prédictions par patch, puis assemblant les résultats pour reconstruire le masque de segmentation complet.

### Installation

Si ce module n'est pas déjà installé, tu peux le faire en clonant le repo git ou en le copiant directement dans ton projet.


## Section 1 : Traitement d'image satellite Sentinel2 L2A avec indices de végétation

Ce code est utilisé pour télécharger et afficher une image satellite en utilisant un indice de végétation (par exemple, NDVI) pour une zone d'intérêt (AOI) spécifique. Le processus inclut la gestion de la couverture nuageuse et la sélection d'un intervalle de dates. Voici les étapes principales du code :

### 1. Définition des dates de début et de fin
Le code définit une période d'intérêt, par exemple **30 août 2024 au 30 septembre 2024**.

### 2. Sélection de l'indice de végétation
Un indice de végétation est choisi parmi plusieurs options, comme **NDVI**, **EVI**, **GNDVI**, etc. Dans cet exemple, l'indice choisi est **NDVI**.

### 3. Chargement de la zone d'intérêt (AOI)
La zone d'intérêt est chargée à partir d'un fichier **GeoJSON local** (`AOI_Rubicon.geojson`). Ce fichier contient la géométrie de la région à analyser.

### 4. Téléchargement de l'image SentinelHub
La fonction `geotiff_for_veg_index` de la bibliothèque `rubicon_cs.main` est utilisée pour télécharger l'image de l'indice de végétation correspondant à l'AOI et à la plage de dates spécifiée. Si l'image est trop grande, la résolution est ajustée pour respecter la limite de taille d'image de **2500x2500 pixels** imposée par SentinelHub.

### 5. Affichage de l'image
Enfin, l'image est affichée à l'aide de la fonction `display_geotiff` pour visualiser l'indice de végétation sur la période spécifiée.

### Remarques importantes
- N'oublie pas de mettre à jour le fichier `.env` avec ton **client ID** et ton **secret** pour SentinelHub.
- Le code peut être ajusté pour prendre en charge d'autres indices de végétation comme **EVI**, **GNDVI**, etc.
- Si l'image dépasse la taille maximale autorisée par SentinelHub (2500x2500 pixels), la résolution est automatiquement ajustée.

## Section 2 : Pipeline de segmentation sémantique sur grandes images

Ce pipeline permet de réaliser une segmentation sémantique sur des **grandes images** en les découpant en **patches de 512x512** et en reconstruisant le masque de segmentation. Voici les étapes principales :

1. **Chargement de l'image** :  
   L'image est récupérée via **Sentinel Hub** en format PNG.

2. **Découpage en patches** :  
   L'image est découpée en tuiles de **512x512** pixels, avec un **padding** si nécessaire pour garantir des dimensions multiples de 512.

3. **Prédiction par patch** :  
   Chaque patch est passé à travers un modèle de **segmentation sémantique** pour générer une prédiction.

4. **Assemblage du masque** :  
   Les prédictions des patches sont assemblées pour reconstruire le masque complet de segmentation.

5. **Affichage du résultat** :  
   Le masque final est visualisé avec une palette de couleurs et sauvegardé au format **PNG**.



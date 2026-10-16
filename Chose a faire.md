# **Listes de choses à améliorer après le test du notebook**

##  1) Ranger le programme en ordre et claire => polir le travail de l'année précédente 
- ### Les dossiers sont placés de manières confuses:
     - Certains sont mentionnés dans le programme mais manque à l'appel
     - Il y a la présence de plusieurs full_code
- ### Un seul fichier à executer
  On souhaiterais pouvoir proposer à l'utilisateur un seul fichier (executable) permettant de lancer une interface demandant les manuel, et qui lancera par la suite le programme python pour le déchiffrer en arrière plan.
( SI POSSIBLE: Egalement, en demandant l'autorisation à l'utilisateur d'installer les librairies necessaires dans un env virtuel crée ou qu'on aura crée (préférable) 
- ### Les programmes manquent de documentation:
  on a l'utilité de chaque ligne mais pas ce que cela lance et prend en paramètre, ainsi que ce que ça fait globalement dans le programme python final => rajouter ces infos alors ainsi qu'un fichier explicatif de l'utilité des dossiers et fichiers.
  Cela va certe prendre du temps mais c'est necessaire
- ### Pas besoin d'installer les librairies au préalable pour un utilisateur voulant utiliser le programme!!
On souhaiterais rendre l'utilisation la plus simple possible même pour des personnes ne sachant pas utiliser un terminal!

### En conclusion, on souhaiterais offrir un logiciel plus simple à executer (même pour les personnes les moins à l'aise en informatique),  ainsi qu'une meilleure organisation des fichiers et documentation. 

### SOLUTIONS: PyInstaller, cette librarie va nous permettre de créer un executable à partir d'un projet python, d'en faire un unique fichier qu'on pourra envoyer directement à un utilisateur. Celui-ci n'aura qu'à le lancer, sans avoir besoin d'installer python, librairies ou même d'env virtuelle!! 
Et utiliser une librarie d'interface graphique ex Gradio.

##  2) Augmenter les performances
- ### Un programme plus rapide et performant
Le programme est trop lent au lancement et plante pour certains PC.

### SOLUTIONS :

## 3) Proposer un preprocessing et une conversion PDF
- ### Proposer une conversion PDF efficace avec une table, une image de carte et une table mise en joint
- ### Pouvoir lire même les pdf les plus détériorer grâce au préprocessing 

## 4) Meilleur data set
- ### Plus de PDF d'entrainement
Trouver le schema, la carte et la table dans le manuel pdf. Pouvoir vérifier que c'est la carte correspond bien au schema, et que la table est bien celle de la carte!

- ### Reconnaissance dans la carte à partir de la table et du schema
- ### Creation de table d'élement
En programme python (je sais pas si ça avait été déjà fait): créer la table d'éléments si non présente dans le pdf joint à partir du schema => pvr ranger dans chaque catégories selon les composants

## 5) INTERFACE UTILISATEUR 
### - Une interface intuitive
Proposer une interface type app => d'abord une page acceuil avec le choix d'upload le fichier ou de faire des images en pdf
=> execution du programme avec le fichier choisi:
On affichera 3 parties:
- à gauche un dérouleur qui nous permet de selectionner le type
Après selections du type, on affiche tt les composants de se type là dans cette même partie, qu'on pourra naviger en descendant.
En cliquant sur le composants, on zoomera sur celui-ci sur le schema et la carte
- au centre la carte
- a droite le schema electronique

(est ce qu'on préenregistre les fichiers précédente??)





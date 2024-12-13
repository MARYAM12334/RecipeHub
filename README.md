# Recipe Search System 🍳

## Table des matières
- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)

## Vue d'ensemble
Recipe Search System est une application web moderne permettant aux utilisateurs de rechercher des recettes de cuisine à partir de fichiers PDF indexés.
L'application utilise un backend Python avec Flask pour l'indexation et la recherche, et un frontend React pour l'interface utilisateur.

## Fonctionnalités
- 📄 Indexation de fichiers PDF contenant des recettes
- 🔍 Recherche rapide et efficace dans les recettes indexées
- 💡 Suggestions de recherche intelligentes
- 📱 Interface responsive et moderne
- 🎯 Résultats de recherche pertinents avec système de score

## Prérequis
### Backend
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Frontend
- Node.js 14.x ou supérieur
- npm 6.x ou supérieur

## Installation

### Configuration du Backend

1. Clonez le dépôt et accédez au dossier du backend :
```bash
git clone https://github.com/MARYAM12334/RecipeHub.git
cd recipe-search-engine/backend
```

2. Créez et activez un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
# ou
venv\Scripts\activate  # Sur Windows
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```
Note : Si cette commande ne fonctionne pas, vous pouvez installer les dépendances individuellement :
```bash 
pip install Flask
pip install Flask-Cors
pip install pymupdf
pip install rapidfuzz
```

4. Démarrez le serveur :
```bash
python file_indexing_server.py
```

### Configuration du Frontend

1. Accédez au dossier frontend :
```bash
cd ../frontend
```

2. Installez les dépendances :
```bash
npm install
```

3. Lancez l'application en mode développement :
```bash
npm start
```

## Structure du projet
```
RecipeSearchSystem/
├── backend/
│   ├── venv/                   # Environnement virtuel Python
│   ├── file_indexing_server.py # Serveur Flask
│   └── requirements.txt        # Dépendances Python
├── frontend/
│   ├── public/                 # Fichiers publics
│   ├── src/                    # Code source React
│   │   ├── components/         # Composants React
│   │   ├── pages/             # Pages de l'application
│   │   ├── App.js             # Composant principal
│   │   └── index.js           # Point d'entrée
│   ├── package.json           # Configuration NPM
│   ├── tailwind.config.js     # Configuration Tailwind
│   └── postcss.config.js      # Configuration PostCSS
└── README.md
```
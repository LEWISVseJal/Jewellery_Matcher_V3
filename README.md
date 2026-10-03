# JewelMatch AI

JewelMatch AI is a jewellery visual similarity matching system that
compares an uploaded jewellery image against a catalogue and returns
visually similar designs.

## Current status

The current working system includes:

-   Flask/Python backend
-   React + Vite web frontend
-   DINOv2-based visual embeddings
-   Gold and Prototype catalogues
-   Visual similarity search
-   Cross-collection search modes
-   Catalogue browsing and management
-   Add Jewellery
-   Browser camera capture
-   Catalogue index rebuilding
-   Local development setup
-   Render backend deployment configuration

Android application, production authentication, production database
migration, and other larger-scope items are future work unless
implemented separately.

## Project structure

``` text
Jewellery_Matcher/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── catalogue/
│   │   ├── gold/
│   │   └── prototype/
│   ├── database/
│   │   ├── jewellery.json
│   │   ├── dino_index.npz
│   │   └── lightweight_index.npz
│   ├── scripts/
│   │   ├── create_dino_index.py
│   │   ├── create_embeddings.py
│   │   └── create_lightweight_index.py
│   └── services/
│       ├── catalogue.py
│       ├── embedding.py
│       ├── matcher.py
│       └── segmentation.py
└── frontend/
    ├── static/
    ├── templates/
    └── react/
        ├── package.json
        ├── index.html
        ├── .env
        └── src/
            ├── main.jsx
            ├── App.jsx
            ├── components/
            │   ├── Header.jsx
            │   ├── SearchModeSelector.jsx
            │   ├── ImageUpload.jsx
            │   ├── CameraModal.jsx
            │   ├── SearchResults.jsx
            │   └── CatalogueCard.jsx
            ├── pages/
            │   ├── SearchPage.jsx
            │   ├── CataloguePage.jsx
            │   └── AddJewelleryPage.jsx
            ├── services/
            │   └── api.js
            └── styles/
                ├── global.css
                ├── search.css
                ├── catalogue.css
                └── add-jewellery.css
```

## Requirements

### Backend

-   Windows
-   Python 3.11+
-   64-bit Python
-   Virtual environment
-   Flask and packages in `backend/requirements.txt`
-   PyTorch CPU build
-   OpenCV
-   Transformers
-   Pillow
-   NumPy

The current development machine uses Python 3.11.9, 64-bit Windows and
PyTorch 2.14.1+cpu.

### Frontend

-   Node.js current LTS
-   npm
-   React
-   Vite
-   React Router

## Backend setup

From the project root:

``` powershell
cd "C:\Users\SEJAL LEWIS\Pictures\Projects\JewelleryMatcher_v2\Jewellery_Matcher"
```

Create the virtual environment if needed:

``` powershell
python -m venv venv
```

Activate it:

``` powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

``` powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

If PyTorch is missing:

``` powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Test PyTorch:

``` powershell
python -c "import torch; print('Torch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

For a CPU installation, `CUDA: False` is expected.

## Start the backend

From the project root:

``` powershell
python -m backend.app
```

Backend:

``` text
http://127.0.0.1:5000
```

Health check:

``` text
http://127.0.0.1:5000/api/health
```

A 404 at `/` is not a backend failure if the API health route works.

## Frontend setup

Open a second PowerShell window:

``` powershell
cd "C:\Users\SEJAL LEWIS\Pictures\Projects\JewelleryMatcher_v2\Jewellery_Matcher\frontend\react"
```

Check Node and npm:

``` powershell
node -v
npm -v
```

Install packages:

``` powershell
npm install
```

Start Vite:

``` powershell
npm run dev
```

Frontend:

``` text
http://localhost:5173
```

## Frontend API configuration

File:

``` text
frontend/react/.env
```

Local development:

``` env
VITE_API_BASE_URL=http://127.0.0.1:5000
```

Render backend:

``` env
VITE_API_BASE_URL=https://jewellery-matcher-docker-v2.onrender.com
```

Restart Vite after changing `.env`.

## Main pages

### Search

Route:

``` text
/
```

Features:

-   Image upload
-   Drag and drop
-   Browse image
-   Browser camera capture
-   Search mode selection
-   Visual matching
-   Similarity display
-   Collection/type information
-   Responsive layout

### Catalogue

Route:

``` text
/catalogue
```

Features:

-   Total Designs
-   Gold count
-   Prototype count
-   Search
-   Gold/Prototype filters
-   Catalogue cards
-   View
-   Edit
-   Delete
-   Rebuild Search Index

### Add Jewellery

Route:

``` text
/add-jewellery
```

Features:

-   Image upload
-   Drag and drop
-   Camera capture
-   Jewellery name
-   Collection
-   Jewellery type
-   Description
-   API submission
-   Backend catalogue update

Gender and Subtype have been removed from the new Add Jewellery form.

## Search modes

### Search from All

``` text
all
```

Searches Gold and Prototype.

### Gold -\> Prototype

``` text
gold_to_prototype
```

Searches Prototype using a Gold query.

### Prototype -\> Gold

``` text
prototype_to_gold
```

Searches Gold using a Prototype query.

These modes support cross-material visual matching.

## Jewellery type options

The new Add Jewellery form has exactly these 25 options:

1.  LP
2.  GP
3.  LAD
4.  GAD
5.  SSL
6.  SSG
7.  WB
8.  EMROLD
9.  KACHUWA TORTOISE
10. CHALA MIX
11. OMP
12. GF
13. FOTO
14. LBR
15. GBR
16. PENDELS
17. HIGHPOLISHCHARMS
18. CUTTING CHARMS
19. LCH
20. SIMBA
21. LETTERS
22. OMRING
23. RAJMUDRA
24. OTHERS EXTRA
25. GCH

## Catalogue data

Main catalogue file:

``` text
backend/database/jewellery.json
```

The current catalogue includes the existing Prototype and Gold records,
including J001-J016, J017-J031 and GOLD0001.

The new catalogue structure focuses on:

``` json
{
  "id": "J001",
  "name": "Prototype8657",
  "type": "GP",
  "collection": "Prototype",
  "description": "",
  "image": "J001.jpeg"
}
```

Legacy Gender and Subtype fields have been removed from the cleaned
catalogue data. Existing records that still have the old `Ring` type can
be classified into the new 25-type system later when the correct
business type is known.

## Visual matching

The main visual embedding model is:

``` text
facebook/dinov2-base
```

DINOv2 produces 768-dimensional embeddings.

The current DINO index contains:

``` text
Total images: 31
Gold images: 15
Prototype images: 16
Embedding dimension: 768
```

Index:

``` text
backend/database/dino_index.npz
```

The index contains embeddings and catalogue metadata such as IDs,
collections, image paths and design IDs.

Additional matching/verification features in the backend include:

-   Image segmentation
-   Shape descriptors
-   Edge information
-   ORB local feature matching
-   Candidate selection
-   Visual similarity verification

The goal is to emphasize jewellery structure and design rather than
simply matching colour.

## Index rebuilding

The backend provides:

``` http
POST /api/rebuild-index
```

The Catalogue page exposes this as:

``` text
Rebuild Search Index
```

Rebuild the index after catalogue changes when required.

## Backend API

``` text
GET    /api/health
POST   /api/match
GET    /api/catalogue
GET    /api/catalogue/<id>
POST   /api/jewellery/add
POST   /api/jewellery/<id>
DELETE /api/jewellery/<id>
POST   /api/rebuild-index
GET    /catalogue-image/<collection>/<filename>
```

`POST /api/match` accepts the uploaded image and search mode.

The current Add/Edit metadata focuses on:

``` text
name
collection
type
description
```

## Camera support

The Search page provides a browser camera workflow:

1.  Open camera.
2.  Grant camera permission.
3.  Preview the live camera stream.
4.  Capture an image.
5.  Use the captured image for matching.

The Add Jewellery page also supports camera capture on supported mobile
browsers.

## Current implemented features

-   [x] Flask backend
-   [x] React frontend
-   [x] Vite setup
-   [x] Gold catalogue
-   [x] Prototype catalogue
-   [x] JSON catalogue
-   [x] DINOv2 embeddings
-   [x] DINO search index
-   [x] Visual similarity matching
-   [x] Cross-collection matching
-   [x] Search from All
-   [x] Gold -\> Prototype
-   [x] Prototype -\> Gold
-   [x] Image upload
-   [x] Drag-and-drop upload
-   [x] Browser camera capture
-   [x] Search results
-   [x] Similarity information
-   [x] Catalogue page
-   [x] Catalogue search
-   [x] Collection filters
-   [x] Catalogue statistics
-   [x] Add Jewellery
-   [x] Edit Jewellery API
-   [x] Delete Jewellery API
-   [x] Rebuild Search Index API
-   [x] React-to-Flask API connection
-   [x] Responsive web UI
-   [x] Gender removed from new Add Jewellery form
-   [x] Subtype removed from new Add Jewellery form
-   [x] 25 new jewellery type options

## Future work / not yet part of the current working implementation

-   [ ] Android application
-   [ ] Production authentication
-   [ ] User accounts
-   [ ] Admin authentication/authorization
-   [ ] Full production admin dashboard
-   [ ] Production database migration from JSON
-   [ ] Cloud image/object storage
-   [ ] Production React deployment
-   [ ] Production optimization for DINOv2 memory usage
-   [ ] Larger real-world jewellery dataset
-   [ ] Classification of all legacy `Ring` records into the new 25
    types
-   [ ] Production monitoring and logging
-   [ ] Final deployment and handover configuration

## GitHub workflow

Check status:

``` powershell
git status
```

Add changes:

``` powershell
git add .
```

Commit:

``` powershell
git commit -m "Update JewelMatch AI frontend and backend"
```

Push:

``` powershell
git push origin main
```

Do not commit:

``` text
venv/
node_modules/
__pycache__/
.env
```

These should be included in `.gitignore`.

## Recommended daily workflow

### Terminal 1 - Flask

``` powershell
cd "C:\Users\SEJAL LEWIS\Pictures\Projects\JewelleryMatcher_v2\Jewellery_Matcher"
.\venv\Scripts\Activate.ps1
python -m backend.app
```

### Terminal 2 - React

``` powershell
cd "C:\Users\SEJAL LEWIS\Pictures\Projects\JewelleryMatcher_v2\Jewellery_Matcher\frontend\react"
npm run dev
```

Open:

``` text
http://localhost:5173
```

Recommended test order:

``` text
Search
  ↓
Catalogue
  ↓
Add Jewellery
  ↓
Edit
  ↓
Delete
  ↓
Rebuild Search Index
  ↓
Search again
```

## Application architecture

``` text
React Frontend
http://localhost:5173
        |
        | HTTP API
        v
Flask Backend
http://127.0.0.1:5000
        |
        +-------------------+
        |                   |
        v                   v
Catalogue Service       Matcher Service
                            |
                            v
                      Embedding Service
                            |
                            v
                         DINOv2
                            |
                            v
                    Search Index / NPZ
```

## Render backend

The backend has previously been deployed to:

``` text
https://jewellery-matcher-docker-v2.onrender.com
```

The React frontend can use this backend by setting:

``` env
VITE_API_BASE_URL=https://jewellery-matcher-docker-v2.onrender.com
```

The deployed backend should be tested independently before using it as
the production API.

## Important notes

-   Start Flask with `python -m backend.app`, not by directly executing
    `app.py`.
-   Keep the backend terminal running while testing the React frontend.
-   Keep the frontend terminal running while using the web application.
-   Use the local `/api/health` endpoint to verify the backend.
-   Rebuild the search index after catalogue changes when required.
-   Do not modify the matcher/embedding code just to fix frontend
    startup issues.
-   Keep the React frontend and Flask backend API contracts
    synchronized.

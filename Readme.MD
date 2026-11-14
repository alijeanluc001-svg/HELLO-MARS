# HELLO HELLO — Mars Navigation

```
mars-navigation/
├── app.py              Flask backend (sites, route planner)
├── requirements.txt
├── setup_assets.py     one-time download of JS libs, NASA tiles, globe texture
├── templates/
│   └── index.html      the whole interface
└── static/             created by setup_assets.py
```

## Run it (VS Code → Terminal → New Terminal)

Windows (PowerShell):
```
cd mars-navigation
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup_assets.py
python app.py
```
macOS / Linux:
```
cd mars-navigation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 setup_assets.py
python3 app.py
```
Open http://127.0.0.1:5000

`setup_assets.py` needs internet once. After that the site works offline (3D globe, and the 2D map up to zoom 4).
For deeper offline zoom: `python setup_assets.py 5`.

## Troubleshooting
- PowerShell blocks activation: `Set-ExecutionPolicy -Scope Process Bypass`, then activate again.
- Black screen / red banner at the top: press F12 → Console and send the message. Hard-refresh with Ctrl+Shift+R.
- "three.min.js introuvable": rerun `python setup_assets.py`.
- Port 5000 busy (macOS AirPlay): change `port=5000` to `port=5001` at the bottom of app.py.
- Terrain hazards are SIMULATED (see notice on the page). Real data: replace `hz()` in app.py with MOLA/HiRISE slopes.

Credits: NASA/JPL-Caltech, USGS Astrogeology (Viking MDIM 2.1, MOLA), Three.js, Leaflet.
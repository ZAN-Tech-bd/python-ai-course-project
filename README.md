# Python to AI — Course Projects

A collection of projects built while working through a Python-to-AI bootcamp,
ranging from terminal fundamentals to pygame games and machine-learning /
AI applications.

## Projects

### AI / Machine Learning

| Project | Description |
|---|---|
| [AI chat bot](<AI chat bot>) | Bilingual (Bangla + English) RAG chatbot — TF-IDF retrieval over a JSON knowledge base, with optional Gemini API refinement. Streamlit UI. |
| [Draw in air](<Draw in air>) | Draw on-screen with just your fingertip via webcam hand tracking (OpenCV + MediaPipe) — 2D toolset plus a 3D freehand mode (PyOpenGL/pygame). |
| [Car sales prediction](<Car sales prediction>) | Terminal app that predicts a used car's selling price with a RandomForestRegressor trained on real CarDekho listing data. |
| [Rain prediction](<Rain prediction>) | Terminal tool that predicts rain for any city using the free Open-Meteo API — no signup or key required. |
| [Facial recognition](<Facial recognition>) | Placeholder — not yet implemented. |
| [AI voice assistance](<AI voice assistance>) | Placeholder — not yet implemented. |

### Games (pygame)

| Project | Description |
|---|---|
| [Bike Race](<Bike Race>) | Single-file arcade bike racer with nitro boost, pause, and restart. |
| [Care Rase](<Care Rase>) | Car racing game with acceleration, braking, nitro boost, and a high-score file. |
| [Dino run](<Dino run>) | Endless-runner clone of the Chrome offline dinosaur game. |
| [Flappy Bird](<Flappy Bird>) | Flappy Bird clone built with pygame. |
| [Snakes games](<Snakes games>) | Classic Snake with arrow key/WASD controls, pause, and restart. |
| [3D Environment](<3D Environment>) | Placeholder — not yet implemented. |

### Terminal & UI tools

| Project | Description |
|---|---|
| [ATM terminal](<ATM terminal>) | Simple terminal ATM simulator — PIN check, balance, deposit, withdraw. |
| [Calculator terminal](<Calculator terminal>) | Basic terminal calculator supporting +, -, *, /. |
| [Calculator with ui](<Calculator with ui>) | Calculator with a pygame-based graphical UI. |
| [Grading System](<Grading System>) | Terminal app for tracking student grades, backed by a JSON data file. |
| [Tik Tak tok game](<Tik Tak tok game>) | Terminal Tic-Tac-Toe — two-player and vs-computer modes. |

## Getting started

Each project lives in its own folder and is self-contained. Where a project
has its own `README.md` and `requirements.txt`, follow its instructions
directly, e.g.:

```bash
cd "AI chat bot"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Pygame-based games only require `pip install pygame` and can then be run
directly, e.g.:

```bash
cd "Snakes games"
pip install pygame
python snake_game.py
```

Simple terminal projects (ATM, Calculator terminal, Grading System, Tic-Tac-Toe)
have no dependencies beyond the Python standard library — just run the `.py`
file directly.

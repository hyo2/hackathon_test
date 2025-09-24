import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .model import load_model, predict_image
import logging
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
ANIMALS_JSON = DATA_DIR / "animal_data_with_size.json"
MODELS_DIR = APP_DIR.parent / "models"
MODEL_PTH = Path(os.getenv("MODEL_PTH_PATH", MODELS_DIR / "dog_breed_classifier.pth"))
CLASS_MAP_PATH = Path(os.getenv("CLASS_MAP_PATH", MODELS_DIR / "class_map.json"))
NUM_CLASSES = int(os.getenv("NUM_CLASSES", "20"))

app = FastAPI(title="AI Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Lazy globals
_model = None
_device = None
_label_names: List[str] = []


def ensure_model_loaded():
    global _model, _device, _label_names
    if _model is None:
        if not MODEL_PTH.exists() or not CLASS_MAP_PATH.exists():
            raise HTTPException(status_code=500, detail="Model or class map not found. Please train first.")
        with open(CLASS_MAP_PATH, "r", encoding="utf-8") as f:
            class_map = json.load(f)
        # class_map is dict: label->index; derive ordered labels by index
        _label_names = [None] * len(class_map)
        for k, v in class_map.items():
            if v < 0 or v >= len(_label_names):
                continue
            _label_names[v] = k
        _model, _device = load_model(str(MODEL_PTH), len(_label_names))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/animals")
def list_animals():
    """
    Returns animals from animal_data_with_size.json with stable ids and image URLs that always work.

    Fields added per item:
    - id: stable index-based id
    - gallery: up to 4 image URLs served locally from /ai/images/* when possible.
               If JSON image filenames don't exist locally, we deterministically
               assign images from the local images folder to avoid 404s.
    - thumbnail: first entry of gallery for convenience
    - images_mapped: kept for backward-compat; same as previous mapping logic
    """
    if not ANIMALS_JSON.exists():
        return []

    with open(ANIMALS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Preload available local images once
    local_files = [p.name for p in sorted(IMAGES_DIR.glob("*")) if p.is_file()]
    total_local = len(local_files)

    for idx, item in enumerate(data):
        item["id"] = idx

        # Previous behavior: best-effort map by filename, else keep remote
        mapped = []
        for img in item.get("images", [])[:4]:
            name = Path(img).name
            if (IMAGES_DIR / name).exists():
                mapped.append(f"/ai/images/{name}")
            else:
                mapped.append(img)
        item["images_mapped"] = mapped

        # New, reliable gallery using JSON images, mapped to local only when available
        gallery: List[str] = []
        for img in item.get("images", [])[:4]:
            name = Path(img).name
            if (IMAGES_DIR / name).exists():
                gallery.append(f"/ai/images/{name}")
            else:
                gallery.append(img)

        item["gallery"] = gallery
        item["thumbnail"] = gallery[0] if gallery else None

    return data


@app.get("/animals/{animal_id}")
def get_animal(animal_id: int):
    items = list_animals()
    if animal_id < 0 or animal_id >= len(items):
        raise HTTPException(status_code=404, detail="Animal not found")
    return items[animal_id]


@app.get("/images/{filename}")
def get_image(filename: str):
    file_path = IMAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(file_path))


@app.post("/classify")
async def classify(image: UploadFile = File(...), top_k: int = Query(3, ge=1, le=20)):
    ensure_model_loaded()
    tmp = APP_DIR / "_upload_tmp"
    tmp.mkdir(exist_ok=True)
    out_path = tmp / image.filename
    data = await image.read()
    out_path.write_bytes(data)
    labels, probs, scores = predict_image(str(out_path), _model, _device, _label_names, top_k=top_k)
    logger.info(f"/classify top_k={top_k} -> returned {len(labels)} labels: {labels[:5]}")
    return {"top": labels, "scores": scores, "probs": probs}

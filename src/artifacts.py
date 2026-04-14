# src/artifacts.py

import json
import os
from datetime import datetime

import torch


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_model_checkpoint(model, save_path: str, extra: dict | None = None):
    ensure_dir(os.path.dirname(save_path))

    payload = {
        "state_dict": model.state_dict(),
    }

    if extra is not None:
        payload["extra"] = extra

    torch.save(payload, save_path)


def load_model_checkpoint(model, checkpoint_path: str, map_location="cpu"):
    payload = torch.load(checkpoint_path, map_location=map_location)
    model.load_state_dict(payload["state_dict"])
    return model, payload.get("extra", {})


def save_json(data: dict, save_path: str):
    ensure_dir(os.path.dirname(save_path))
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def build_run_metadata(config_dict: dict, summary_dict: dict):
    return {
        "saved_at": datetime.now().isoformat(),
        "config": config_dict,
        "summary": summary_dict,
    }
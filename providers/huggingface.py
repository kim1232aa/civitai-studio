from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from .base import Provider
from .http import parse_job_id, raw_call, save_bytes

TOKEN_PATH = Path.home() / ".config/huggingface/token"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ROUTER = "https://router.huggingface.co/hf-inference/models"


def hf_key() -> str:
    try:
        t = TOKEN_PATH.read_text().strip()
        if t:
            return t
    except Exception:
        pass
    return (os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or "").strip()


def load_items():
    fp = DOCS / "hf-models.json"
    if not fp.exists():
        return []
    try:
        return json.loads(fp.read_text()).get("items") or []
    except Exception:
        return []


def model_id(service_id: str) -> str:
    s = (service_id or "").strip().lstrip("/")
    if s.startswith("hf/"):
        s = s[3:]
    if s.startswith("huggingface/"):
        s = s[len("huggingface/"):]
    return s


class HuggingFaceProvider(Provider):
    id = "huggingface"
    label = "Hugging Face"

    def has_key(self) -> bool:
        return bool(hf_key())

    def categories(self) -> list:
        return sorted({x.get("category") for x in load_items() if x.get("category")})

    def catalog(self, q, category, status) -> dict:
        qn = (q or "").lower()
        items = list(load_items())
        if category:
            items = [x for x in items if x.get("category") == category]
        if status:
            items = [x for x in items if x.get("status") == status]
        if qn:
            items = [x for x in items if qn in (x.get("name") or "").lower() or qn in (x.get("id") or "").lower()]
        return {
            "total": len(items),
            "count": len(items),
            "backend": "huggingface",
            "items": items,
            "hasKey": self.has_key(),
        }

    def owns_service(self, service_id: str) -> bool:
        sid = (service_id or "").strip()
        if not sid:
            return False
        if sid.startswith(("hf/", "huggingface/")):
            return True
        ids = {x.get("id") for x in load_items()}
        return sid in ids

    def owns_job(self, job_id: str) -> bool:
        pid, _ = parse_job_id(job_id)
        return pid in ("huggingface", "hf") or (job_id or "").startswith("hf|")

    def whatif(self, payload: dict):
        return 200, {
            "backend": "huggingface",
            "cost": {"total": None, "note": "Hugging Face Inference Providers 按次计费，无黄 Buzz 预估"},
            "service": {"serviceId": (payload or {}).get("serviceId")},
        }

    def generate(self, payload: dict):
        key = hf_key()
        if not key:
            return 401, {"error": "没有 Hugging Face API Key"}
        mid = model_id((payload or {}).get("serviceId") or "")
        if not mid:
            return 400, {"error": "缺少 Hugging Face 模型 id"}
        spec = next((x for x in load_items() if x.get("id") == mid), {}) or {}
        task = spec.get("task") or "text-to-image"
        params = {}
        if payload.get("negativePrompt"):
            if task == "text-to-video":
                params["negative_prompt"] = [payload["negativePrompt"]]
            else:
                params["negative_prompt"] = payload["negativePrompt"]
        if payload.get("steps"):
            try:
                params["num_inference_steps"] = int(payload["steps"])
            except (TypeError, ValueError):
                pass
        if payload.get("cfgScale") not in (None, ""):
            try:
                params["guidance_scale"] = float(payload["cfgScale"])
            except (TypeError, ValueError):
                pass
        if payload.get("width"):
            try:
                params["width"] = int(payload["width"])
            except (TypeError, ValueError):
                pass
        if payload.get("height"):
            try:
                params["height"] = int(payload["height"])
            except (TypeError, ValueError):
                pass
        if payload.get("seed") not in (None, "", "random"):
            try:
                params["seed"] = int(payload["seed"])
            except (TypeError, ValueError):
                pass
        if task == "text-to-video" and payload.get("duration"):
            try:
                params["num_frames"] = max(8, int(payload["duration"]) * 8)
            except (TypeError, ValueError):
                pass
        body = {"inputs": payload.get("prompt") or ""}
        if params:
            body["parameters"] = params
        accept = "video/mp4" if task == "text-to-video" else "image/png"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": accept,
        }
        code, raw, ctype = raw_call(f"{ROUTER}/{mid}", method="POST", headers=headers, body=body, timeout=180)
        if code == 503:
            return 503, {"error": "模型正在加载，请稍后再试"}
        if code >= 400:
            try:
                parsed = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                parsed = {"error": raw[:500].decode("utf-8", "replace")}
            if isinstance(parsed, dict):
                parsed.setdefault("error", parsed.get("error") or parsed.get("message") or f"HTTP {code}")
            return code, parsed
        if (ctype or "").startswith("application/json"):
            try:
                parsed = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                parsed = {"error": "无法解析 Hugging Face 响应"}
            return code, parsed if isinstance(parsed, dict) else {"error": str(parsed)}
        jid = f"hf|sync|{uuid.uuid4().hex[:12]}"
        saved = save_bytes(raw, jid)
        return 200, {
            "id": jid,
            "status": "succeeded",
            "backend": "huggingface",
            "endpoint": mid,
            "saved": saved,
            "submittedInput": body,
        }

    def job_status(self, job_id: str):
        # sync jobs finish in generate(); nothing to poll
        return 200, {"id": job_id, "status": "succeeded", "backend": "huggingface", "wait": {"progress": 1, "precedingJobs": None, "etaSeconds": None, "completeAt": None, "log": None}}


from . import register  # noqa: E402

register(HuggingFaceProvider())

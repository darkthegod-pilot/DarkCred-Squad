import json
from datetime import datetime
from pathlib import Path


def save_output(
    variations: list[dict],
    segment_key: str,
    output_dir: str = "output",
    fmt: str = "both",
) -> dict[str, str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{output_dir}/darkcred_{segment_key}_{timestamp}"
    saved = {}

    if fmt in ("json", "both"):
        json_path = base_name + ".json"
        payload = {
            "segment": segment_key,
            "generated_at": timestamp,
            "count": len(variations),
            "variations": variations,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        saved["json"] = json_path

    if fmt in ("text", "both"):
        txt_path = base_name + ".txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"DarkCred — Segmento: {segment_key} — {timestamp}\n")
            f.write("=" * 50 + "\n\n")
            for i, var in enumerate(variations, 1):
                f.write(f"--- Variação {i} ---\n")
                f.write(var.get("full_copy", "") + "\n\n")
        saved["text"] = txt_path

    return saved

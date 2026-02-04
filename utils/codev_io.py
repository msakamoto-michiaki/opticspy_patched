from pathlib import Path
from typing import Optional

def find_seq_path(seq_name: str, start_dir: Optional[str] = None) -> str:
    """
    seq_name（例: 'petzval.seq'）を、よくある配置候補から探索してパスを返す。
    見つからなければ FileNotFoundError。
    """
    base = Path(start_dir).resolve() if start_dir else Path.cwd().resolve()

    candidates = [
        base / seq_name,
        base / "CodeV_examples" / seq_name,
        base / "opticspy" / "ray_tracing" / "CodeV_examples" / seq_name,
        base.parent / "CodeV_examples" / seq_name,
    ]

    for p in candidates:
        if p.exists():
            return str(p)

    raise FileNotFoundError(f"seq file not found: {seq_name} (searched: {candidates})")

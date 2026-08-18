"""AutoStudy 최초 설정 도우미.

사용자별 비밀값을 .env에 저장하고 Colab의 Drive 작업 경로를 맞춘다.
이 파일은 Python 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict

CHOBO_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CHOBO_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"
CREDENTIALS_PATH = PROJECT_DIR / "credentials.json"
COLAB_NOTEBOOK_PATH = PROJECT_DIR / "colab" / "Transcribe.ipynb"
REQUIRED_KEYS = (
    "API_KEY",
    "NOTION_TOKEN",
    "NOTION_DATABASE_ID",
    "NOTION_DATA_SOURCE_ID",
    "WATCH_PATH",
    "COLAB_FOLDER_PATH",
)


def read_env(path: Path = ENV_PATH) -> Dict[str, str]:
    """Read a simple .env file without printing private values."""
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def safe_env_value(value: str) -> str:
    """Reject line breaks so a form value cannot alter another .env setting."""
    if "\n" in value or "\r" in value:
        raise ValueError("입력값에는 줄바꿈을 넣을 수 없습니다.")
    return value.strip()


def write_env(values: Dict[str, str]) -> None:
    lines = [
        "# AutoStudy 개인 설정 파일 — 절대로 공유하거나 GitHub에 올리지 마세요.",
        "# Gemini API 키와 Notion 토큰은 비밀번호와 같은 비밀정보입니다.",
        f"API_KEY={safe_env_value(values['API_KEY'])}",
        f"NOTION_TOKEN={safe_env_value(values['NOTION_TOKEN'])}",
        f"NOTION_DATABASE_ID={safe_env_value(values['NOTION_DATABASE_ID'])}",
        f"NOTION_DATA_SOURCE_ID={safe_env_value(values['NOTION_DATA_SOURCE_ID'])}",
        f"WATCH_PATH={safe_env_value(values['WATCH_PATH'])}",
        f"COLAB_FOLDER_PATH={safe_env_value(values['COLAB_FOLDER_PATH'])}",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def ensure_work_folders(watch_path: str) -> None:
    root = Path(watch_path).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    (root / "lecture").mkdir(exist_ok=True)
    (root / "merged").mkdir(exist_ok=True)


def update_colab_folder_path(colab_folder_path: str) -> int:
    """Replace both hard-coded Colab work-folder assignments in the notebook."""
    if not COLAB_NOTEBOOK_PATH.exists():
        raise FileNotFoundError("colab/Transcribe.ipynb 파일을 찾을 수 없습니다.")

    notebook = json.loads(COLAB_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    replacement = f'folder_path = "{colab_folder_path}"'
    pattern = re.compile(r'folder_path\s*=\s*["\'][^"\']*["\']')
    replacements = 0

    for cell in notebook.get("cells", []):
        source = cell.get("source", [])
        joined = "".join(source) if isinstance(source, list) else source
        updated, count = pattern.subn(replacement, joined)
        if count:
            replacements += count
            cell["source"] = updated.splitlines(keepends=True) if isinstance(source, list) else updated

    if replacements == 0:
        raise RuntimeError("Colab 노트북에서 folder_path 설정을 찾지 못했습니다.")

    COLAB_NOTEBOOK_PATH.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    return replacements


def validation_errors(values: Dict[str, str]) -> list[str]:
    errors = []
    missing = [key for key in REQUIRED_KEYS if not values.get(key, "").strip()]
    if missing:
        errors.append("비어 있는 설정: " + ", ".join(missing))
    watch_path = values.get("WATCH_PATH", "").strip()
    if watch_path and not Path(watch_path).exists():
        errors.append("작업 폴더가 존재하지 않습니다: WATCH_PATH")
    colab_path = values.get("COLAB_FOLDER_PATH", "").strip()
    if colab_path and not colab_path.startswith("/content/drive/"):
        errors.append("Colab 경로는 /content/drive/ 로 시작해야 합니다.")
    if not CREDENTIALS_PATH.exists():
        errors.append("프로그램 폴더에 credentials.json이 없습니다.")
    return errors


def check_configuration() -> int:
    values = read_env()
    errors = validation_errors(values)
    if errors:
        print("[AutoStudy 설정 확인] 아직 실행할 준비가 되지 않았습니다.")
        for error in errors:
            print(f"- {error}")
        print("chobo 폴더의 설정_변경하기.cmd를 실행해 설정을 저장하세요.")
        return 1

    print("[AutoStudy 설정 확인] 실행에 필요한 기본 설정을 확인했습니다.")
    print("작업 폴더:", values["WATCH_PATH"])
    return 0


def launch_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print("설정 창을 열 수 없습니다. Windows용 Python을 다시 설치해 주세요.")
        return 1

    existing = read_env()
    root = tk.Tk()
    root.title("AutoStudy 처음 설정하기")
    root.geometry("780x760")
    root.minsize(700, 650)

    outer = ttk.Frame(root, padding=20)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(1, weight=1)

    intro = (
        "이 창은 작업 폴더와 비밀 설정을 이 컴퓨터의 .env 파일에만 저장합니다.\n"
        "API 키와 Notion 토큰은 다른 사람에게 보여 주거나 전송하지 마세요."
    )
    ttk.Label(outer, text=intro, justify="left", wraplength=720).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
    )

    fields = [
        ("작업 폴더 (WATCH_PATH)", "WATCH_PATH", "Google Drive 안의 AutoStudy 작업 폴더를 선택하세요."),
        ("Google Colab 폴더 경로", "COLAB_FOLDER_PATH", "/content/drive/MyDrive/AutoStudy 형식으로 입력하세요."),
        ("Gemini API 키", "API_KEY", "Google AI Studio에서 만든 키 전체를 붙여 넣으세요."),
        ("Notion 토큰", "NOTION_TOKEN", "Notion Developer Portal의 Personal Access Token입니다."),
        ("Notion 데이터베이스 ID", "NOTION_DATABASE_ID", "강의 결과를 저장할 전체 페이지 데이터베이스의 ID입니다."),
        ("Notion 데이터 소스 ID", "NOTION_DATA_SOURCE_ID", "Manage data sources에서 복사한 ID입니다."),
    ]
    variables: Dict[str, tk.StringVar] = {}
    descriptions: Dict[str, str] = {}

    for index, (label, key, description) in enumerate(fields, start=1):
        variables[key] = tk.StringVar(value=existing.get(key, ""))
        descriptions[key] = description
        ttk.Label(outer, text=label).grid(row=index * 2 - 1, column=0, sticky="w", pady=(7, 0))
        show_value = "*" if key in {"API_KEY", "NOTION_TOKEN"} else ""
        entry = ttk.Entry(outer, textvariable=variables[key], show=show_value)
        entry.grid(row=index * 2 - 1, column=1, sticky="ew", padx=(12, 8), pady=(7, 0))
        if key == "WATCH_PATH":
            def choose_folder() -> None:
                selected = filedialog.askdirectory(title="Google Drive AutoStudy 작업 폴더 선택")
                if selected:
                    variables["WATCH_PATH"].set(selected)
                    if not variables["COLAB_FOLDER_PATH"].get().strip():
                        variables["COLAB_FOLDER_PATH"].set("/content/drive/MyDrive/AutoStudy")
            ttk.Button(outer, text="폴더 선택", command=choose_folder).grid(
                row=index * 2 - 1, column=2, sticky="e", pady=(7, 0)
            )
        ttk.Label(outer, text=description, foreground="#555555", wraplength=680).grid(
            row=index * 2, column=0, columnspan=3, sticky="w", pady=(1, 4)
        )

    credentials_var = tk.StringVar(value=str(CREDENTIALS_PATH) if CREDENTIALS_PATH.exists() else "")
    credentials_row = len(fields) * 2 + 1
    ttk.Label(outer, text="Google Drive credentials.json").grid(row=credentials_row, column=0, sticky="w", pady=(7, 0))
    ttk.Entry(outer, textvariable=credentials_var).grid(row=credentials_row, column=1, sticky="ew", padx=(12, 8), pady=(7, 0))

    def choose_credentials() -> None:
        selected = filedialog.askopenfilename(
            title="Google Drive OAuth credentials.json 선택",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )
        if selected:
            credentials_var.set(selected)

    ttk.Button(outer, text="파일 선택", command=choose_credentials).grid(
        row=credentials_row, column=2, sticky="e", pady=(7, 0)
    )
    ttk.Label(
        outer,
        text="Google Cloud에서 Desktop app 유형으로 내려받은 OAuth JSON 파일입니다. 선택하면 프로그램 폴더에 credentials.json으로 복사됩니다.",
        foreground="#555555",
        wraplength=680,
    ).grid(row=credentials_row + 1, column=0, columnspan=3, sticky="w", pady=(1, 16))

    def save() -> None:
        values = {key: var.get().strip() for key, var in variables.items()}
        empty_keys = [key for key in REQUIRED_KEYS if not values.get(key)]
        if empty_keys:
            messagebox.showerror("입력 확인", "다음 항목을 모두 입력하세요:\n" + "\n".join(empty_keys))
            return
        if not values["COLAB_FOLDER_PATH"].startswith("/content/drive/"):
            messagebox.showerror("Colab 경로 확인", "Colab 경로는 /content/drive/ 로 시작해야 합니다.")
            return

        source_credentials = Path(credentials_var.get().strip())
        if not source_credentials.exists() or source_credentials.suffix.lower() != ".json":
            messagebox.showerror("credentials.json 확인", "Google Drive OAuth JSON 파일을 선택하세요.")
            return

        try:
            ensure_work_folders(values["WATCH_PATH"])
            if source_credentials.resolve() != CREDENTIALS_PATH.resolve():
                shutil.copy2(source_credentials, CREDENTIALS_PATH)
            write_env(values)
            replacements = update_colab_folder_path(values["COLAB_FOLDER_PATH"])
        except Exception as exc:
            messagebox.showerror("저장 실패", f"설정을 저장하지 못했습니다.\n\n{exc}")
            return

        messagebox.showinfo(
            "설정 완료",
            "설정을 저장했습니다.\n\n"
            f"작업 폴더에 lecture·merged 폴더를 만들었고, Colab 경로 {replacements}곳을 갱신했습니다.\n\n"
            "이제 AutoStudy_실행.cmd를 더블클릭해 첫 실행을 시작하세요.",
        )
        root.destroy()

    actions = ttk.Frame(outer)
    actions.grid(row=credentials_row + 2, column=0, columnspan=3, sticky="e", pady=(6, 0))
    ttk.Button(actions, text="취소", command=root.destroy).pack(side="right")
    ttk.Button(actions, text="설정 저장하기", command=save).pack(side="right", padx=(0, 8))

    root.mainloop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoStudy 최초 설정 도우미")
    parser.add_argument("--check", action="store_true", help="설정 상태만 확인하고 창은 열지 않습니다.")
    args = parser.parse_args()
    return check_configuration() if args.check else launch_gui()


if __name__ == "__main__":
    sys.exit(main())

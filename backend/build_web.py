"""Build the Expo web frontend into the combined deployment's public directory."""

import os
import shutil
import subprocess
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = BACKEND_DIR.parent
PUBLIC_DIR = REPOSITORY_DIR / "public"
EXPORT_DIR = REPOSITORY_DIR / ".expo-vercel-build"


def command(name: str) -> str:
    return f"{name}.cmd" if os.name == "nt" else name


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main() -> None:
    build_env = os.environ.copy()
    # The deployed web app calls the FastAPI function on its own origin.
    # Local development keeps using the root .env value instead.
    build_env["EXPO_NO_DOTENV"] = "1"
    build_env["EXPO_PUBLIC_API_BASE_URL"] = ""

    # Vercel may not install the Node dependency tree for a FastAPI project.
    # Install only when Expo is unavailable, so local builds and platforms
    # that already installed package.json dependencies do not install twice.
    if not (REPOSITORY_DIR / "node_modules" / "expo" / "package.json").is_file():
        run(command("npm"), "ci", cwd=REPOSITORY_DIR, env=build_env)
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    # Expo copies everything in public/ into the export, so an old build there
    # would end up in the new one (the page would load two copies of the app).
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
    run(
        command("npx"),
        "expo",
        "export",
        "--platform",
        "web",
        "--output-dir",
        str(EXPORT_DIR.relative_to(REPOSITORY_DIR)),
        cwd=REPOSITORY_DIR,
        env=build_env,
    )
    shutil.copytree(EXPORT_DIR, PUBLIC_DIR)
    shutil.rmtree(EXPORT_DIR)


if __name__ == "__main__":
    main()

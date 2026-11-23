"""Build the Expo web frontend into web/, which the FastAPI app serves."""

import os
import shutil
import subprocess
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = BACKEND_DIR.parent
# Not public/: for a FastAPI project Vercel neither serves public/ as static files
# nor packs it into the function, so a build written there never reaches the site.
WEB_DIR = REPOSITORY_DIR / "web"
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
    if WEB_DIR.exists():
        shutil.rmtree(WEB_DIR)
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
    shutil.copytree(EXPORT_DIR, WEB_DIR)
    shutil.rmtree(EXPORT_DIR)


if __name__ == "__main__":
    main()

"""
Uso: python3 spotDL_wrapper.py <file_urls.txt> [directory_output] [opzioni]

Esempi:
  python3 spotDL_wrapper.py urls.txt
  python3 spotDL_wrapper.py urls.txt ~/Music/Spotify
  python3 spotDL_wrapper.py urls.txt ~/Music/Spotify --organize
  python3 spotDL_wrapper.py urls.txt ~/Music --overwrite force
  python3 spotDL_wrapper.py urls.txt ~/Music --bulk
  python3 spotDL_wrapper.py urls.txt ~/Music --bulk --cooldown 30 --cooldown-jitter 5
  python3 spotDL_wrapper.py urls.txt ~/Music --bulk --retries 5
"""

import argparse
import random
import subprocess
import sys
import time
from pathlib import Path


#  Costanti
SUPPORTED_DOMAINS = (
    "open.spotify.com",
    "spotify.com",
)

URL_TYPES = {
    "album":    "Album",
    "artist":   "Artista (discografia completa)",
    "playlist": "Playlist",
    "track":    "Singola traccia",
}

OVERWRITE_MODES = ("skip", "metadata", "force")

DEFAULT_RETRIES        = 3
DEFAULT_COOLDOWN       = 20   # secondi tra un URL e l'altro (bulk mode)
DEFAULT_COOLDOWN_JITTER = 2   # +- secondi di jitter casuale


#  lettura URL dal file
def load_urls(filepath: Path) -> list[str]:
    """Legge il file di testo e restituisce una lista di URL validi."""
    if not filepath.exists():
        print(f"[ERRORE] File non trovato: {filepath}")
        sys.exit(1)

    urls = []
    with filepath.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):   # righe vuote / commenti
                continue
            if not any(domain in line for domain in SUPPORTED_DOMAINS):
                print(f"[AVVISO] Riga {lineno}: URL non Spotify ignorato → {line}")
                continue
            urls.append(line)

    if not urls:
        print("[ERRORE] Nessun URL Spotify valido trovato nel file.")
        sys.exit(1)

    return urls


#  classificazione URL
def classify_url(url: str) -> str:
    for key in URL_TYPES:
        if f"/{key}/" in url:
            return key
    return "unknown"


#  Costruzione comando spotDL
def build_spotdl_command(url: str, output_dir: Path, organize: bool, overwrite: str,) -> list[str]:
    """Costruisce la lista di argomenti per spotdl."""
    cmd = ["spotdl", "download", url]

    # ── Directory di output ──────────────────
    if organize:
        output_template = str(output_dir / "{artist}" / "{album}" / "{title}.{output-format}")
    else:
        output_template = str(output_dir / "{title}.{output-format}")

    cmd += ["--output", output_template]

    # ── Modalità overwrite ───────────────────
    cmd += ["--overwrite", overwrite]

    return cmd


#  Cooldown visivo figo
def cooldown(base: float, jitter: float) -> None:
    """Attende base +- jitter secondi con countdown a schermo."""
    wait = base + random.uniform(-jitter, jitter)
    wait = max(0.0, wait)
    print(f"\n  Cooldown bulk: attendo {wait:.1f}s prima del prossimo URL...")
    end = time.monotonic() + wait
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            break
        print(f"\r     {remaining:.0f}s rimanenti...  ", end="", flush=True)
        time.sleep(min(1.0, remaining))
    print("\r     Pronto.                    ")


#  Download di un singolo URL (con retry manuale)
def download_one(url: str, idx: int, total: int, output_dir: Path, organize: bool, overwrite: str, retries: int,) -> bool:
    """Tenta il download di url. True ha successo."""
    kind  = classify_url(url)
    label = URL_TYPES.get(kind, "Sconosciuto")
    pfx   = f"[{idx}/{total}]"

    print(f"\n{pfx} -> {label}")
    print(f"{pfx}   {url}")

    cmd = build_spotdl_command(url, output_dir, organize, overwrite)
    print(f"{pfx}   Comando: {' '.join(cmd)}")

    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(cmd, check=False)
        except FileNotFoundError:
            print("\n[ERRORE FATALE] 'spotdl' non trovato nel PATH.")
            print("Installalo con:  pip install spotdl (nell'enviroment)")
            sys.exit(2)

        if result.returncode == 0:
            print(f"{pfx} ✓ Completato (tentativo {attempt}/{retries}).")
            return True

        print(f"{pfx} ✗ Errore (exit {result.returncode}) — tentativo {attempt}/{retries}.")
        if attempt < retries:
            backoff = 5 * attempt
            print(f"{pfx}   Riprovo tra {backoff}s...")
            time.sleep(backoff)

    print(f"{pfx} ✗ Tutti i {retries} tentativi falliti. Passo al successivo.")
    return False


#  Gestore download
def run_downloads(urls: list[str], output_dir: Path, organize: bool, overwrite: str, retries: int, bulk: bool, cooldown_base: float, cooldown_jitter: float) -> None:
    total = len(urls)

    print(f"\n{'═' * 62}")
    print(f"  spotDL Wrapper — {total} URL da scaricare")
    print(f"  Output          : {output_dir}")
    print(f"  Organizzazione  : {'Sì' if organize else 'No'}")
    print(f"  Overwrite       : {overwrite}")
    print(f"  Retry per URL   : {retries}")
    if bulk:
        print(f"  Modalità      : BULK  (cooldown {cooldown_base}s (+/-) {cooldown_jitter}s)")
    else:
        print(f"  Modalità      : Normale (nessun cooldown)")
    print(f"{'═' * 62}")

    output_dir.mkdir(parents=True, exist_ok=True)

    success_list = []
    failed_list  = []

    try:
        for idx, url in enumerate(urls, 1):
            ok = download_one(url=url, idx=idx, total=total, output_dir=output_dir, organize=organize, overwrite=overwrite, retries=retries)
            if ok:
                success_list.append(url)
            else:
                failed_list.append(url)

            # Cooldown solo in bulk mode e non dopo l'ultimo URL
            if bulk and idx < total:
                cooldown(cooldown_base, cooldown_jitter)

    except KeyboardInterrupt:
        print("\n\n[INTERROTTO] Download annullato dall'utente.")
        _print_summary(success_list, failed_list, total)
        sys.exit(0)

    _print_summary(success_list, failed_list, total)


def _print_summary(success_list: list, failed_list: list, total: int) -> None:
    print(f"\n{'═' * 62}")
    print(f"  Riepilogo: {len(success_list)}/{total} URL scaricati con successo.")
    if failed_list:
        print(f"\n  URL falliti ({len(failed_list)}):")
        for u in failed_list:
            print(f"    ✗ {u}")
    print(f"{'═' * 62}\n")


#  Parsing argomenti
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="spotDL_wrapper.py",
        description="Wrapper per spotDL: scarica album, artisti e playlist da Spotify.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Esempi:
  python3 spotDL_wrapper.py urls.txt
  python3 spotDL_wrapper.py urls.txt ~/Music/Spotify --organize
  python3 spotDL_wrapper.py urls.txt ~/Music --overwrite force
  python3 spotDL_wrapper.py urls.txt ~/Music --bulk
  python3 spotDL_wrapper.py urls.txt ~/Music --bulk --retries 5
  python3 spotDL_wrapper.py urls.txt ~/Music --bulk --cooldown 30 --cooldown-jitter 5

Modalità BULK (--bulk):
  Scarica gli URL in sequenza con un cooldown casuale tra uno e l'altro
  (default: {DEFAULT_COOLDOWN}s +/- {DEFAULT_COOLDOWN_JITTER}s) per ridurre il rischio di
  throttling da parte di Spotify/YouTube. Ogni URL viene ritentato
  fino a --retries volte (default: {DEFAULT_RETRIES}) prima di passare al successivo,
  con backoff crescente tra i tentativi (5s, 10s, 15s...).

Formato file URL (righe vuote e #commenti vengono ignorati):
  https://open.spotify.com/album/...
  https://open.spotify.com/artist/...
  https://open.spotify.com/playlist/...
        """,
    )

    parser.add_argument(
        "url_file",
        type=Path,
        help="File di testo contenente gli URL Spotify (uno per riga).",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Directory di destinazione (default: cartella corrente).",
    )
    parser.add_argument(
        "--organize",
        action="store_true",
        help="Crea sottocartelle Artista/Album/Canzone.mp3.",
    )
    parser.add_argument(
        "--overwrite",
        choices=OVERWRITE_MODES,
        default="skip",
        metavar="MODALITÀ",
        help=(
            "Gestione file duplicati: "
            "skip (salta, default) | metadata (aggiorna solo tag) | force (riscrivi tutto)."
        ),
    )
    bulk_group = parser.add_argument_group(
        "Bulk download",
        "Opzioni per il download di grandi liste di URL in modo sicuro e sostenibile.",
    )
    bulk_group.add_argument(
        "--bulk",
        action="store_true",
        help=(
            f"Attiva la modalità bulk: aggiunge un cooldown casuale di "
            f"{DEFAULT_COOLDOWN}s +/- {DEFAULT_COOLDOWN_JITTER}s tra un URL e il successivo "
            f"e ritenta i download falliti fino a --retries volte."
        ),
    )
    bulk_group.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        metavar="N",
        help=(
            f"Numero massimo di tentativi per ogni URL prima di passare al successivo "
            f"(default: {DEFAULT_RETRIES}). Tra ogni tentativo viene applicato un backoff "
            f"crescente (5s x numero_tentativo)."
        ),
    )
    bulk_group.add_argument(
        "--cooldown",
        type=float,
        default=DEFAULT_COOLDOWN,
        metavar="s",
        help=(
            f"Durata base del cooldown tra un URL e il successivo in modalità --bulk "
            f"(default: {DEFAULT_COOLDOWN}s). Il tempo effettivo varia di (+/-) --cooldown-jitter secondi."
        ),
    )
    bulk_group.add_argument(
        "--cooldown-jitter",
        type=float,
        default=DEFAULT_COOLDOWN_JITTER,
        metavar="s",
        dest="cooldown_jitter",
        help=(
            f"Variazione casuale (+/-) applicata al cooldown (default: (+/-){DEFAULT_COOLDOWN_JITTER}s). "
            f"Esempio: con --cooldown 20 --cooldown-jitter 2 l'attesa sarà tra 18s e 22s."
        ),
    )

    return parser.parse_args()


#  Entry point
def main() -> None:
    args = parse_args()
    urls = load_urls(args.url_file)
    output_dir = args.output_dir.expanduser().resolve()

    run_downloads(urls=urls, output_dir=output_dir, organize=args.organize, overwrite=args.overwrite, retries=args.retries, bulk=args.bulk, cooldown_base=args.cooldown, cooldown_jitter=args.cooldown_jitter)


if __name__ == "__main__":
    main()
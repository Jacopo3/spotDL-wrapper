# spotDL Wrapper

Uno script TUI che semplifica i download con **spotDL** per album, artisti, playlist e singole tracce Spotify. Offre modalità **bulk** con cooldown casuale, retry con backoff e opzioni di organizzazione in cartelle.

---

## Caratteristiche

- Lettura di un file di URL (uno per riga) con supporto per commenti `#` e righe vuote.
- Riconoscimento automatico del tipo di URL: album, artista, playlist, traccia.
- Costruzione sicura del comando `spotDL_wrapper` con template di output personalizzabile.
- **Overwrite** configurabile: `skip`, `metadata`, `force`.
- **Bulk mode** opzionale: cooldown casuale tra URL e retry con backoff progressivo.
- Riepilogo finale con successi/fallimenti.

---

## Installazione

1. Clona o copia **spotDL_wrapper.py**
2. (Opsionale) Crea e attiva un virtual environment

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install spotdl
    ```

3. Testare l'installazione

    ```bash
    python3 spotDL_wrapper.py --help
    ```

---

## Utilizzo

Sintassi base:

```bash
python3 spotDL_wrapper.py <file_urls.txt> [directory_output] [opzioni]
```

Esempi rapidi:

```bash
python3 spotDL_wrapper.py urls.txt ~/Music/Spotify --organize
```

### Argomenti principali

- `url_file` (obbligatorio): file di testo con URL Spotify, uno per riga.
- `output_dir` (opzionale): cartella di destinazione (default: la directory corrente).

### Opzioni

- `--organize`  
  Crea sottocartelle `Artista/Album/Titolo.formato` invece di salvare tutto nella stessa cartella.

- `--overwrite {skip|metadata|force}`  
  Controlla come gestire file già presenti:  
  - `skip` (default): non sovrascrive  
  - `metadata`: aggiorna solo i tag  
  - `force`: riscarica e riscrive  

- `--bulk`  
  Abilita la modalità bulk: inserisce un cooldown casuale tra URL e abilita i retry.
- `--retries N` (default: 3)  
  Numero di tentativi per ogni URL con backoff lineare (5s, 10s, 15s, …).
- `--cooldown s` (default: 20)  
  Durata base del cooldown tra URL.
- `--cooldown-jitter s` (default: 2)  
  Variazione casuale (+/-) applicata al cooldown.

---

## Formato del file di URL

Sono ignorati commenti e righe vuote. Supporta i seguenti tipi:

```text
https://open.spotify.com/track/...
https://open.spotify.com/album/...
https://open.spotify.com/artist/...
https://open.spotify.com/playlist/...
# Commento
```

---

## Crediti

- Tutto il lavoro vero è stato fatto da [spotDL](https://spotdl.readthedocs.io)

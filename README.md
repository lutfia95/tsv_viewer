# TSV Viewer

A small, read-only desktop TSV viewer made with Python and PySide6.

## Install and run

Open Command Prompt or PowerShell in this folder, then run:

```text
python -m pip install -r requirements.txt
python tsv_viewer.py
```

On Windows, after installing the dependency, you can also double-click
`run_tsv_viewer.bat`. You may pass a file directly:

```text
python tsv_viewer.py path\to\data.tsv
```

## Controls

- `Ctrl+O`: open a TSV file
- `Ctrl+F`: open search; typing highlights all matches
- `Enter` or `F3`: next match
- `Shift+F3`: previous match
- Click and drag to select cells
- Click a row number to select a row
- Click a column name to select a column
- Hold `Ctrl` to add separate cells, rows, or columns to the selection

The first line of the TSV file is used as its column headers. Files are opened
read-only, so the viewer cannot accidentally change the source data.

# Susu Group Manager

A small Python program that manages one rotating savings group ("susu").
Members each contribute a fixed weekly amount in GHS; the whole pot is
paid out to one member per week, in join order.

## Requirements

- Python 3.7 or newer (uses `dataclasses` and `Decimal`).
- No third-party packages required.

## Files

| File            | Purpose                                        |
| --------------- | ---------------------------------------------- |
| `susu.py`       | The program (library classes + CLI menu).      |
| `test_susu.py`  | Automated tests (unittest, no extras needed).  |
| `NOTES.md`      | Assumptions, decisions and future improvements.|

## Running the program

From the project folder:

```bash
python susu.py
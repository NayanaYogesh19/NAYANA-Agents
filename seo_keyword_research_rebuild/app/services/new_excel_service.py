import pandas as pd


def export_to_excel(rows, output_path):
    """Write keyword rows to Excel. All values are raw from SE Ranking API."""
    df = pd.DataFrame(rows, columns=[
        "Page URL",
        "Keyword",
        "Position",
        "Volume",
        "Difficulty",
        "CPC",
        "Competition",
        "Traffic"
    ])

    df.to_excel(output_path, index=False)
    print(f"EXCEL EXPORTED: {output_path} ({len(rows)} rows)")
    return output_path

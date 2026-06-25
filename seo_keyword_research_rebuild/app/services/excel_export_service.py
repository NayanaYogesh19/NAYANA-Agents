import pandas as pd

def export_excel(

    rows,

    output_file
):

    df = pd.DataFrame(rows)

    df.to_excel(

        output_file,

        index=False
    )

    return output_file
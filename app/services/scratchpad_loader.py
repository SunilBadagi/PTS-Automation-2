import pandas as pd


class ScratchPadLoader:

    def load(
        self,
        worksheet,
        csv_path
    ):

        df = pd.read_csv(
            csv_path,
            sep="\t"
        )

        worksheet.Cells.Clear()

        rows, cols = df.shape

        for r in range(rows):

            for c in range(cols):

                worksheet.Cells(
                    r + 1,
                    c + 1
                ).Value = df.iloc[r, c]
import pandas as pd


class DataLoader:

    @staticmethod
    def load_stacked_data(path):
        return pd.read_excel(path, sheet_name="Stacked Data")

    @staticmethod
    def load_data(path):
        return pd.read_excel(path, sheet_name="Data")

    @staticmethod
    def load_data_sheet(path):
        return pd.read_excel(path, sheet_name="Data")
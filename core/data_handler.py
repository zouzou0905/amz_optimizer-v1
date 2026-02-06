import pandas as pd
import os

class DataHandler:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path
        self.df = None

    def load_data(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"找不到输入文件: {self.input_path}")
        # 根据你的文件名，可能是读取 .xlsx
        self.df = pd.read_excel(self.input_path)
        return self.df

    def save_step(self, index, column_name, value):
        self.df.loc[index, column_name] = value
        # 实时保存到结果文件
        self.df.to_excel(self.output_path, index=False)
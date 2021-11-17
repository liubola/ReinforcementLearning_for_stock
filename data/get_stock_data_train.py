import baostock as bs
import os
from datetime import datetime, timedelta

def mkdir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok = True)

class Downloader(object):
    def __init__(self,
                 output_dir,
                 date_start,
                 date_end):
        self._bs = bs
        bs.login()
        self.date_start = date_start
        self.date_end = date_end
        self.output_dir = output_dir
        self.fields = "date,code,open,high,low,close,volume,amount," \
                      "adjustflag,turn,tradestatus,pctChg,peTTM," \
                      "pbMRQ,psTTM,pcfNcfTTM,isST"

    def exit(self):
        bs.logout()

    def get_codes_by_date(self, date):
        print(date)
        stock_rs = bs.query_all_stock(date)
        stock_df = stock_rs.get_data()
        print(stock_df)
        return stock_df

    def run(self):
        stock_df = self.get_codes_by_date(self.date_end)
        for index, row in stock_df.iterrows():
            print(f'processing {row["code"]} {row["code_name"]}')
            df_code = bs.query_history_k_data_plus(row["code"], self.fields,
                                                   start_date=self.date_start,
                                                   end_date=self.date_end,
                                                   adjustflag="1").get_data() # adjustflag：复权类型，默认不复权：3；1：后复权；2：前复权
            df_code.to_csv(f'{self.output_dir}/{row["code"]}.{row["code_name"].replace("*","star_")}.csv', index=False)
        self.exit()

if __name__ == '__main__':

    # 获取全部股票的日K线数据
    datapath_train = './train'
    mkdir(datapath_train)
    downloader = Downloader(datapath_train, date_start='1990-01-01', date_end='2019-11-29')
    downloader.run()

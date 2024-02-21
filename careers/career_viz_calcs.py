from collections import defaultdict
from tqdm import tqdm
import json
import numpy as np
import pandas as pd
import boto3
from datetime import datetime
from career_pipeline import CareerStage
from pandas import Timestamp

class VizCalcs(CareerStage):
    """
    Class to perform alculations for the RCR distributions per FOR graph
    """
    def __init__(self):
        super().__init__()
        self.career = CareerStage()
        self.RCR_distribution_data_path = "dimensions/careers/RCR_dict.json"

        self.process_RCR_distributions()
        self.career.load_career_processed_data()
        self.career.load_career_data_exploded()
        self.career.load_FOR_hierarchy()
        self.RCR_list()
        self.RCR_len()

        self.funders = ['DR', 'wellcome', 'MRC', 'NIHR', 'crick']

    def calculate_RCR_distributions(self):
        """
        Calculations for the RCR distributions per FOR graph
        """
        self.career.load_pub_ids()
        s3 = boto3.client('s3')

        RCR_dict = defaultdict(list)

        for _, item in tqdm(self.career.pubs_info.iterrows(), total=self.career.pubs_info.shape[0]):
            for FOR in eval(item['pub_FOR_super']):
                if not np.isnan(item['RCR']):
                    RCR_dict[FOR].append(item['RCR'])

        s3.put_object(Body=json.dumps(RCR_dict), Bucket=self.career.bucket, Key=self.RCR_distribution_data_path)

    def process_RCR_distributions(self):
        """
        pprocess RCR for each field into a numpy array
        """
        s3 = boto3.client('s3')
        content = s3.get_object(Bucket=self.bucket, Key=self.RCR_distribution_data_path)
        json_data = json.loads(content['Body'].read().decode('utf-8'))
        json_log_data = defaultdict(list)
        for key in json_data.keys():
            json_data[key] = np.array(json_data[key])
            json_log_data[key] = np.log(json_data[key])

        self.RCR_distribution_data = json_data
        self.RCR_log_distribution_data = json_log_data

    def RCR_list(self):
        """
        Creates a list of all RCR log values for Shapiro-Wilk test for normality
        """

        self.RCR_list = [x for values in self.RCR_log_distribution_data for x in (self.RCR_log_distribution_data[values])]

    def RCR_log_funder_lists(self):
        """
        Creates a list of all RCR log values for all considered funders
        """
        data = self.career.career_data_processed[['dimensions_publication_id', 'RCR_log', 'funder_crick', 'funder_DR', 'funder_MRC', 'funder_NIHR', 'funder_wellcome']]
        
        Crick_data = data[data['funder_crick'] == True]
        self.Crick_RCR_log_list = Crick_data[['dimensions_publication_id', 'RCR_log']].drop_duplicates(subset='dimensions_publication_id')['RCR_log'].tolist()
        self.Crick_RCR_log_list = [value for value in self.Crick_RCR_log_list if not np.isnan(value)]
        self.Crick_RCR_log_above_threshold_list = [value for value in self.Crick_RCR_log_list if value >= self.RCR_log_threshold]

        DR_data = data[data['funder_DR'] == True]
        self.DR_RCR_log_list = DR_data[['dimensions_publication_id', 'RCR_log']].drop_duplicates(subset='dimensions_publication_id')['RCR_log'].tolist()
        self.DR_RCR_log_list = [value for value in self.DR_RCR_log_list if not np.isnan(value)]
        self.DR_RCR_log_above_threshold_list = [value for value in self.DR_RCR_log_list if value >= self.RCR_log_threshold]

        Wellcome_data = data[data['funder_wellcome'] == True]
        self.Wellcome_RCR_log_list = Wellcome_data[['dimensions_publication_id', 'RCR_log']].drop_duplicates(subset='dimensions_publication_id')['RCR_log'].tolist()
        self.Wellcome_RCR_log_list = [value for value in self.Wellcome_RCR_log_list if not np.isnan(value)]
        self.Wellcome_RCR_log_above_threshold_list = [value for value in self.Wellcome_RCR_log_list if value >= self.RCR_log_threshold]

        MRC_data = data[data['funder_MRC'] == True]
        self.MRC_RCR_log_list = MRC_data[['dimensions_publication_id', 'RCR_log']].drop_duplicates(subset='dimensions_publication_id')['RCR_log'].tolist()
        self.MRC_RCR_log_list = [value for value in self.MRC_RCR_log_list if not np.isnan(value)]
        self.MRC_RCR_log_above_threshold_list = [value for value in self.MRC_RCR_log_list if value >= self.RCR_log_threshold]
        
        NIHR_data = data[data['funder_NIHR'] == True]
        self.NIHR_RCR_log_list = NIHR_data[['dimensions_publication_id', 'RCR_log']].drop_duplicates(subset='dimensions_publication_id')['RCR_log'].tolist()
        self.NIHR_RCR_log_list = [value for value in self.NIHR_RCR_log_list if not np.isnan(value)]
        self.NIHR_RCR_log_above_threshold_list = [value for value in self.NIHR_RCR_log_list if value >= self.RCR_log_threshold]

    def RCR_len(self):
        """
        Calculates how many publications and fields were considered for the RCR graphs
        """
        self.fields = len(self.RCR_distribution_data)
        self.num_pubs = sum([len(self.RCR_distribution_data[values]) for values in self.RCR_distribution_data])   

    def researchers_per_field(self):
        """
        Calculates the number of researchers per field per funder
        """
        self.DR_field_count = defaultdict(int)
        self.MRC_field_count = defaultdict(int)
        self.NIHR_field_count = defaultdict(int)
        self.Crick_field_count = defaultdict(int)
        self.Wellcome_field_count = defaultdict(int)

        for _, row in tqdm(self.career.career_data_exploded.iterrows()):
            fields = set(eval(row['pub_FOR_super_list']))
            for field in fields:
                if row['one_or_more_DR_pubs']:
                    self.DR_field_count[field]+=1
                if row['one_or_more_MRC_pubs']:
                    self.MRC_field_count[field]+=1
                if row['one_or_more_Wellcome_pubs']:
                    self.Wellcome_field_count[field]+=1
                if row['one_or_more_NIHR_pubs']:
                    self.NIHR_field_count[field]+=1
                if row['one_or_more_Crick_pubs']:
                    self.Crick_field_count[field]+=1

    def publications_per_field(self):
        """
        Calculates the number of publications per field per funder
        """
        self.DR_pubs_field_count = defaultdict(set)
        self.MRC_pubs_field_count = defaultdict(set)
        self.NIHR_pubs_field_count = defaultdict(set)
        self.Crick_pubs_field_count = defaultdict(set)
        self.Wellcome_pubs_field_count = defaultdict(set)

        for _, row in tqdm(self.career.career_data_exploded.iterrows()):
            fields = eval(row['pub_FOR_super_list'])
            for field in fields:
                if row['one_or_more_DR_pubs']:
                    self.DR_pubs_field_count[field].add(row['dimensions_publication_id'])
                if row['one_or_more_MRC_pubs']:
                    self.MRC_pubs_field_count[field].add(row['dimensions_publication_id'])
                if row['one_or_more_Wellcome_pubs']:
                    self.Wellcome_pubs_field_count[field].add(row['dimensions_publication_id'])
                if row['one_or_more_NIHR_pubs']:
                    self.NIHR_pubs_field_count[field].add(row['dimensions_publication_id'])
                if row['one_or_more_Crick_pubs']:
                    self.Crick_pubs_field_count[field].add(row['dimensions_publication_id'])

        

    def RCR_log_pubs_above_threshold(self):
        """
        Calculates the number of pubs per field per funder
        """
        self.DR_RCR_log_pubs_field_count = defaultdict(set)
        self.MRC_RCR_log_pubs_field_count = defaultdict(set)
        self.NIHR_RCR_log_pubs_field_count = defaultdict(set)
        self.Crick_RCR_log_pubs_field_count = defaultdict(set)
        self.Wellcome_RCR_log_pubs_field_count = defaultdict(set)

        for _, row in tqdm(self.career.career_data_exploded.iterrows()):
            fields = eval(row['pub_FOR_super_list'])
            values = eval(row['RCR_log_above_threshold'])
            for value, field in zip(values, fields):
                if value:
                    if row['one_or_more_DR_pubs']:
                        self.DR_RCR_log_pubs_field_count[field].add(row['dimensions_publication_id'])
                    if row['one_or_more_MRC_pubs']:
                        self.MRC_RCR_log_pubs_field_count[field].add(row['dimensions_publication_id'])
                    if row['one_or_more_Wellcome_pubs']:
                        self.Wellcome_RCR_log_pubs_field_count[field].add(row['dimensions_publication_id'])
                    if row['one_or_more_NIHR_pubs']:
                        self.NIHR_RCR_log_pubs_field_count[field].add(row['dimensions_publication_id'])
                    if row['one_or_more_Crick_pubs']:
                        self.Crick_RCR_log_pubs_field_count[field].add(row['dimensions_publication_id'])
        
    def RCR_log_above_threshold(self):
        """
        Calculates the number of researchers per field per funder
        """
        self.DR_RCR_log_field_count = defaultdict(int)
        self.MRC_RCR_log_field_count = defaultdict(int)
        self.NIHR_RCR_log_field_count = defaultdict(int)
        self.Crick_RCR_log_field_count = defaultdict(int)
        self.Wellcome_RCR_log_field_count = defaultdict(int)

        for _, row in tqdm(self.career.career_data_exploded.iterrows()):
            fields = set(eval(row['pub_FOR_super_list']))
            values = eval(row['RCR_log_above_threshold'])
            for field in fields:
                if any(values):
                    if row['one_or_more_DR_pubs']:
                        self.DR_RCR_log_field_count[field]+=1
                    if row['one_or_more_MRC_pubs']:
                        self.MRC_RCR_log_field_count[field]+=1
                    if row['one_or_more_Wellcome_pubs']:
                        self.Wellcome_RCR_log_field_count[field]+=1
                    if row['one_or_more_NIHR_pubs']:
                        self.NIHR_RCR_log_field_count[field]+=1
                    if row['one_or_more_Crick_pubs']:
                        self.Crick_RCR_log_field_count[field]+=1
        
    
    
    def RCR_log_per_DR_scheme(self):
        """
        Calculates the RCR log above the 95th percentile threshold per DR scheme
        """
        DR_pub_id_tracker = set()
        self.DR_scheme_RCR_dict = defaultdict(list)

        for _, item in self.career.career_data_exploded.iterrows():
            values = eval(item['DR_scheme'].replace('nan', 'None'))
            RCR_logs = eval(item['RCR_log'].replace('nan', 'None'))
            pub_ids = eval(item['dimensions_publication_id'].replace('nan', 'None'))

            for value, RCR_log, pub_id in zip(values, RCR_logs, pub_ids):
                if RCR_log is not None and value is not None and pub_id not in DR_pub_id_tracker:
                    self.DR_scheme_RCR_dict[value].append(RCR_log)
                    DR_pub_id_tracker.add(pub_id)

        self.DR_scheme_RCR_log_len = [len(self.DR_scheme_RCR_dict[key]) for key in self.DR_scheme_RCR_dict.keys()]

        self.DR_scheme_labels = [key for key in self.DR_scheme_RCR_dict.keys()]
        self.DR_scheme_RCR_log_above_thresh_len = []
        for key in self.DR_scheme_RCR_dict:
            length = len([value for value in self.DR_scheme_RCR_dict[key] if value > self.career.RCR_log_threshold])
            self.DR_scheme_RCR_log_above_thresh_len.append(length)


    def first_funding_date(self, dates, boolean_values):
        dates = eval(dates.replace('nan', 'None'))

        dates = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in dates if isinstance(date_str, str)]
        dates = [date for date, bool in zip(dates, eval(boolean_values)) if bool is True]
        if len(dates)>0:
            sorted_dates = sorted(dates)
            return sorted_dates[0]
        
    def RCR_log_pubs_since_funding(self):
        
        self.career.career_data_exploded = self.career.career_data_exploded.rename(columns={'DR_pub': 'funder_DR'})
        for funder in self.funders:
            self.career.career_data_exploded[f'grant_start_{funder}'] = self.career.career_data_exploded.apply(lambda row: self.first_funding_date(row['grant_start_date'], row[f'funder_{funder}']), axis=1)

        self.RCR_log_pubs_before = defaultdict(int)
        self.RCR_log_pubs_after = defaultdict(int)
        self.RCR_log_pubs_before_over_threshold = defaultdict(int)
        self.RCR_log_pubs_after_over_threshold = defaultdict(int)
        
        threshold = self.career.RCR_log_threshold

        for _, item in self.career.career_data_exploded.iterrows():
            grant_start_date = defaultdict(Timestamp)
            for funder in self.funders:
                grant_start_date[funder] = item[f'grant_start_{funder}']
            pub_dates = eval(item['date'])
            pub_dates = [pd.to_datetime(date) for date in pub_dates]
            RCR_log = eval(item['RCR_log'].replace('nan', 'None'))
            pub_ids = eval(item['dimensions_publication_id'].replace('nan', 'None'))
                           
            for idx in range(len(RCR_log)):
                if RCR_log[idx] is not None:
                    for funder in self.funders:
                        if RCR_log[idx]>= threshold and pub_dates[idx]>grant_start_date[funder]:
                            self.RCR_log_pubs_after_over_threshold[funder]+=1
                            self.RCR_log_pubs_after[funder]+=1
                        if RCR_log[idx]< threshold and pub_dates[idx]>grant_start_date[funder]:
                            self.RCR_log_pubs_after[funder]+=1
                        if RCR_log[idx]>= threshold and pub_dates[idx]<=grant_start_date[funder]:
                            self.RCR_log_pubs_before_over_threshold[funder]+=1
                            self.RCR_log_pubs_before[funder]+=1
                        if RCR_log[idx]< threshold and pub_dates[idx]<=grant_start_date[funder]:
                            self.RCR_log_pubs_before[funder]+=1

    def inner_product(self, list_1, list_2):
        return  sum([x*y for x,y in zip(list_1,list_2)])

    def RCR_log_over_time(self):
        years_list = list(range(2002, 2024))
        data = self.career.career_data_processed[['dimensions_publication_id', 'RCR_log_above_threshold', 'date', 'funder_DR', 'funder_wellcome', 'funder_MRC', 'funder_NIHR', 'funder_crick']]
        data['date'] = pd.to_datetime(data['date'])
        data['year'] = data['date'].dt.year

        # only consider year in years_list
        data = data[data['year'].isin(years_list)]
        data = data.drop_duplicates(subset=['dimensions_publication_id', 'funder_DR', 'funder_wellcome', 'funder_MRC', 'funder_NIHR', 'funder_crick'])
        data_grouped = data.groupby('year')[['RCR_log_above_threshold', 'funder_DR', 'funder_wellcome', 'funder_MRC', 'funder_NIHR', 'funder_crick']].agg(list)
    

        funders = self.funders
        for funder in funders:
            data_grouped[f'funder_{funder}_count'] = data_grouped[f'funder_{funder}'].apply(lambda x: sum(x))
            data_grouped[f'funder_{funder}_above_threshold'] = data_grouped.apply(lambda row: self.inner_product(row[f'funder_{funder}'], row['RCR_log_above_threshold']), axis=1)
            data_grouped[f'funder_{funder}_RCR_log_proportion'] = data_grouped.apply(lambda row: row[f'funder_{funder}_above_threshold']/row[f'funder_{funder}_count'] if row[f'funder_{funder}_count']>0 else 0, axis=1)

        self.RCR_log_over_time = data_grouped
    


    
if __name__ == "__main__":

    viz_calcs = VizCalcs()
    # viz_calcs.calculate_RCR_distributions()
    viz_calcs.process_RCR_distributions()
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

        self.funders = ['DR', 'wellcome', 'MRC', 'NIHR']
        self.fields = list(set(list(self.career.FOR_hierarchy.values())))

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
        
        self.RCR_log_list = {funder: [] for funder in self.funders}
        self.RCR_log_list_above_threshold = {funder: [] for funder in self.funders}

        for funder in self.funders:
            funder_data = data[data[f'funder_{funder}'] == True]
            self.RCR_log_list[funder] = funder_data[['dimensions_publication_id', 'RCR_log']].drop_duplicates(subset='dimensions_publication_id')['RCR_log'].tolist()
            self.RCR_log_list[funder] = [value for value in self.RCR_log_list[funder] if not np.isnan(value)]
            self.RCR_log_list_above_threshold[funder] = [value for value in self.RCR_log_list[funder] if value >= self.RCR_log_threshold]

    def RCR_len(self):
        """
        Calculates how many publications and fields were considered for the RCR graphs
        """
        self.num_fields = len(self.RCR_distribution_data)
        self.num_pubs = sum([len(self.RCR_distribution_data[values]) for values in self.RCR_distribution_data])   

    def researchers_per_field(self):
        """
        Calculates the number of researchers per field per funder
        """
        self.researcher_field_count = {funder: defaultdict(int) for funder in self.funders}

        for _, row in tqdm(self.career.career_data_exploded.iterrows(), total=self.career.career_data_exploded.shape[0]):
            fields = set(eval(row['pub_FOR_super_list']))
            for field in fields:
                for funder in self.funders:
                    if row[f'one_or_more_{funder}_pubs']:
                        self.researcher_field_count[funder][field]+=1

        
    def researchers_per_field_above_threshold(self):
        """
        Calculates the number of researchers per field per funder with RCR log above the 95th percentile threshold
        """
        self.researcher_field_count_above_thresh = {funder: defaultdict(int) for funder in self.funders}

        for _, row in tqdm(self.career.career_data_exploded.iterrows(), total=self.career.career_data_exploded.shape[0]):
            fields = set(eval(row['pub_FOR_super_list']))
            values = eval(row['RCR_log_above_threshold'])
            for field in fields:
                if any(values):
                    for funder in self.funders:
                        if row[f'one_or_more_{funder}_pubs']:
                            self.researcher_field_count_above_thresh[funder][field]+=1

    def publications_per_field(self):
        """
        Calculates the number of pubs per field per funder
        """
        data = self.career.career_data_processed[['dimensions_publication_id', 'pub_FOR_super', 'RCR_log_above_threshold', 'funder_NIHR', 'funder_wellcome', 'funder_MRC', 'funder_DR']]

        self.pubs_field_count = {funder: defaultdict(int) for funder in self.funders}
        self.pubs_field_count_above_thresh = {funder: defaultdict(int) for funder in self.funders}


        for funder in self.funders:
            funder_data = data[data[f'funder_{funder}'] == True]
            already_done_pubs = set()
            # funder_data = funder_data.drop_duplicates(subset=['dimensions_publication_id','pub_FOR_super'])[['pub_FOR_super', 'RCR_log_above_threshold']]
            for _, row in tqdm(funder_data.iterrows()):
                if row['dimensions_publication_id'] not in already_done_pubs:
            # if there is at least one publication in the field, add the publication ids to the set
                    for field in eval(row['pub_FOR_super']):
                        self.pubs_field_count[funder][field]+=1
                        if row['RCR_log_above_threshold']:
                            self.pubs_field_count_above_thresh[funder][field]+=1
                    already_done_pubs.add(row['dimensions_publication_id'])
        
    
    def RCR_log_per_DR_scheme(self):
        """
        Calculates the RCR log above the 95th percentile threshold per DR scheme
        """

        data = self.career.career_data_processed[['dimensions_publication_id', 'DR_scheme', 'RCR_log', 'RCR_log_above_threshold']]
        data.dropna(subset=['DR_scheme', 'RCR_log'], inplace=True)
        self.DR_scheme_RCR_dict = defaultdict(list)
        self.DR_scheme_RCR_log_len = defaultdict(int)
        self.DR_scheme_RCR_log_above_thresh_len = defaultdict(int)
        self.DR_scheme_labels = list(set(data['DR_scheme']))

        for _, item in data.iterrows():
            value = item['DR_scheme']
            RCR_log_above_threshold = item['RCR_log_above_threshold']
            pub_id = item['dimensions_publication_id']
            self.DR_scheme_RCR_dict[value].append(pub_id)
            self.DR_scheme_RCR_log_len[value]+=1
            if value in self.DR_scheme_labels:
                if RCR_log_above_threshold:
                    self.DR_scheme_RCR_log_above_thresh_len[value]+=1

    def first_funding_date(self, dates, boolean_values):
        """
        Utility function to find the first funding date for each funder
        Args:
            dates: list of dates
            boolean_values: list of boolean values representing the presense of a funder

        Returns:
            first funding date
        """
        dates = eval(dates.replace('nan', 'None'))

        dates = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in dates if isinstance(date_str, str)]
        dates = [date for date, bool in zip(dates, eval(boolean_values)) if bool is True]
        if len(dates)>0:
            sorted_dates = sorted(dates)
            return sorted_dates[0]
        
    def RCR_log_pubs_since_funding(self):
        """
        Calculates the proportion of RCR log over threshold before and after funding for each funder
        """

        self.RCR_log_pubs_before = defaultdict(int)
        self.RCR_log_pubs_after = defaultdict(int)
        self.RCR_log_pubs_before_over_threshold = defaultdict(int)
        self.RCR_log_pubs_after_over_threshold = defaultdict(int)

        threshold = self.career.RCR_log_threshold

        # pull out the first grant start date for each funder
        for funder in self.funders:
            self.career.career_data_exploded[f'grant_start_{funder}'] = self.career.career_data_exploded.apply(lambda row: self.first_funding_date(row['grant_start_date'], row[f'funder_{funder}']), axis=1)

        for _, item in tqdm(self.career.career_data_exploded.iterrows(), desc='calculating proportion of RCR log over threshold before and after funding'):
            grant_start_date = defaultdict(Timestamp)
            for funder in self.funders:
                grant_start_date[funder] = item[f'grant_start_{funder}']
            pub_dates = eval(item['date'])
            pub_dates = [pd.to_datetime(date) for date in pub_dates]
            RCR_log = eval(item['RCR_log'].replace('nan', 'None'))
            pub_ids = eval(item['dimensions_publication_id'].replace('nan', 'None'))
            already_done_pubs = set()

            for idx in range(len(RCR_log)):
                if RCR_log[idx] is not None:
                    if pub_ids[idx] not in already_done_pubs:
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
                        already_done_pubs.add(pub_ids[idx])

    def inner_product(self, list_1, list_2):
        """
        Utility function to calculate the inner product of two lists
        Args:
            list_1: list 1
            list_2: list 2

        Returns:
            inner product of the two lists
        """
        return  sum([x*y for x,y in zip(list_1,list_2)])

    def RCR_log_over_time(self):
        """
        Calculates the RCR log over time for each funder
        """
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
        
    def years_from_first_to_last_author_position(self):
        """
        Calculates the number of years it takes to reach last author position for researchers related to the funders of interest

        Returns:
            hist_values: dictionary with the number of years it takes to reach last author position for researchers related to the funders of interest
            hist_bins: dictionary with the bins for the number of years it takes to reach last author position for researchers related to the funders of interest
        """
        hist_values = defaultdict(list)
        hist_bins = defaultdict(list)
        plt_data = self.career.career_data_exploded[['years_between_first_last', 'funder_DR', 'funder_wellcome', 'funder_MRC', 'funder_NIHR']]

        for funder in self.funders:
            plt_data[f'funder_{funder}_union'] = plt_data[f'funder_{funder}'].apply(lambda x: any(eval(x.replace('nan', 'None'))))

            hist_data = plt_data[plt_data[f'funder_{funder}_union']==True]['years_between_first_last'].dropna()
            hist_values[funder], hist_bins[funder] = np.histogram(hist_data, bins=100, density=True)

        return hist_values, hist_bins
    
    def years_since_first_pub(self):
        """
        Calculates the number of years since first publication for researchers related to the funders of interest

        Returns:
            hist_values: dictionary with the number of years since first publication for researchers related to the funders of interest
            hist_bins: dictionary with the bins for the number of years since first publication for researchers related to the funders of interest
        """
        hist_values = defaultdict(list)
        hist_bins = defaultdict(list)
        plt_data = self.career.career_data_exploded[['max_time_since_first_pub', 'funder_DR', 'funder_wellcome', 'funder_MRC', 'funder_NIHR']]

        for funder in self.funders:
            plt_data[f'funder_{funder}_union'] = plt_data[f'funder_{funder}'].apply(lambda x: any(eval(x.replace('nan', 'None'))))

            hist_data = plt_data[plt_data[f'funder_{funder}_union']==True]['max_time_since_first_pub'].dropna()
            hist_values[funder], hist_bins[funder] = np.histogram(hist_data, bins=100, density=True)

        return hist_values, hist_bins
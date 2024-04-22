
from career_pipeline import CareerStage

if __name__ == "__main__":
    """
    Script to run all data extraction and processing functions from the CareerStage class
    """
    career_stage = CareerStage()
    # career_stage.career_info_adam()
    # career_stage.career_info_wac()

    career_stage.collate_career_info()
    career_stage.process_career_info()
    career_stage.process_career_info_exploded()
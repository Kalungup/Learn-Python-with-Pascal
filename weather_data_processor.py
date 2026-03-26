"""
field_data_processor.py

Module for ingesting, cleaning, and processing field data
for the Maji Ndogo farm survey project.
"""

import logging
import pandas as pd
from data_ingestion import create_db_engine, query_data, read_from_web_CSV


class FieldDataProcessor:
    """
    Processes field survey data including ingestion, cleaning,
    renaming, and merging weather station mapping.
    """

    def __init__(self, config_params, logging_level="INFO"):
        """
        Initialize processor with configuration parameters.
        """

        self.db_path = config_params["db_path"]
        self.sql_query = config_params["sql_query"]
        self.columns_to_rename = config_params["columns_to_rename"]
        self.values_to_rename = config_params["values_to_rename"]
        self.weather_csv_path = config_params["weather_csv_path"]
        self.weather_mapping_csv = config_params["weather_mapping_csv"]

        self.df = None
        self.engine = None

        self._initialize_logging(logging_level)

    def _initialize_logging(self, logging_level):
        """Set up logging configuration."""

        logger_name = __name__ + ".FieldDataProcessor"
        self.logger = logging.getLogger(logger_name)
        self.logger.propagate = False

        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "NONE": None
        }

        log_level = level_map.get(logging_level.upper(), logging.INFO)

        if log_level is None:
            self.logger.disabled = True
            return

        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def ingest_sql_data(self):
        """Load data from SQL database."""

        self.engine = create_db_engine(self.db_path)
        self.df = query_data(self.engine, self.sql_query)

        self.logger.info("Successfully ingested SQL data.")
        return self.df

    def rename_columns(self):
        """Swap column names safely."""

        col1 = list(self.columns_to_rename.keys())[0]
        col2 = list(self.columns_to_rename.values())[0]

        temp_name = "__temp_swap__"

        self.df.rename(columns={col1: temp_name}, inplace=True)
        self.df.rename(columns={col2: col1}, inplace=True)
        self.df.rename(columns={temp_name: col2}, inplace=True)

        self.logger.info(f"Swapped columns: {col1} and {col2}")

    def apply_corrections(self):
        """Correct spelling and elevation values."""

        self.df["Elevation"] = self.df["Elevation"].abs()

        self.df["Crop_type"] = self.df["Crop_type"].replace(
            self.values_to_rename
        )

        self.logger.info("Applied crop type and elevation corrections.")

    def weather_station_mapping(self):
        """Load weather station mapping data."""

        weather_map_df = read_from_web_CSV(self.weather_mapping_csv)

        self.logger.info("Weather station mapping loaded.")

        return weather_map_df

    def process(self):
        """Execute full processing pipeline."""

        self.ingest_sql_data()

        self.rename_columns()

        self.apply_corrections()

        weather_map_df = self.weather_station_mapping()

        self.df = self.df.merge(
            weather_map_df,
            on="Field_ID",
            how="left"
        )

        self.logger.info("Processing completed successfully.")

        return self.df
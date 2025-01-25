import pandas as pd
import validators

REQUIRED_COLUMNS = ['S.No.', 'Product Name', 'Input Image Urls']

def validate_csv(file_path):
    try:
        df = pd.read_csv(file_path, quotechar='"', skipinitialspace=True, dtype=str)
        # Check if required columns are present
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            return False, f"Missing required column(s): {', '.join(missing_columns)}"

        # Check for empty (null or empty string) values in required columns
        for col in REQUIRED_COLUMNS:
            if df[col].str.strip().eq('').any():
                return False, f"Column '{col}' contains empty values."

        # Validate URLs in the 'Input Image Urls' column
        for index, row in df.iterrows():
            urls = str(row['Input Image Urls']).strip()  # Ensure it’s a string and remove extra spaces
            if urls == '':
                return False, f"Empty URL field found at row {index + 1}"

            url_list = [url.strip() for url in urls.split(',')]
            for url in url_list:
                if not validators.url(url):
                    return False, f"Invalid URL found at row {index + 1}: {url}"

        return True, "CSV is valid"

    except pd.errors.EmptyDataError:
        return False, "CSV file is empty or unreadable."

    except pd.errors.ParserError:
        return False, "CSV file contains parsing errors (e.g., incorrect delimiters or corrupted data)."

    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"
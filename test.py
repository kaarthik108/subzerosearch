
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("kaarthik Andavar Senior Data Engineer Resume.pdf")
print(result.text_content)


CREATE OR REPLACE FUNCTION parse_pdf_from_stage(file_path STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.9'
PACKAGES = ('snowflake-snowpark-python', 'markitdown')
HANDLER = 'parse_pdf'
AS
$$
import snowflake.snowpark as snowpark
from markitdown import MarkItDown

def parse_pdf(file_path):
    # Initialize the MarkItDown parser
    md = MarkItDown()
    
    # Read the file from the stage location
    # Assuming the file is already downloaded to a local path
    # You might need to use Snowflake's GET command to download the file first
    with open(file_path, 'rb') as file:
        # Convert the PDF to text
        result = md.convert(file)
    
    # Return the text content
    return result.text_content
$$;
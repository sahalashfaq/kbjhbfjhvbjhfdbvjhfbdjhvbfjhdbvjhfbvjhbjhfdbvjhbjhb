import streamlit as st
import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
from io import BytesIO
import urllib.parse

# Configure Streamlit page
st.set_page_config(
    layout="wide"
)

# Regex to detect phone numbers (supports multiple formats)
PHONE_REGEX = r"""
    (?:\+?\d{1,3}[-.\s]?)?  # Country code
    \(?\d{2,3}\)?[-.\s]?    # Area code (optional)
    \d{3,4}[-.\s]?          # First part
    \d{3,4}                 # Second part
"""

def extract_phone_numbers(url):
    """Extract phone numbers from a given URL."""
    try:
        # Fix URL format if needed
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.netloc:
            return {"status": "error", "message": "Invalid URL", "numbers": []}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        # Find all phone numbers (remove duplicates)
        phone_numbers = re.findall(PHONE_REGEX, text, re.VERBOSE)
        cleaned_numbers = list(set([num.strip() for num in phone_numbers if len(num) > 7]))
        
        return {"status": "success", "numbers": cleaned_numbers}
    
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {str(e)}", "numbers": []}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}", "numbers": []}

def process_file(uploaded_file):
    """Read CSV/Excel file into a DataFrame."""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            return None, "❌ Unsupported file. Upload CSV/Excel."
        return df, None
    except Exception as e:
        return None, f"❌ Error reading file: {str(e)}"

def main():
    # st.title("📞 Website Phone Number Extractor")
    st.markdown("""
    Upload a **CSV/Excel** file containing website URLs.  
    The tool will extract phone numbers and add them in a new column.  
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload CSV/Excel File",
        type=['csv', 'xls', 'xlsx'],
        help="File must contain a column with website URLs."
    )
    
    if uploaded_file:
        df, error = process_file(uploaded_file)
        
        if error:
            st.error(error)
            return
        
        st.markdown("<p style='font-weight:600;font-size:xx-large;'>📂 File Preview</p>",unsafe_allow_html=True)
        st.dataframe(df.head())
        
        # Let user select URL column
        url_column = st.selectbox(
            "Select the URL Column",
            options=df.columns,
            index=0
        )
        
        if st.button("🔍 Extract Phone Numbers"):
            with st.spinner("Extracting phone numbers. This may take a while..."):
                progress_bar = st.progress(0)
                results = []
                
                for i, row in df.iterrows():
                    url = row[url_column]
                    
                    if pd.isna(url) or str(url).strip() == '':
                        results.append({
                            "url": url,
                            "phone_numbers": "No URL provided",
                            "status": "skipped"
                        })
                        continue
                    
                    # Clean URL
                    url = str(url).strip()
                    extraction_result = extract_phone_numbers(url)
                    
                    if extraction_result['status'] == 'success':
                        numbers = extraction_result['numbers']
                        if numbers:
                            phone_str = " / ".join(numbers)
                            status = f"Found {len(numbers)} numbers"
                        else:
                            phone_str = "No numbers found"
                            status = "no numbers"
                    else:
                        phone_str = f"Error: {extraction_result.get('message', 'Unknown error')}"
                        status = "error"
                    
                    results.append({
                        "url": url,
                        "phone_numbers": phone_str,
                        "status": status
                    })
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(df))
                
                # Add results to DataFrame
                df['Phone_Numbers'] = [r['phone_numbers'] for r in results]
                df['Extraction_Status'] = [r['status'] for r in results]
                
                # Show results
                st.success("✅ Extraction complete!")
                st.dataframe(df.head())
                
                # Download results
                output = BytesIO()
                if uploaded_file.name.endswith('.csv'):
                    df.to_csv(output, index=False)
                    file_extension = 'csv'
                else:
                    df.to_excel(output, index=False)
                    file_extension = 'xlsx'
                
                output.seek(0)
                
                st.download_button(
                    label="📥 Download Results",
                    data=output,
                    file_name=f"phone_numbers_extracted.{file_extension}",
                    mime=f"application/{file_extension}"
                )
                
                # Show stats
                st.markdown("<p style='font-weight:600;font-size:xx-large;'>📊 Extraction Stats</p>",unsafe_allow_html=True)
                stats = pd.DataFrame(results)['status'].value_counts().reset_index()
                stats.columns = ['Status', 'Count']
                st.write(stats)
                
                # Show errors (if any)
                errors = [r for r in results if r['status'] == 'error']
                if errors:
                    st.warning(f"⚠️ Errors in {len(errors)} URLs:")
                    for error in errors[:3]:
                        st.write(f"- **{error['url']}**: {error['phone_numbers']}")

if __name__ == "__main__":
    main()

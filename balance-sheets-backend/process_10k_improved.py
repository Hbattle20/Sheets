#!/usr/bin/env python3
"""
Improved 10-K processor that uses SEC's TEXT format for better section extraction.
Downloads from SEC directly and processes for vector database.
"""

import os
import json
import csv
import re
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurable parameters
CHUNK_SIZE_WORDS = 800  # Target chunk size in words
MIN_CHUNK_SIZE_WORDS = 100  # Minimum chunk size
MAX_CHUNK_SIZE_WORDS = 1000  # Maximum chunk size
OVERLAP_PERCENTAGE = 0.15  # 15% overlap between chunks

# Financial-specific stop words to keep (these are important in financial context)
FINANCIAL_KEEP_WORDS = {'not', 'no', 'without', 'less', 'more', 'under', 'over', 
                       'before', 'after', 'above', 'below', 'loss', 'gain', 'risk',
                       'significant', 'material', 'adverse'}

# Section patterns for extraction
SECTION_PATTERNS = [
    (r'ITEM\s*1\s*[\.—–\-]?\s*B?USINESS', 'Item 1 - Business'),
    (r'ITEM\s*1\s*A\s*[\.—–\-]?\s*RISK\s*FACTORS?', 'Item 1A - Risk Factors'),
    (r'ITEM\s*1\s*B\s*[\.—–\-]?\s*UNRESOLVED\s*STAFF\s*COMMENTS?', 'Item 1B - Unresolved Staff Comments'),
    (r'ITEM\s*1\s*C\s*[\.—–\-]?\s*CYBERSECURITY', 'Item 1C - Cybersecurity'),
    (r'ITEM\s*2\s*[\.—–\-]?\s*PROPERTIES', 'Item 2 - Properties'),
    (r'ITEM\s*3\s*[\.—–\-]?\s*LEGAL\s*PROCEEDINGS?', 'Item 3 - Legal Proceedings'),
    (r'ITEM\s*4\s*[\.—–\-]?\s*MINE\s*SAFETY', 'Item 4 - Mine Safety Disclosures'),
    (r'ITEM\s*5\s*[\.—–\-]?\s*MARKET\s*FOR', 'Item 5 - Market Information'),
    (r'ITEM\s*6\s*[\.—–\-]?\s*(?:\[?RESERVED\]?|SELECTED\s*FINANCIAL)', 'Item 6 - Selected Financial Data'),
    (r'ITEM\s*7\s*[\.—–\-]?\s*MANAGEMENT', 'Item 7 - MD&A'),
    (r'ITEM\s*7\s*A\s*[\.—–\-]?\s*QUANTITATIVE', 'Item 7A - Market Risk'),
    (r'ITEM\s*8\s*[\.—–\-]?\s*FINANCIAL\s*STATEMENTS?', 'Item 8 - Financial Statements'),
    (r'ITEM\s*9\s*[\.—–\-]?\s*CHANGES?\s*IN', 'Item 9 - Changes in Accountants'),
    (r'ITEM\s*9\s*A\s*[\.—–\-]?\s*CONTROLS?\s*AND\s*PROCEDURES?', 'Item 9A - Controls and Procedures'),
    (r'ITEM\s*9\s*B\s*[\.—–\-]?\s*OTHER\s*INFORMATION', 'Item 9B - Other Information'),
    (r'ITEM\s*9\s*C\s*[\.—–\-]?\s*DISCLOSURE\s*REGARDING', 'Item 9C - Foreign Jurisdictions'),
]


class ImprovedSEC10KProcessor:
    """Process 10-K documents from SEC's TEXT format"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.archives_url = "https://www.sec.gov/Archives/edgar/data"
        self.headers = {
            'User-Agent': 'BalanceSheetsApp/1.0 (contact@example.com)',
            'Accept': 'application/json,text/plain,text/html'
        }
        
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            logger.info("Downloading NLTK punkt_tab tokenizer...")
            nltk.download('punkt_tab', quiet=True)
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a company ticker"""
        try:
            tickers_url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(tickers_url, headers=self.headers)
            response.raise_for_status()
            
            tickers_data = response.json()
            
            for item in tickers_data.values():
                if item.get('ticker') == ticker:
                    cik = str(item.get('cik_str')).zfill(10)
                    logger.info(f"Found CIK for {ticker}: {cik}")
                    return cik
            
            logger.error(f"CIK not found for ticker {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting CIK: {e}")
            return None
    
    def get_recent_10k_urls(self, ticker: str) -> Optional[Dict]:
        """Get URLs for the most recent 10-K filing"""
        try:
            cik = self.get_cik(ticker)
            if not cik:
                return None
            
            # Get company submissions
            submissions_url = f"{self.base_url}/submissions/CIK{cik}.json"
            response = requests.get(submissions_url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            recent_filings = data.get('filings', {}).get('recent', {})
            
            # Find the most recent 10-K
            forms = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            
            for i, form in enumerate(forms):
                if form == '10-K':
                    accession = accession_numbers[i]
                    accession_clean = accession.replace('-', '')
                    cik_clean = cik.lstrip('0')
                    
                    base_filing_url = f"{self.archives_url}/{cik_clean}/{accession_clean}"
                    
                    return {
                        'ticker': ticker,
                        'filing_date': filing_dates[i],
                        'accession': accession,
                        'txt_url': f"{base_filing_url}/{accession}.txt",
                        'html_url': f"{base_filing_url}/{accession}-index.html"
                    }
            
            logger.error("No 10-K filing found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting 10-K URLs: {e}")
            return None
    
    def download_and_extract_text(self, ticker: str) -> Optional[Tuple[str, Dict]]:
        """Download 10-K and extract clean text from TEXT section"""
        try:
            # Get filing URLs
            filing_info = self.get_recent_10k_urls(ticker)
            if not filing_info:
                return None
            
            logger.info(f"Downloading 10-K from: {filing_info['txt_url']}")
            
            # Download the complete submission file
            response = requests.get(filing_info['txt_url'], headers=self.headers)
            response.raise_for_status()
            
            content = response.text
            logger.info(f"Downloaded {len(content):,} characters")
            
            # Extract the TEXT section
            text_start = content.find('<TEXT>')
            text_end = content.find('</TEXT>')
            
            if text_start == -1 or text_end == -1:
                logger.error("Could not find <TEXT> section in filing")
                return None
            
            # Extract just the TEXT section
            text_content = content[text_start + 6:text_end]  # +6 to skip <TEXT>
            
            # If the TEXT section contains HTML, clean it
            if '<html' in text_content.lower()[:1000]:
                logger.info("TEXT section contains HTML, cleaning...")
                soup = BeautifulSoup(text_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text
                text_content = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text_content.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text_content = '\n'.join(chunk for chunk in chunks if chunk)
            
            logger.info(f"Extracted clean text: {len(text_content):,} characters")
            
            return text_content, filing_info
            
        except Exception as e:
            logger.error(f"Error downloading/extracting 10-K: {e}")
            return None
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from clean text"""
        sections = {}
        
        # Find all section positions
        found_sections = []
        for pattern, name in SECTION_PATTERNS:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            if matches:
                # Take the last match to avoid TOC
                match = matches[-1]
                found_sections.append((match.start(), name))
                logger.info(f"Found {name} at position {match.start()}")
        
        # Sort by position
        found_sections.sort(key=lambda x: x[0])
        
        # Extract text between sections
        for i, (start, name) in enumerate(found_sections):
            if i < len(found_sections) - 1:
                end = found_sections[i + 1][0]
            else:
                # Look for common end markers
                end_match = re.search(r'(SIGNATURES|EXHIBIT\s+INDEX|^ITEM\s+15\.)', 
                                    text[start:], re.IGNORECASE | re.MULTILINE)
                if end_match:
                    end = start + end_match.start()
                else:
                    end = min(start + 500000, len(text))  # Max 500k chars
            
            section_text = text[start:end].strip()
            
            # Clean section text
            section_text = self.clean_section_text(section_text)
            
            if len(section_text) > 50:  # Lower threshold to capture short sections like "Not applicable"
                sections[name] = section_text
                logger.info(f"Extracted {name}: {len(section_text):,} characters")
        
        return sections
    
    def clean_section_text(self, text: str) -> str:
        """Clean section text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers
        text = re.sub(r'Table of Contents', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Page \d+', '', text)
        text = re.sub(r'\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove repeated dashes or underscores
        text = re.sub(r'[-_]{3,}', '', text)
        
        return text.strip()
    
    def create_chunks(self, text: str, section_name: str) -> List[Dict]:
        """Create overlapping chunks from text"""
        chunks = []
        
        # Tokenize into sentences
        try:
            sentences = sent_tokenize(text)
        except:
            # Fallback to simple splitting
            sentences = text.split('. ')
        
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            words = sentence.split()
            word_count = len(words)
            
            # Check if adding this sentence would exceed max size
            if current_word_count + word_count > MAX_CHUNK_SIZE_WORDS and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'word_count': current_word_count,
                    'section': section_name
                })
                
                # Calculate overlap
                overlap_words = int(current_word_count * OVERLAP_PERCENTAGE)
                overlap_text = ' '.join(current_chunk[-overlap_words:]) if overlap_words > 0 else ''
                
                # Start new chunk with overlap
                if overlap_text:
                    current_chunk = overlap_text.split() + words
                    current_word_count = len(current_chunk)
                else:
                    current_chunk = words
                    current_word_count = word_count
            else:
                current_chunk.extend(words)
                current_word_count += word_count
        
        # Add final chunk
        if current_chunk and current_word_count >= MIN_CHUNK_SIZE_WORDS:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'word_count': current_word_count,
                'section': section_name
            })
        elif current_chunk and len(text.split()) < MIN_CHUNK_SIZE_WORDS:
            # For very short sections (like "Not applicable"), create a single chunk
            chunks.append({
                'text': text,
                'word_count': len(text.split()),
                'section': section_name
            })
        
        return chunks
    
    def extract_metadata(self, chunk: Dict, chunk_index: int, total_chunks: int, 
                        ticker: str, filing_date: str) -> Dict:
        """Extract metadata for a chunk"""
        text = chunk['text']
        
        # Extract financial figures
        financial_figures = re.findall(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand))?', text)
        
        # Extract dates
        dates = re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', text)
        dates.extend(re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text))
        
        # Extract percentages
        percentages = re.findall(r'\d+(?:\.\d+)?%', text)
        
        # Key financial terms
        financial_terms = [
            'revenue', 'income', 'earnings', 'profit', 'loss', 'margin',
            'cash flow', 'debt', 'equity', 'assets', 'liabilities',
            'growth', 'decline', 'increase', 'decrease'
        ]
        term_counts = {term: text.lower().count(term) for term in financial_terms}
        
        # Risk indicators
        risk_terms = ['risk', 'uncertainty', 'adverse', 'negative', 'decline', 'loss']
        risk_score = sum(text.lower().count(term) for term in risk_terms)
        
        return {
            'chunk_id': f"{ticker}_{filing_date}_{chunk_index}",
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'section': chunk['section'],
            'word_count': chunk['word_count'],
            'char_count': len(text),
            'sentence_count': len(sent_tokenize(text)),
            'financial_figures_count': len(financial_figures),
            'dates_count': len(dates),
            'percentages_count': len(percentages),
            'key_terms': {k: v for k, v in term_counts.items() if v > 0},
            'risk_score': risk_score,
            'ticker': ticker,
            'filing_date': filing_date,
            'document_type': '10-K',
            'text_preview': text[:200] + '...' if len(text) > 200 else text
        }
    
    def process_10k(self, ticker: str, output_dir: str = 'output') -> bool:
        """Main processing function"""
        try:
            logger.info(f"\nProcessing 10-K for {ticker}")
            logger.info("=" * 60)
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Download and extract text
            result = self.download_and_extract_text(ticker)
            if not result:
                return False
            
            text_content, filing_info = result
            
            # Extract sections
            logger.info("\nExtracting sections...")
            sections = self.extract_sections(text_content)
            
            if not sections:
                logger.error("No sections extracted")
                return False
            
            logger.info(f"\nExtracted {len(sections)} sections")
            
            # Create chunks for each section
            all_chunks = []
            chunk_index = 0
            
            for section_name, section_text in sections.items():
                logger.info(f"\nProcessing {section_name}...")
                chunks = self.create_chunks(section_text, section_name)
                
                for chunk in chunks:
                    metadata = self.extract_metadata(
                        chunk, chunk_index, 0,  # Total chunks updated later
                        ticker, filing_info['filing_date']
                    )
                    
                    all_chunks.append({
                        'text': chunk['text'],
                        'metadata': metadata
                    })
                    chunk_index += 1
                
                logger.info(f"  Created {len(chunks)} chunks")
            
            # Update total chunks count
            total_chunks = len(all_chunks)
            for chunk in all_chunks:
                chunk['metadata']['total_chunks'] = total_chunks
            
            logger.info(f"\nTotal chunks created: {total_chunks}")
            
            # Save outputs
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save JSON
            json_file = os.path.join(output_dir, f'{ticker}_10K_chunks_{timestamp}.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': {
                        'ticker': ticker,
                        'filing_date': filing_info['filing_date'],
                        'accession_number': filing_info['accession'],
                        'processing_date': datetime.now().isoformat(),
                        'total_sections': len(sections),
                        'total_chunks': total_chunks,
                        'chunk_config': {
                            'target_size_words': CHUNK_SIZE_WORDS,
                            'min_size_words': MIN_CHUNK_SIZE_WORDS,
                            'max_size_words': MAX_CHUNK_SIZE_WORDS,
                            'overlap_percentage': OVERLAP_PERCENTAGE
                        }
                    },
                    'sections': list(sections.keys()),
                    'chunks': all_chunks
                }, f, indent=2)
            
            logger.info(f"Saved JSON: {json_file}")
            
            # Save CSV
            csv_file = os.path.join(output_dir, f'{ticker}_10K_chunks_{timestamp}.csv')
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'chunk_id', 'chunk_index', 'total_chunks', 'section',
                    'word_count', 'char_count', 'sentence_count',
                    'financial_figures_count', 'dates_count', 'percentages_count',
                    'risk_score', 'ticker', 'filing_date', 'text'
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for chunk in all_chunks:
                    row = {
                        'chunk_id': chunk['metadata']['chunk_id'],
                        'chunk_index': chunk['metadata']['chunk_index'],
                        'total_chunks': chunk['metadata']['total_chunks'],
                        'section': chunk['metadata']['section'],
                        'word_count': chunk['metadata']['word_count'],
                        'char_count': chunk['metadata']['char_count'],
                        'sentence_count': chunk['metadata']['sentence_count'],
                        'financial_figures_count': chunk['metadata']['financial_figures_count'],
                        'dates_count': chunk['metadata']['dates_count'],
                        'percentages_count': chunk['metadata']['percentages_count'],
                        'risk_score': chunk['metadata']['risk_score'],
                        'ticker': chunk['metadata']['ticker'],
                        'filing_date': chunk['metadata']['filing_date'],
                        'text': chunk['text']
                    }
                    writer.writerow(row)
            
            logger.info(f"Saved CSV: {csv_file}")
            
            # Save summary
            summary_file = os.path.join(output_dir, f'{ticker}_10K_summary_{timestamp}.txt')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"10-K Processing Summary for {ticker}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Filing Date: {filing_info['filing_date']}\n")
                f.write(f"Accession Number: {filing_info['accession']}\n")
                f.write(f"Processing Date: {datetime.now().isoformat()}\n\n")
                f.write(f"Sections Extracted: {len(sections)}\n")
                for section in sections.keys():
                    f.write(f"  - {section}\n")
                f.write(f"\nTotal Chunks: {total_chunks}\n")
                f.write(f"Average Chunk Size: {sum(c['metadata']['word_count'] for c in all_chunks) // total_chunks} words\n")
            
            logger.info(f"Saved summary: {summary_file}")
            
            logger.info("\n✓ Processing complete!")
            return True
            
        except Exception as e:
            logger.error(f"Error processing 10-K: {e}")
            return False


def main():
    """Process Microsoft's 10-K as an example"""
    processor = ImprovedSEC10KProcessor()
    
    # Process Microsoft's 10-K
    success = processor.process_10k('MSFT')
    
    if success:
        logger.info("\n✓ Successfully processed Microsoft's 10-K")
    else:
        logger.error("\n✗ Failed to process Microsoft's 10-K")


if __name__ == "__main__":
    main()
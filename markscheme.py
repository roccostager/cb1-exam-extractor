"""
Gemini also pretty much one-shotted this...
Like slight change from pdfPath param to name param with formatted string.
Also added padding to fix clipping.
Took maybe 4 prompts.
"""

import fitz
import re
import os

def find_markscheme_zones(name: str) -> dict:
    """
    Scans a mark scheme PDF line-by-line to identify all vertical zones for each question.
    Handles tight groupings (like MCQs) by examining individual lines rather than text blocks.
    """

    if name.startswith("2019"): return find_old_markscheme_zones(name)

    doc = fitz.open(f"papers/{name}_markscheme.pdf")
    q_pattern = re.compile(r'^Q\s*(\d+)', re.IGNORECASE)
    
    markers = []
    
    # Step 1: Find all question markers line-by-line
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Use 'dict' to prevent PyMuPDF from merging separate lines into one block
        page_data = page.get_text("dict")
        
        for block in page_data.get("blocks", []):
            if "lines" not in block: 
                continue
            
            for line in block["lines"]:
                # Reconstruct the line text from its spans
                line_text = "".join([span["text"] for span in line["spans"]]).strip()
                
                match = q_pattern.match(line_text)
                if match:
                    q_num = int(match.group(1))
                    # The y0 of the line is the top coordinate of its bounding box
                    y0 = line["bbox"][1] 
                    
                    markers.append({
                        'q_num': q_num,
                        'page_num': page_num,
                        'y0': y0
                    })

    # Sort markers by page number, then by y0 coordinate to ensure top-to-bottom logical flow
    markers.sort(key=lambda x: (x['page_num'], x['y0']))
                
    # Step 2: Convert markers into start/end zones
    zones = {}
    for i in range(len(markers)):
        current_marker = markers[i]
        q_num = current_marker['q_num']
        
        start_page = current_marker['page_num']
        start_y = max(0, current_marker['y0'] - 5) # 5 pt margin above the text
        
        # The zone ends where the next marker begins, or at the end of the document
        if i + 1 < len(markers):
            next_marker = markers[i+1]
            end_page = next_marker['page_num']
            end_y = max(0, next_marker['y0'] - 5)
        else:
            end_page = len(doc) - 1
            end_y = doc[end_page].rect.height
            
        zone_info = {
            'start_page': start_page,
            'start_y': start_y,
            'end_page': end_page,
            'end_y': end_y
        }
        
        # Append to a list to handle repeats/workings for the same question
        if q_num not in zones:
            zones[q_num] = []
        zones[q_num].append(zone_info)
        
    doc.close()
    return zones


def save_markscheme_questions(name: str, zones: dict, output_dir: str = "output"):
    """
    Takes the zones dictionary and the original PDF, 
    then saves each question (including all its split parts) as an individual PDF.
    """

    count = 0

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    doc = fitz.open(f"papers/{name}_markscheme.pdf")
    
    for q_num, zone_list in zones.items():
        new_doc = fitz.open()
        
        # Process every zone associated with this question number
        for zone in zone_list:
            start_page = zone['start_page']
            end_page = zone['end_page']
            
            for current_page_num in range(start_page, end_page + 1):
                # Insert the target page into our new document
                new_doc.insert_pdf(doc, from_page=current_page_num, to_page=current_page_num)
                page = new_doc[-1] # Target the newly inserted page
                
                x0 = 0
                x1 = page.rect.width
                
                # Determine vertical crop coordinates based on page position within the zone
                if current_page_num == start_page and current_page_num == end_page:
                    y0, y1 = zone['start_y'], zone['end_y']
                elif current_page_num == start_page:
                    y0, y1 = zone['start_y'], page.rect.height
                elif current_page_num == end_page:
                    y0, y1 = 0, zone['end_y']
                else:
                    y0, y1 = 0, page.rect.height
                    
                # Add padding
                y0 = max(0, y0 + 5)
                y1 = min(page.rect.height, y1 + 5)

                # Apply the crop
                page.set_cropbox(fitz.Rect(x0, y0, x1, y1))
                
        # Save the fully compiled question
        output_filename = os.path.join(output_dir, f"{name}Q{q_num}_m.pdf")
        new_doc.save(output_filename)
        new_doc.close()

        count += 1
        
    doc.close()
    return count


def find_old_markscheme_zones(name: str) -> dict:
    """
    Scans an older mark scheme PDF line-by-line to identify all vertical zones for each question.
    Handles questions on their own line (e.g., "11") AND multi-part questions 
    where the text starts on the same line (e.g., "19 (i) The first ratio...").
    """
    doc = fitz.open(f"papers/{name}_markscheme.pdf")
    
    # Matches a line starting with a 1-2 digit number, followed by EITHER:
    # 1. The end of the line (handles standalone numbers)
    # 2. An optional opening bracket, letters/numbers, and a mandatory closing bracket ')' (handles "19 (i) text...")
    q_pattern = re.compile(r'^(\d{1,2})(?:\s*$|\s*\(?[a-z0-9]+\))', re.IGNORECASE)
    
    markers = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_data = page.get_text("dict")
        
        for block in page_data.get("blocks", []):
            if "lines" not in block: 
                continue
            
            for line in block["lines"]:
                # Reconstruct the line text from its spans
                line_text = "".join([span["text"] for span in line["spans"]]).strip()
                match = q_pattern.match(line_text)
                
                if match:
                    q_num = int(match.group(1))
                    y0 = line["bbox"][1] 
                    
                    markers.append({
                        'q_num': q_num,
                        'page_num': page_num,
                        'y0': y0
                    })

    # Sort markers by page number, then by y0 coordinate to ensure top-to-bottom logical flow
    markers.sort(key=lambda x: (x['page_num'], x['y0']))
                
    # Convert markers into start/end zones
    zones = {}
    for i in range(len(markers)):
        current_marker = markers[i]
        q_num = current_marker['q_num']
        
        start_page = current_marker['page_num']
        start_y = max(0, current_marker['y0'] - 5)
        
        # The zone ends where the next marker begins, or at the end of the document
        if i + 1 < len(markers):
            next_marker = markers[i+1]
            end_page = next_marker['page_num']
            end_y = max(0, next_marker['y0'] - 5)
        else:
            end_page = len(doc) - 1
            end_y = doc[end_page].rect.height
            
        zone_info = {
            'start_page': start_page,
            'start_y': start_y,
            'end_page': end_page,
            'end_y': end_y
        }
        
        if q_num not in zones:
            zones[q_num] = []
        zones[q_num].append(zone_info)
        
    doc.close()
    return zones
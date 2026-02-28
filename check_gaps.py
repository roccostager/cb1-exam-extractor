"""
I was not bothered to write this part
It just checks for extra content that is sometimes given for the long-form Qs
Gemini one-shotted this lol
"""

import fitz

def check_and_extend_gaps(doc, zones, anchors):
    """
    Checks for extra content between Q19 and Q20, and Q20 to END OF PAPER.
    If valid content (non-footer) is found, it extends the bounding box of the question.
    """
    
    # 1. Check the gap between Question 19 and 20
    if 19 in zones and 20 in anchors:
        start_page = zones[19]["end_page_num"]
        start_y = zones[19]["y1"]
        end_page = anchors[20]["page_num"]
        end_y = anchors[20]["start"][1]
        
        has_content, final_page, final_y = analyze_gap(doc, start_page, start_y, end_page, end_y)
        if has_content:
            zones[19]["end_page_num"] = final_page
            zones[19]["y1"] = final_y + 10  # Add slight padding

    # 2. Check the gap between Question 20 and 'END OF PAPER'
    if 20 in zones:
        start_page = zones[20]["end_page_num"]
        start_y = zones[20]["y1"]
        
        # Find the 'END OF PAPER' marker
        end_page = start_page
        end_y = doc[start_page].rect.height
        found_end = False
        
        for p in range(start_page, len(doc)):
            page = doc[p]
            marks = page.search_for("END OF PAPER")
            if marks:
                end_page = p
                end_y = marks[0].y0
                found_end = True
                break
                
        # Fallback if "END OF PAPER" is missing
        if not found_end:
            end_page = len(doc) - 1
            end_y = doc[end_page].rect.height - 50 
            
        has_content, final_page, final_y = analyze_gap(doc, start_page, start_y, end_page, end_y)
        if has_content:
            zones[20]["end_page_num"] = final_page
            zones[20]["y1"] = final_y + 10


def analyze_gap(doc, start_page, start_y, end_page, end_y):
    """
    Looks for valid content in the specified gap, filtering out known footers and margins.
    Returns: (boolean indicating if content was found, max page of content, max Y coordinate)
    """
    has_content = False
    max_page = start_page
    max_y = start_y
    
    for p in range(start_page, end_page + 1):
        page = doc[p]
        
        # Define search rectangle for the current page in the gap
        rect_y0 = start_y if p == start_page else 0
        rect_y1 = end_y if p == end_page else page.rect.height
        
        search_rect = fitz.Rect(0, rect_y0, page.rect.width, rect_y1)
        blocks = page.get_text("blocks", clip=search_rect)
        
        for b in blocks:
            # PyMuPDF block structure: (x0, y0, x1, y1, text, block_no, block_type)
            b_y0, b_y1, text, b_type = b[1], b[3], b[4], b[6]
            
            # Ignore images/drawings (type != 0) and empty strings
            if b_type != 0 or not text.strip():
                continue
                
            # Ignore common footers (modify these strings if your footer format changes)
            if "CB1 A2025" in text or "Institute and Faculty of Actuaries" in text:
                continue
                
            # Ignore text located in the bottom 50 points of the page (standard footer margin)
            if b_y0 > page.rect.height - 50:
                continue
                
            # If we reach here, we've hit valid text (like your statements/tables)
            has_content = True
            max_page = p
            # Track the lowest point the content reaches
            max_y = max(max_y, b_y1) if p == max_page else b_y1
            
    return has_content, max_page, max_y
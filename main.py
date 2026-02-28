# Importing Libraries
import pandas as pd
import fitz
import os

from check_gaps import check_and_extend_gaps
from markscheme import find_markscheme_zones, save_markscheme_questions

df = pd.read_csv("problems.csv")
row_length: int = len(df)


# Config
CAP = 1  # Safety mechanism
BOLD_FLAG = 20
OUTPUT_DIR = "output"


def main():

    for i in range(row_length):

        question: str = df["Question"][i]
        name = question.split("Q")[0]
        question_number = question.split("Q")[1]

        # Coordinate based cropping
        zones = find_zones(name)
        save_questions(name, zones)

        m_zones = find_markscheme_zones(name)
        save_markscheme_questions(name, m_zones, OUTPUT_DIR)

        if i + 1 >= CAP:  # Safety
            break


def find_zones(name: str):
    """
    Find zones for each question
    """

    doc = fitz.open(f"papers/{name}_exam.pdf")
    data = []

    for page_num in range(len(doc)):

        page = doc[page_num]
        page_data = page.get_text("dict")
        data.append(page_data)


    # Finding beginning of questions
    anchors = {}

    for page_num, page in enumerate(data):
            
        for block in page.get("blocks", []):
            if "lines" not in block: continue
            for line in block["lines"]:
                for span in line["spans"]:
                    
                    span_text = span["text"].strip()
                    span_flags = span["flags"]

                    if span_text.isdigit() and (span_flags & 16):
                        
                        question_no = int(span_text)
                        anchors[question_no] = {
                            "page_num": page_num,
                            "start": span["bbox"]
                        }

    # Find crop zones
    zones = {}

    for question_no, info in anchors.items():
        if question_no <= 18:  # short-form question
            find_question_zone(doc, question_no, info, anchors, zones)
        else: # long-form question
            find_long_question_zone(doc, question_no, info, anchors, zones)

    check_and_extend_gaps(doc, zones, anchors)

    doc.close()

    return zones


def find_question_zone(doc, question_no, info, anchors, zones):

    page_num = info["page_num"]
    y_start = info["start"][1]

    # Initial search area
    curr_page_num = page_num
    current_page = doc[curr_page_num]
    search_rect = fitz.Rect(0, y_start, current_page.rect.width, current_page.rect.height)

    # Define ending
    found_end = False

    while not found_end:

        marks = current_page.search_for("[", clip=search_rect)

        if marks:  # Question end found
            first_mark = marks[0]
            anchors[question_no]["end"] = first_mark
            
            zones[question_no] = {
                "page_num": page_num,
                "y0": y_start - 10,
                "end_page_num": curr_page_num,
                "y1": first_mark.y1 + 10
            }

            found_end = True  # End search

        else:

            # Increment current page number
            curr_page_num += 1

            if curr_page_num >= len(doc):
                found_end = True
            else:

                # Update search area to new search area
                current_page = doc[curr_page_num]
                search_rect = fitz.Rect(0, 0, current_page.rect.width, current_page.rect.height)


def find_long_question_zone(doc, question_no, info, anchors, zones):

    page_num = info["page_num"]
    y_start = info["start"][1]

    # Initial search area
    curr_page_num = page_num
    current_page = doc[curr_page_num]
    search_rect = fitz.Rect(0, y_start, current_page.rect.width, current_page.rect.height)

    # Define ending
    found_end = False

    while not found_end:

        marks = current_page.search_for("[Total", clip=search_rect)

        if marks:  # Question end found
            first_mark = marks[0]
            anchors[question_no]["end"] = first_mark
            
            zones[question_no] = {
                "page_num": page_num,
                "y0": y_start - 10,
                "end_page_num": curr_page_num,
                "y1": first_mark.y1 + 10
            }

            found_end = True  # End search

        else:

            # Increment current page number
            curr_page_num += 1

            if curr_page_num >= len(doc):
                found_end = True
            else:

                # Update search area to new search area
                current_page = doc[curr_page_num]
                search_rect = fitz.Rect(0, 0, current_page.rect.width, current_page.rect.height)


def save_questions(name: str, zones):
    """
    Takes the zones dictionary and the original PDF, 
    then saves each question as an individual PDF.
    """

    # Open the source document
    doc = fitz.open(f"papers/{name}_exam.pdf")

    for question_no, zone_data in zones.items():
        # 1. Start a new PDF for this specific question
        new_doc = fitz.open()
        
        start_page = zone_data["page_num"]
        end_page = zone_data["end_page_num"]

        for current_page_num in range(start_page, end_page + 1):

            new_doc.insert_pdf(doc, from_page=current_page_num, to_page=current_page_num)
            page = new_doc[-1]
            
            # Find crop box
            x0 = 0
            x1 = page.rect.width
            
            # Y-coordinates depend on whether we are at the start, middle, or end
            if current_page_num == start_page and current_page_num == end_page:  # Singe-page question
                y0, y1 = zone_data["y0"], zone_data["y1"]
            elif current_page_num == start_page:  # first page, multi-page question
                y0, y1 = zone_data["y0"], page.rect.height
            elif current_page_num == end_page:  # last page, multi-page question
                y0, y1 = 0, zone_data["y1"]
            else:  # middle page, multi-page question
                y0, y1 = 0, page.rect.height

            # Apply the crop
            page.set_cropbox(fitz.Rect(x0, y0, x1, y1))

        # 4. Save the finished question PDF
        output_filename = f"{name}Q{question_no}_q.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        new_doc.save(output_path)
        new_doc.close()

    doc.close()


if __name__ == "__main__":
    main()
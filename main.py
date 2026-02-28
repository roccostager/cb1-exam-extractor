# Importing Libraries
import pandas as pd
import fitz
import json
import re
import os


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
        find_zones(name, question_number)

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
            if "lines" in block:
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

        page_num = info["page_num"]
        y_start = info["start"][1]
        
        # Initial search area
        curr_page_num = page_num
        current_page = doc[curr_page_num]
        search_rect = fitz.Rect(0, y_start, current_page.rect.width, current_page.rect.height)
        
        # Define ending
        found_end = False

        while not found_end:

            marks = current_page.search_for(re.compile(r"\[\d+\]"), clip=search_rect)

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


if __name__ == "__main__":
    main()
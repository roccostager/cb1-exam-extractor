from pdf2image import convert_from_path
from PIL import Image
import os


INPUT_DIR = "docs-pdf"
OUTPUT_DIR = "docs"


def pdf_to_image(name):

    pdf_path = f"{INPUT_DIR}/{name}.pdf"
    pages = convert_from_path(pdf_path, dpi=200, use_cropbox=True)

    width = max(page.width for page in pages)
    height = sum(page.height for page in pages)

    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    y = 0
    for page in pages:
        image.paste(page.convert("RGBA"), (0, y))
        y += page.height

    image.save(f"{OUTPUT_DIR}/{name}.png", "PNG")


def process_pdfs():

    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            
            print(filename)

            name = filename.split(".")[0]
            pdf_to_image(name)


process_pdfs()
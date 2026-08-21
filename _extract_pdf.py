import fitz

doc = fitz.open(r"C:/Users/User/Downloads/devfest (1).pdf")
out = []
out.append(f"PAGES: {doc.page_count}")
for i, page in enumerate(doc):
    out.append(f"\n===== PAGE {i+1} =====\n")
    out.append(page.get_text())
with open(r"C:/Users/User/Documents/DEVLEAGUE HACKATHON/_spec.txt", "w", encoding="utf-8") as f:
    f.write("".join(out))
print("WROTE", len("".join(out)), "chars")

# --- الشكل الأول معدل: ترتيب الصور وتقليل الصفحات ---
def run_fpdf_style_fixed(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Style1_Fixed_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        out_doc = fitz.open() 
        font_path = "Amiri.ttf"
        all_processed_images = []

        new_page = out_doc.new_page()
        y_offset = 50

        for page in doc:
            # ترتيب الصور حسب الظهور وتقليل الصفحات
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in all_processed_images: continue
                try:
                    pix = fitz.Pixmap(doc, xref)
                    img_rect = fitz.Rect(50, y_offset, 540, y_offset + 280)
                    new_page.insert_image(img_rect, pixmap=pix)
                    y_offset += 290  # مسافة أقل لتقليل الصفحات
                    if y_offset > 750:  # إذا تجاوز الارتفاع، صفحة جديدة
                        new_page = out_doc.new_page()
                        y_offset = 50
                    all_processed_images.append(xref)
                except: pass

            # معالجة النصوص (إنجليزي 14 عربي 14.5)
            text = page.get_text("text")
            if text.strip():
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 3:
                        try:
                            translated = GoogleTranslator(source='en', target='ar').translate(line)
                            fixed_ar = fix_arabic(translated)
                            if y_offset > 750:
                                new_page = out_doc.new_page()
                                y_offset = 50
                            # كتابة الإنجليزي
                            new_page.insert_text((50, y_offset), line, fontsize=14, color=(0,0,0))
                            y_offset += 18
                            # كتابة العربي
                            new_page.insert_text((50, y_offset), fixed_ar, fontsize=14.5, fontname="f0", fontfile=font_path, color=(0.8, 0, 0))
                            y_offset += 25
                        except: continue

        out_doc.save(output_pdf)
        out_doc.close()
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"حدث خطأ غير متوقع: {e}")


# --- الشكل الثالث معدل: تكبير الخط العربي والإنجليزي ---
def run_highlight_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Highlight_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)
        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        for page in doc:
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    rect = span["bbox"]
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    # تكبير الخطوص كما طلب
                                    ar_sz = 10
                                    en_sz = 8
                                    high_rect = [rect[0], rect[3]-2, rect[2], rect[3]+ar_sz-1]
                                    page.draw_rect(high_rect, color=(0.92, 0.96, 1), fill=(0.92, 0.96, 1))
                                    # كتابة الإنجليزي
                                    page.insert_text(fitz.Point(rect[0], rect[1]), txt, fontsize=en_sz, color=(0,0,0))
                                    # كتابة العربي
                                    page.insert_text(fitz.Point(rect[0], high_rect[3]-0.5), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1, 0.3, 0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ في شكل الهايلايت: {e}")

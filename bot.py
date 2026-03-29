# --- الشكل 3: الهايلايت المحمي من التداخل ---
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
                                    
                                    # 1. مسح السطر الأصلي تماماً لضمان عدم التداخل
                                    clean_rect = fitz.Rect(rect[0]-1, rect[1]-1, rect[2]+1, rect[3]+1)
                                    page.draw_rect(clean_rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    
                                    # 2. إعادة كتابة الإنكليزي بحجم أصغر وبمكان "مرتفع" قليلاً
                                    eng_sz = span["size"] * 0.75
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    
                                    # 3. ترجمة العربي
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    
                                    # 4. رسم الهايلايت تحت الإنكليزي مباشرة
                                    ar_sz = span["size"] * 0.60
                                    # المستطيل الملون يغطي مساحة العربي فقط
                                    high_rect = fitz.Rect(rect[0], rect[1] + eng_sz + 1, rect[2], rect[3] + 1)
                                    page.draw_rect(high_rect, color=(0.94, 0.97, 1), fill=(0.94, 0.97, 1))
                                    
                                    # 5. حقن العربي داخل الهايلايت
                                    page.insert_text(fitz.Point(rect[0], high_rect.y1 - 1), fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0.1, 0.3, 0.7))
                                except: continue
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: bot.reply_to(message, f"خطأ: {e}")

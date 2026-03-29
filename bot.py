# --- الشكل 3: الهايلايت الرسمي (المضمون) ---
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
                                    rect = span["bbox"] # [x0, y0, x1, y1]
                                    
                                    # 1. مسح النص الأصلي تماماً (للنظافة)
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                    
                                    # 2. إعادة كتابة الإنكليزي (تصغير 0.70)
                                    eng_sz = span["size"] * 0.70
                                    page.insert_text(fitz.Point(rect[0], rect[1] + eng_sz), txt, fontsize=eng_sz, color=(0,0,0))
                                    
                                    # 3. ترجمة وحقن العربي (تصغير 0.60)
                                    trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                    fixed = fix_arabic(trans)
                                    ar_sz = span["size"] * 0.60
                                    
                                    # إحداثيات نص العربي
                                    ar_point = fitz.Point(rect[0], rect[3])
                                    page.insert_text(ar_point, fixed, fontsize=ar_sz, fontname="f0", fontfile=font_path, color=(0, 0, 0)) # نكتبه بالأسود ليوضح فوق الهايلايت
                                    
                                    # 4. إضافة الهايلايت (التظليل) فوق نص العربي فقط
                                    # نحدد منطقة العربي (النصف السفلي من السطر الأصلي)
                                    ar_rect = fitz.Rect(rect[0], rect[1] + eng_sz + 1, rect[2], rect[3] + 1)
                                    annot = page.add_highlight_annot(ar_rect)
                                    annot.set_colors(stroke=(0.8, 0.9, 1)) # لون سمائي فاتح جداً
                                    annot.update()
                                    
                                except: continue
        
        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e: 
        bot.reply_to(message, f"خطأ في الهايلايت: {str(e)}")

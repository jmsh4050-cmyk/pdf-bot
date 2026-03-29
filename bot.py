for page in doc:
    dict_text = page.get_text("dict")
    for block in dict_text["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if len(txt) > 2 and not contains_arabic(txt):
                        try:
                            # إحداثيات السطر الأصلي
                            rect = span["bbox"] # [x0, y0, x1, y1]
                            
                            # --- 1. المسح الذكي (Smart Clean) ---
                            # نكبر المستطيل الأبيض شوية للأعلى وللأسفل لضمان المسح الكامل
                            clean_rect = fitz.Rect(rect[0], rect[1] - 1, rect[2], rect[3] + 1)
                            page.draw_rect(clean_rect, color=(1, 1, 1), fill=(1, 1, 1))
                            
                            # --- 2. كتابة الإنكليزي الجديد (تصغير أكثر للضمان) ---
                            # راح نستخدم 0.7 للإنكليزي حتى نترك مجال للعربي
                            eng_sz = span["size"] * 0.7
                            # نضع الإنكليزي في أعلى المستطيل الممسوح
                            page.insert_text(
                                fitz.Point(rect[0], rect[1] + eng_sz), 
                                txt, 
                                fontsize=eng_sz, 
                                color=(0, 0, 0)
                            )
                            
                            # --- 3. الترجمة وحقن العربي ---
                            trans = GoogleTranslator(source='en', target='ar').translate(txt)
                            fixed = fix_arabic(trans)
                            
                            # حجم العربي 0.6 من الأصلي
                            ar_sz = span["size"] * 0.6
                            # نضع العربي في أسفل المستطيل الممسوح (بعيد عن الإنكليزي)
                            page.insert_text(
                                fitz.Point(rect[0], rect[3]), 
                                fixed, 
                                fontsize=ar_sz, 
                                fontname="f0", 
                                fontfile=font_path, 
                                color=(0, 0.4, 0.8)
                            )
                        except: continue
                            

def run_flashcard_style(message, file_info):
    user_id = message.chat.id
    try:
        file_path = bot.get_file(file_info['file_id']).file_path
        downloaded = bot.download_file(file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Nursing_Cards_{file_info['file_name']}"
        with open(input_pdf, 'wb') as f: f.write(downloaded)

        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf"
        
        for page in doc:
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # الترتيب من الأعلى للأسفل
            
            # مسح الصفحة بالكامل
            page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            y_pos = 40
            margin = 30
            page_width = page.rect.width

            for block in blocks:
                txt = block[4].strip()
                if len(txt) > 2 and not contains_arabic(txt):
                    try:
                        translated = GoogleTranslator(source='en', target='ar').translate(txt)
                        ar_txt = fix_arabic(translated)
                        
                        # تحديد الارتفاع المطلوب للبطاقة بناءً على طول النص
                        card_height = 45 if len(txt) < 50 else 70
                        
                        # رسم إطار البطاقة (Card)
                        card_rect = fitz.Rect(margin, y_pos, page_width - margin, y_pos + card_height)
                        page.draw_rect(card_rect, color=(0.8, 0.8, 0.8), width=0.5) # إطار خفيف
                        
                        # إذا كان عنوان، نلون البطاقة
                        if any(k in txt.upper() for k in ["NURSING", "CARE", "DIAGNOSIS"]):
                            page.draw_rect(card_rect, color=(0.9, 0.9, 1), fill=(0.9, 0.9, 1))

                        # كتابة النص الإنكليزي (يسار)
                        page.insert_textbox(fitz.Rect(margin + 5, y_pos + 5, (page_width/2) - 5, y_pos + card_height - 5),
                                            txt, fontsize=12, color=(0,0,0), align=0)
                        
                        # كتابة النص العربي (يمين)
                        page.insert_textbox(fitz.Rect((page_width/2) + 5, y_pos + 5, page_width - margin - 5, y_pos + card_height - 5),
                                            ar_txt, fontsize=12, fontname="f0", fontfile=font_path, color=(0,0,0), align=2)

                        y_pos += card_height + 10 # مسافة بين البطاقات
                        
                        if y_pos > page.rect.height - 50: break
                    except: continue

        doc.save(output_pdf)
        doc.close()
        send_and_clean(message, output_pdf, input_pdf)
    except Exception as e:
        bot.reply_to(message, f"خطأ في شكل البطاقات: {e}")

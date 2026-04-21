from telethon import TelegramClient, events, types

# بياناتك التي طلبتها
api_id = 23902341  # ستحتاج للتأكد من هذا الرقم من my.telegram.org
api_hash = '9190100418be2436f560e206014457e5' # ستحتاج للتأكد من هذا أيضاً
bot_token = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'

client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

@client.on(events.Raw(types.UpdateMessageReactions))
async def handler(event):
    # إرسال إشعار عند حدوث تفاعل
    # ملاحظة: استبدل 123456789 برقم الـ ID الخاص بك (من بوت @userinfobot)
    my_id = 123456789 
    
    try:
        msg_id = event.msg_id
        await client.send_message(my_id, f"🔔 تم رصد تفاعل جديد على الرسالة رقم: {msg_id}")
    except Exception as e:
        print(f"حدث خطأ: {e}")

print("✅ البوت يعمل الآن باستخدام التوكن الخاص بك...")
client.run_until_disconnected()

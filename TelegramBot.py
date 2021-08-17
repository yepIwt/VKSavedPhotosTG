
from aiogram import Bot, Dispatcher, executor, types

class Core:

	def __init__(self, telegram_token: str, upload_pic_to_vk):
		self.bot = Bot(telegram_token)
		self.group_id = None
		self.upload_pic_to_vk = upload_pic_to_vk

	async def got_picture_from_channel(self, message: types.Message):
		if message.chat.id == self.group_id:
			await self.bot.download_file_by_id(message.photo[-1].file_id, str(message.photo[-1].file_id) + '.jpg')
			await self.upload_pic_to_vk(message.photo[-1].file_id + '.jpg')
			await message.answer('Отправлено')

		elif not self.group_id:
			await message.answer("Для регистрации канала напишите /start в канал")
		else:
			await message.answer("Отправьте пикчу в тг-канал")		

	async def send_info(self, message: types.Message):
		if message.chat.type == 'group':
			if not self.group_id:
				self.group_id = message.chat.id
				message_text = "Теперь все сохранёночки из вк будут лететь в этот чат"
			else:
				message_text = "Отправьте сюда картиночку и я вам помогу)"
		else:
			message_text = "Добавьте меня в телеграм-группу для начала работы"
		await message.answer(message_text)
		

	def start(self):
		dp = Dispatcher(self.bot)
		dp.register_message_handler(self.send_info, commands = ['start', 'help'])
		dp.register_message_handler(self.got_picture_from_channel, content_types = ['photo'])
		executor.start_polling(dp, skip_updates = True)

if __name__ == "__main__":
	token = ""
	c = Core(telegram_token = token)
	c.start()
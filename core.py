import os
import TelegramBot
from vkwave.api import API
from vkwave.client import AIOHTTPClient

import aiohttp, aiofiles
import asyncio

import json

VK_API_TOKEN = os.getenv("VK_API_TOKEN")
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

ALBUM_DESCRIPTION = "Этот альбом используется для загрузки фоток из Телеграма. Большую часть времени он пустой, это значит, что ниче не синхронится"

class Core:

	def __init__(self, vk_api_key: str, tg_api_key: str):
		self.vk_api = self.get_vk_api(vk_api_key)
		self.tg_core = TelegramBot.Core(tg_api_key, self.save_photo, self.get_saved_photos_from_vk)
		self.sync_album = None
		self.locked = None

	def get_vk_api(self, token):
		api_session = API(tokens= token, clients=AIOHTTPClient())
		api = api_session.get_context()
		return api

	async def get_sync_queue_album(self):
		response = await self.vk_api.photos.get_albums()
		sync_album = None
		for album in response.response.items:
			if album.title == 'SYNC_QUEUE':
				sync_album = album.id
		return sync_album

	async def create_sync_queue_album(self):
		response = await self.vk_api.photos.create_album(
			title = 'SYNC_QUEUE',
			description = ALBUM_DESCRIPTION,
			privacy_view = 'only_me',
			privacy_comment = 'only_me',
			comments_disabled = 1,
		)
		return response.response.id

	async def check_sync_album(self):
		if not self.sync_album:
			self.sync_album = await self.get_sync_queue_album()
			if not self.sync_album:
				self.sync_album = await self.create_sync_queue_album()

	async def upload_pic_to_sync_album(self, filename):

		await self.check_sync_album() # 1
		await asyncio.sleep(5)
		result = await self.vk_api.photos.get_upload_server(album_id = self.sync_album) # 2
		await asyncio.sleep(5)
		url_to_upload = result.response.upload_url

		if not os.access(filename, os.R_OK):
			raise 'No such file'

		f = open(filename, 'rb')

		async with aiohttp.ClientSession() as session:
			async with session.post(url_to_upload, data = {'file':f}) as resp:
				data = await resp.read()

		hashrate = json.loads(data)

		result = await self.vk_api.photos.save( #3
			album_id = self.sync_album,
			server = hashrate['server'],
			photos_list = hashrate['photos_list'],
			hash = hashrate['hash']
		)

		return result.response[0].owner_id, result.response[0].id

	async def save_photo(self, filename):
		
		await asyncio.sleep(5)

		owner_id, photo_id = await self.upload_pic_to_sync_album(filename) # 4

		result = await self.vk_api.photos.copy(owner_id = owner_id, photo_id = photo_id) # 5

		await asyncio.sleep(5)

		await self.vk_api.photos.delete(owner_id = owner_id, photo_id = photo_id) #6


		photo_id_in_saved = result.response

		# раньше я сохранял в свои списки photo_id и не понимал, почему он дублируется
		# оказывается я я тупанул и сохранял photo_id от альбома sync, а при копировании
		# ну или добавлении в сохраненки выдается дургой photo_id
		# долго не мог понять, почему дублируется фотка

		self.tg_core.sent_pictures.append(photo_id_in_saved)

		os.remove(filename)

	async def get_all_saved_photos(self, offset, where_saved):

		result = await self.vk_api.photos.get(album_id=-15, offset = offset,count=1000)

		where_saved.extend(result.response.items)

		if len(result.response.items) != 0 and len(where_saved) != len(result.response.items):
			await self.get_all_saved_photos(offset+1000, where_saved)

		return where_saved

	async def get_saved_photos_from_vk(self):

		saved_photos = await self.get_all_saved_photos(0, [])

		new_saved_photos = []

		for item in saved_photos:
			new_saved_photos.append(item.id)

		to_sync = list(set(new_saved_photos) - set(self.tg_core.sent_pictures))

		result = await self.vk_api.photos.get(album_id = -15, photo_ids = to_sync)

		for element in result.response.items:
			url = element.sizes[-1].url
			photo_id = element.id
			
			if photo_id not in self.tg_core.sent_pictures: # дабл проверка
				await self.tg_core.send_picture_to_channel(url, photo_id)

if __name__ == '__main__':
	c = Core(VK_API_TOKEN, TELEGRAM_API_TOKEN)
	c.tg_core.start()
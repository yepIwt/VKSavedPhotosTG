import os
import TelegramBot
from vkwave.api import API
from vkwave.client import AIOHTTPClient

from vkwave.bots.utils.uploaders import WallPhotoUploader

import aiohttp, aiofiles
import asyncio

import json

import config

ALBUM_DESCRIPTION = "Этот альбом используется для загрузки фоток из Телеграма. Большую часть времени он пустой, это значит, что ниче не синхронится"

class Core:

	def __init__(self, vk_api_key: str, tg_api_key: str):
		self.vk_api = self.get_vk_api(vk_api_key)
		self.tg_core = TelegramBot.Core(tg_api_key, self.save_photo) 
		self.sync_album = None

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
		await self.check_sync_album()
		result = await self.vk_api.photos.get_upload_server(album_id = self.sync_album)
		url_to_upload = result.response.upload_url

		if not os.access(filename, os.R_OK):
			return (False, 'No such file')

		f = open(filename, 'rb')

		async with aiohttp.ClientSession() as session:
			async with session.post(url_to_upload, data = {'file':f}) as resp:
				data = await resp.read()

		hashrate = json.loads(data)

		result = await self.vk_api.photos.save(
			album_id = self.sync_album,
			server = hashrate['server'],
			photos_list = hashrate['photos_list'],
			hash = hashrate['hash']
		)

		return result.response[0].owner_id, result.response[0].id

	async def save_photo(self, filename):

		owner_id, photo_id = await self.upload_pic_to_sync_album(filename)

		await self.vk_api.photos.copy(owner_id = owner_id, photo_id = photo_id)
		await self.vk_api.photos.delete(owner_id = owner_id, photo_id = photo_id)

		os.remove(filename)

if __name__ == '__main__':
	c = Core(config.VK_API_KEY, config.TELEGRAM_API_KEY)
	c.tg_core.start()
import { Injectable } from '@nestjs/common'
import { Ctx, On, Start, Update } from 'nestjs-telegraf'
import { Context } from 'telegraf'

import { TelegramService } from './telegram.service'

@Injectable()
@Update()
export class TelegramUpdateHandler {
	constructor(private readonly telegramService: TelegramService) {}

	@Start()
	async start(@Ctx() ctx: Context) {
		await ctx.reply('Welcome!')
	}

	@On('text')
	async handleText(@Ctx() context: Context): Promise<void> {
		await this.telegramService.handleTextMessage(context)
	}

	@On('photo')
	async handlePhoto(@Ctx() context: Context): Promise<void> {
		await this.telegramService.handlePhotoMessage(context)
	}
}

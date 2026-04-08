import { Module } from '@nestjs/common'
import { ConfigModule } from '@nestjs/config'

import { TransactionsModule } from '../transactions/transactions.module'
import { WebsocketModule } from '../websocket/websocket.module'
import { LlmService } from './llm.service'
import { OcrService } from './ocr.service'
import { ParsingService } from './parsing.service'
import { ProcessingService } from './processing.service'

@Module({
	imports: [ConfigModule, TransactionsModule, WebsocketModule],
	providers: [OcrService, LlmService, ParsingService, ProcessingService],
	exports: [ProcessingService],
})
export class ProcessingModule {}

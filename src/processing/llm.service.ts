import { Injectable } from '@nestjs/common'
import { ConfigService } from '@nestjs/config'
import axios from 'axios'

type LlmExtractResponse = {
	bank_name?: string
	amount?: number
	transaction_id?: string
	timestamp?: string
	bankName?: string
	transactionId?: string
}

@Injectable()
export class LlmService {
	constructor(private readonly configService: ConfigService) {}

	async extractFields(ocrText: string): Promise<{
		bankName: string | null
		amount: number | null
		transactionId: string | null
		timestamp: string | null
	}> {
		const llmBaseUrl = this.configService.get<string>('LLM_SERVICE_URL')
		if (!llmBaseUrl) {
			throw new Error('LLM_SERVICE_URL is not configured')
		}

		const response = await axios.post<LlmExtractResponse>(`${llmBaseUrl}/llm/extract`, { text: ocrText }, { timeout: 30000 })

		const data = response.data
		return {
			bankName: data.bankName ?? data.bank_name ?? null,
			amount: typeof data.amount === 'number' && Number.isFinite(data.amount) ? data.amount : null,
			transactionId: data.transactionId ?? data.transaction_id ?? null,
			timestamp: data.timestamp ?? null,
		}
	}
}

import { Injectable } from '@nestjs/common'

import { LlmService } from './llm.service'
import { ParsedTransaction } from './types/parsed-transaction.type'

const BANK_NAMES = ['CBE', 'Commercial Bank of Ethiopia', 'Awash', 'Abyssinia', 'Dashen', 'Hibret', 'Telebirr']

@Injectable()
export class ParsingService {
	constructor(private readonly llmService: LlmService) {}

	async parse(ocrText: string): Promise<ParsedTransaction> {
		const regexParsed = this.parseWithRegex(ocrText)

		const hasCriticalFields =
			regexParsed.amount !== null && regexParsed.transactionId !== null && regexParsed.timestamp !== null && regexParsed.bankName !== null

		if (hasCriticalFields) {
			return {
				...regexParsed,
				confidence: 0.92,
				usedLlm: false,
			}
		}

		const llmParsed = await this.llmService.extractFields(ocrText)
		const merged: ParsedTransaction = {
			bankName: regexParsed.bankName ?? llmParsed.bankName,
			amount: regexParsed.amount ?? llmParsed.amount,
			transactionId: regexParsed.transactionId ?? llmParsed.transactionId,
			timestamp: regexParsed.timestamp ?? llmParsed.timestamp,
			usedLlm: true,
			confidence: 0.78,
		}

		const mergedHasAllFields = merged.amount !== null && merged.transactionId !== null && merged.timestamp !== null && merged.bankName !== null

		if (!mergedHasAllFields) {
			return { ...merged, confidence: 0.55 }
		}

		return merged
	}

	private parseWithRegex(ocrText: string): Omit<ParsedTransaction, 'confidence' | 'usedLlm'> {
		const amountRegex = /(?:ETB|Birr|Br)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})|[0-9]+(?:\.[0-9]{1,2}))/i
		const transactionIdRegex = /(?:tx(?:n|id)?|transaction(?:\s*id)?|reference|ref)[\s:#-]*([A-Za-z0-9-]{6,})/i
		const dateRegex = /([0-9]{4}[/-][0-9]{2}[/-][0-9]{2}(?:\s+[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?)/

		const amountMatch = ocrText.match(amountRegex)
		const transactionIdMatch = ocrText.match(transactionIdRegex)
		const dateMatch = ocrText.match(dateRegex)

		const amount = amountMatch ? Number(amountMatch[1].replaceAll(',', '')) : null
		const transactionId = transactionIdMatch ? transactionIdMatch[1] : null
		const timestamp = dateMatch ? this.normalizeDate(dateMatch[1]) : null
		const bankName = this.extractBankName(ocrText)

		return {
			amount: Number.isFinite(amount) ? amount : null,
			transactionId,
			timestamp,
			bankName,
		}
	}

	private normalizeDate(rawDate: string): string | null {
		const normalized = rawDate.replaceAll('/', '-')
		const date = new Date(normalized)
		if (Number.isNaN(date.getTime())) {
			return null
		}
		return date.toISOString()
	}

	private extractBankName(ocrText: string): string | null {
		const normalizedText = ocrText.toLowerCase()
		const matched = BANK_NAMES.find((bank) => normalizedText.includes(bank.toLowerCase()))
		return matched ?? null
	}
}
